"""
model_registry.py — resolve model ids against whatever the region actually hosts.

watsonx model availability differs per region, and a hardcoded id is a demo that
works on one account and dies on another. eu-gb, for instance, hosts no Granite
instruct model at all, so the configured baseline silently fell back to the
creative model and the "hybrid" claim quietly stopped being true.

So instead of naming one model per role, each role names an ordered *preference
list* and we pick the best id the region can actually serve. Nothing is
hardcoded as required: if none of the preferences exist, we take any model the
region offers for that role rather than failing.

The registry is queried once at startup and cached. If the query itself fails
(offline, permissions, SDK change) every role falls back to its configured id,
so a resolution problem can never be worse than the old hardcoded behaviour.
"""
from __future__ import annotations

import logging
import threading
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# ── Role preferences, best first ──────────────────────────────────────────────
# Ordering rationale, not arbitrary:
#   creative — instruction-following under a persona constraint is what matters.
#   baseline — this is the "bland AI default" anchor for distinctiveness, so it
#     wants a *small, cheap, low-temperature* model. It is also scored against,
#     so a different family from the creative model makes the measurement
#     independent rather than self-referential (see pick_baseline).
#     granite-4-h-small leads: it is the current Granite generation, and the
#     baseline is the one role where the model's *own* prose is measured, so
#     running the newest Granite makes the anchor a fair representation of what
#     a current IBM model actually writes when asked to be bland.
#   embedding — multilingual Granite first; the slate retrievers are the
#     long-standing fallback present in nearly every region.
CREATIVE_PREFERENCES: tuple[str, ...] = (
    "meta-llama/llama-3-3-70b-instruct",
    "meta-llama/llama-4-maverick-17b-128e-instruct-fp8",
    "meta-llama/llama-3-405b-instruct",
    "mistralai/mistral-large",
    "mistralai/mistral-small-3-1-24b-instruct-2503",
    "ibm/granite-4-h-small",
    "ibm/granite-3-3-8b-instruct",
    "ibm/granite-3-2-8b-instruct",
)

BASELINE_PREFERENCES: tuple[str, ...] = (
    "ibm/granite-4-h-small",
    "ibm/granite-3-3-8b-instruct",
    "ibm/granite-3-2-8b-instruct",
    "ibm/granite-3-8b-instruct",
    "mistralai/mistral-small-3-1-24b-instruct-2503",
    "meta-llama/llama-3-2-3b-instruct",
    "meta-llama/llama-3-3-70b-instruct",
)

EMBEDDING_PREFERENCES: tuple[str, ...] = (
    "ibm/granite-embedding-278m-multilingual",
    "ibm/granite-embedding-107m-multilingual",
    "ibm/slate-125m-english-rtrvr-v2",
    "ibm/slate-125m-english-rtrvr",
    "ibm/slate-30m-english-rtrvr-v2",
)


@dataclass(frozen=True)
class Resolved:
    """What the region gave us, and whether it was our first choice."""

    model_id: str
    preferred: bool
    reason: str


def family(model_id: str) -> str:
    """Provider prefix — 'ibm', 'meta-llama', 'mistralai'."""
    return model_id.split("/", 1)[0] if "/" in model_id else model_id


def pick(available: list[str], preferences: tuple[str, ...], configured: str) -> Resolved:
    """
    First preference the region hosts. The configured id is tried ahead of
    everything, so an explicit env override always wins when it is valid.
    """
    if not available:
        return Resolved(configured, True, "region model list unavailable; using configured id")

    for candidate in (configured, *preferences):
        if candidate in available:
            first = candidate == configured or candidate == preferences[0]
            return Resolved(candidate, first, "available in region")

    # Nothing we know about. Take what exists rather than refusing to start.
    return Resolved(
        available[0],
        False,
        f"none of the preferred models are hosted here; fell back to {available[0]}",
    )


def pick_baseline(available: list[str], creative_id: str, configured: str) -> Resolved:
    """
    The baseline anchors the distinctiveness score, so it must not be the model
    we are scoring. Two rules, in order of how much they matter:

      1. Never the *same id* as the creative model. That was the shipped bug:
         the baseline silently collapsed onto the creative model and the score
         became "distance from a colder version of myself", which is nothing.
      2. Prefer a *different provider family*, so the anchor is an independent
         idea of what bland writing sounds like rather than a sibling's.

    Only when the region offers literally one model do we accept the collapse,
    and then we say so out loud.
    """
    if not available:
        return Resolved(configured, True, "region model list unavailable; using configured id")

    if configured in available and family(configured) != family(creative_id):
        return Resolved(configured, True, "available in region")

    # Rule 2 — a different family.
    for candidate in BASELINE_PREFERENCES:
        if candidate in available and family(candidate) != family(creative_id):
            return Resolved(candidate, True, "different family from the creative model")

    for candidate in available:
        if family(candidate) != family(creative_id):
            return Resolved(candidate, False, "only same-family models were preferred")

    # Rule 1 — same family is unavoidable, but a different model still is not.
    for candidate in BASELINE_PREFERENCES:
        if candidate in available and candidate != creative_id:
            return Resolved(candidate, False, "region hosts one family; using a different model in it")

    for candidate in available:
        if candidate != creative_id:
            return Resolved(candidate, False, "region hosts one family; using a different model in it")

    return Resolved(
        creative_id,
        False,
        "region hosts a single usable model, so the baseline shares the creative model "
        "and distinctiveness is measured against a colder run of it",
    )


# ── Asking the region what it has ─────────────────────────────────────────────
# Deliberately duck-typed: this module never imports the watsonx SDK, so the
# selection logic above stays importable and testable without credentials or the
# package installed. We are handed an api_client and poke at it defensively,
# because the accessor names have moved between SDK versions and a rename must
# degrade to "use the configured id", never to a crash.

_TEXT_SPEC_METHODS = ("get_model_specs", "get_model_specs_with_prompt_tuning_support")
_EMBED_SPEC_METHODS = ("get_embeddings_model_specs", "get_embedding_model_specs")

_TEXT_FUNCTION = "text_generation"
_EMBED_FUNCTION = "embedding"


def _withdrawn(entry: dict) -> bool:
    """
    True if the spec says this model is gone. A withdrawn model is still listed,
    so selecting one would give us an id that exists on paper and 404s in
    practice. Shape-tolerant: an unrecognised lifecycle is treated as fine.
    """
    lifecycle = entry.get("lifecycle")
    if not isinstance(lifecycle, list):
        return False
    for state in lifecycle:
        if isinstance(state, dict) and state.get("id") == "withdrawn" and not state.get("start_date"):
            return True
        if state == "withdrawn":
            return True
    return False


def _serves(entry: dict, function_id: str | None) -> bool:
    """
    True if the model does the job we want. Absent or unrecognised `functions`
    means "don't know", and we keep the model rather than discarding a candidate
    over a payload shape we failed to parse.
    """
    if function_id is None:
        return True
    functions = entry.get("functions")
    if not isinstance(functions, list) or not functions:
        return True

    names: list[str] = []
    for fn in functions:
        if isinstance(fn, dict):
            value = fn.get("id") or fn.get("name")
            if isinstance(value, str):
                names.append(value)
        elif isinstance(fn, str):
            names.append(fn)
    return not names or function_id in names


def _ids_from(specs: object, function_id: str | None = None) -> list[str]:
    """Pull usable model ids out of a foundation_model_specs payload."""
    resources: object = specs
    if isinstance(specs, dict):
        resources = specs.get("resources", [])
    if not isinstance(resources, list):
        return []

    ids: list[str] = []
    for entry in resources:
        if isinstance(entry, dict):
            model_id = entry.get("model_id") or entry.get("id")
            if not isinstance(model_id, str) or not model_id:
                continue
            if _withdrawn(entry) or not _serves(entry, function_id):
                continue
            ids.append(model_id)
        elif isinstance(entry, str) and entry:
            ids.append(entry)
    return ids


def _query(api_client: object, method_names: tuple[str, ...], role: str, function_id: str) -> list[str]:
    catalogue = getattr(api_client, "foundation_models", None)
    if catalogue is None:
        logger.warning("SDK exposes no foundation_models catalogue; %s falls back to configured id.", role)
        return []

    for name in method_names:
        method = getattr(catalogue, name, None)
        if not callable(method):
            continue
        try:
            ids = _ids_from(method(), function_id)
        except Exception as exc:  # pragma: no cover - network/permissions dependent
            logger.warning("Listing %s models via %s failed (%s).", role, name, exc)
            continue
        if ids:
            logger.info("Region hosts %d %s model(s).", len(ids), role)
            return ids

    logger.warning("Could not list %s models in this region; falling back to configured id.", role)
    return []


def available_text_models(api_client: object) -> list[str]:
    """Text-generation model ids this project can actually call."""
    return _query(api_client, _TEXT_SPEC_METHODS, "text-generation", _TEXT_FUNCTION)


def available_embedding_models(api_client: object) -> list[str]:
    """Embedding model ids this project can actually call."""
    return _query(api_client, _EMBED_SPEC_METHODS, "embedding", _EMBED_FUNCTION)


@dataclass(frozen=True)
class Resolution:
    """The three ids the app will actually run with."""

    creative: Resolved
    baseline: Resolved
    embedding: Resolved


_cached: Resolution | None = None
_lock = threading.Lock()


def resolve(api_client: object, settings: object) -> Resolution:
    """
    Resolve all three roles against the region, once per process.

    Order matters: the creative model is chosen first because the baseline is
    then chosen *relative to it* — the baseline is the yardstick distinctiveness
    is measured against, so it should come from a different provider family.

    Locked because startup warms the three clients in parallel threads, and the
    region query is a network round-trip we only want to pay for once.
    """
    global _cached
    if _cached is not None:
        return _cached

    with _lock:
        if _cached is not None:
            return _cached

        text = available_text_models(api_client)
        embed = available_embedding_models(api_client)

        creative = pick(text, CREATIVE_PREFERENCES, getattr(settings, "generation_model_id", ""))
        baseline = pick_baseline(text, creative.model_id, getattr(settings, "baseline_model_id", ""))
        embedding = pick(embed, EMBEDDING_PREFERENCES, getattr(settings, "embedding_model_id", ""))

        for role, chosen in (("creative", creative), ("baseline", baseline), ("embedding", embedding)):
            level = logger.info if chosen.preferred else logger.warning
            level("Model role %s -> %s (%s)", role, chosen.model_id, chosen.reason)

        _cached = Resolution(creative=creative, baseline=baseline, embedding=embedding)
        return _cached


def reset_cache() -> None:
    """Test hook — forget the resolved ids."""
    global _cached
    _cached = None


def cached() -> Resolution | None:
    """
    What has already been resolved, or None if nothing has yet. Read-only, so
    reporting endpoints can show the truth without triggering a region query.
    """
    return _cached
