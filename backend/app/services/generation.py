"""
generation.py — watsonx generation (HYBRID model strategy):
  1. The "bland AI default" baseline — Granite instruct model (falls back to the
     creative model if the Granite id is unavailable in-region). This is the
     anchor for the Distinctiveness measurement.
  2. Persona-constrained divergent directions — Llama-3-3-70b, run in parallel,
     shaped by the writer's controls (format, length, tone, audience, voice).

SDK clients are cached at module level — same pattern as embeddings.py.
"""
from __future__ import annotations
import logging
import re
from concurrent.futures import ThreadPoolExecutor, as_completed

from ibm_watsonx_ai import APIClient, Credentials
from ibm_watsonx_ai.foundation_models import ModelInference
from ibm_watsonx_ai.metanames import GenTextParamsMetaNames as GenParams

from app.config import get_settings

logger = logging.getLogger(__name__)

# ── Module-level client cache ────────────────────────────────────────────────
_generation_client: ModelInference | None = None
_baseline_client: ModelInference | None = None
_shared_api_client: APIClient | None = None


def _api_client() -> APIClient:
    global _shared_api_client
    if _shared_api_client is None:
        settings = get_settings()
        credentials = Credentials(url=settings.watsonx_url, api_key=settings.watsonx_api_key)
        _shared_api_client = APIClient(credentials=credentials, project_id=settings.watsonx_project_id)
    return _shared_api_client


def get_generation_client() -> ModelInference:
    global _generation_client
    if _generation_client is None:
        settings = get_settings()
        logger.info("Initialising creative generation client (one-time cold start)...")
        _generation_client = ModelInference(
            model_id=settings.generation_model_id,
            api_client=_api_client(),
            params={
                GenParams.MAX_NEW_TOKENS: 400,
                GenParams.TEMPERATURE: 0.8,
                GenParams.TOP_P: 0.95,
                GenParams.REPETITION_PENALTY: 1.15,
            },
        )
        logger.info("Creative generation client ready.")
    return _generation_client


def get_baseline_client() -> ModelInference:
    """
    Granite instruct client for the bland baseline. Falls back to the creative
    model id if the Granite model can't be instantiated in-region.
    """
    global _baseline_client
    if _baseline_client is None:
        settings = get_settings()
        for model_id in (settings.baseline_model_id, settings.generation_model_id):
            try:
                logger.info("Initialising baseline client with %s ...", model_id)
                _baseline_client = ModelInference(
                    model_id=model_id,
                    api_client=_api_client(),
                    params={GenParams.MAX_NEW_TOKENS: 300, GenParams.TEMPERATURE: 0.2},
                )
                break
            except Exception as exc:  # pragma: no cover - depends on region availability
                logger.warning("Baseline model %s unavailable (%s); trying fallback.", model_id, exc)
        if _baseline_client is None:  # pragma: no cover
            _baseline_client = get_generation_client()
    return _baseline_client

# ── Styles ────────────────────────────────────────────────────────────────────
# The preset library lives in styles.py so the API and the UI share one source
# of truth. PERSONAS/PERSONAS_BY_NAME are re-exported for backwards compatibility.

from app.services.styles import (  # noqa: E402
    STYLES,
    STYLES_BY_NAME,
    DEFAULT_STYLE_NAMES,
    MAX_SELECTED_STYLES,
    CUSTOM_STYLE_NAME,
    build_instruction,
    custom_style,
)

PERSONAS = STYLES
PERSONAS_BY_NAME = STYLES_BY_NAME


def _resolve_personas(controls) -> list[dict]:
    """
    Select which styles to run, in the order the writer picked them.

    Three cases, and the distinction between the last two is the whole point:

      * ``personas is None``  — the writer hasn't opened the picker yet, so fall
        back to the defaults and give them something to look at.
      * ``personas == []``    — the writer deliberately cleared the selection.
        Honour it and return nothing. Silently reinstating the defaults here is
        what used to make the picker feel like it was fighting the writer.
      * a non-empty list      — use it. Unknown names are dropped rather than
        raising, since the UI and the library can drift across a deploy and a
        stale chip shouldn't fail the request. If *nothing* in the list
        resolves, that's a drift bug rather than an intent to clear, so the
        defaults still apply.

    A custom brief is appended in every case, including the cleared one — it's
    an independent control and shouldn't need a preset selected to work. It
    occupies one of the ``MAX_SELECTED_STYLES`` slots rather than sitting past
    them, so a full preset selection loses its last preset rather than the brief.
    """
    names = getattr(controls, "personas", None)
    cleared = names is not None and len(names) == 0

    chosen: list[dict] = []
    seen: set[str] = set()
    for n in names or []:
        if n in STYLES_BY_NAME and n not in seen:
            chosen.append(STYLES_BY_NAME[n])
            seen.add(n)

    if not chosen and not cleared:
        chosen = [STYLES_BY_NAME[n] for n in DEFAULT_STYLE_NAMES if n in STYLES_BY_NAME]

    # Each direction is a parallel LLM call, so the total is capped. A custom
    # brief takes one of those slots rather than being appended past the cap:
    # it's the writer's most explicit instruction, so it must never be the thing
    # that gets silently dropped, and the UI gives it a tab either way.
    custom = (getattr(controls, "custom_persona", "") or "").strip()
    if custom:
        chosen = chosen[: MAX_SELECTED_STYLES - 1]
        chosen.append(custom_style(custom))

    return chosen[:MAX_SELECTED_STYLES]


def resolve_single_style(style_name: str, controls) -> dict | None:
    """
    Look up one style by name for POST /api/direction, including the writer's
    custom brief. Returns None if the name isn't a real style.
    """
    if style_name in STYLES_BY_NAME:
        return STYLES_BY_NAME[style_name]
    if style_name == CUSTOM_STYLE_NAME:
        brief = (getattr(controls, "custom_persona", "") or "").strip()
        if brief:
            return custom_style(brief)
    return None


# ── Prompt construction ───────────────────────────────────────────────────────

_FORMAT_CLAUSE = {
    "prose":    "Write flowing prose in complete paragraphs.",
    "bullets":  "Structure the output as tight bullet points.",
    "punchy":   "Keep it punchy — short paragraphs, high impact, nothing wasted.",
    "longform": "Develop the piece more fully with well-formed paragraphs.",
}
_LENGTH_CLAUSE = {
    "shorter": "Make it noticeably shorter than the draft — cut hard.",
    "match":   "Keep roughly the same length as the draft.",
    "longer":  "Expand it somewhat beyond the draft's length.",
}

# How far the rewrite is licensed to travel from the draft. Three named notches
# beat a bare 0–100 slider: each notch has a stated meaning, so the writer can
# predict the score delta before they click.
_DIVERGENCE_CLAUSE = {
    "nudge": (
        "Stay close to the draft's structure and sentence order. Apply the style "
        "through word choice and rhythm only. The reader should recognise this as "
        "the same piece, sharpened."
    ),
    "recast": (
        "Re-form the piece in this style. You may reorder, merge, and split "
        "sentences freely, but keep every point the draft makes."
    ),
    "break": (
        "Break the draft's shape completely and rebuild it in this style from the "
        "ground up. Keep the argument and the facts; discard the original "
        "structure, sentence order, and phrasing entirely. Take real risks."
    ),
}

# Grounded in measured frequency spikes in LLM-authored text and in the
# structural tells writers actually report. Applied as a global ban when the
# writer enables it, on top of any per-style ban list.
_AI_CADENCE_BAN = (
    "Avoid the standard markers of AI-generated prose: three-item lists and "
    "tricolons, the 'not just X but Y' construction, em-dash asides, a "
    "summarising final sentence, opening with 'In today's world', and the words "
    "'delve', 'leverage', 'tapestry', 'realm', 'testament', 'landscape', "
    "'navigate', 'underscore', 'crucial', 'multifaceted', 'commendable', "
    "'meticulous', 'intricate'."
)

# ── Narration controls ────────────────────────────────────────────────────────
# Each table deliberately omits its no-op value ("keep" / "standard"), so an
# untouched control contributes nothing to the prompt rather than contributing
# an instruction to change nothing — which models tend to over-obey.

_POV_CLAUSE = {
    "first":  "Write in the first person.",
    "second": "Address the reader directly in the second person.",
    "third":  "Write in the third person.",
}
_TENSE_CLAUSE = {
    "present": "Use the present tense throughout.",
    "past":    "Use the past tense throughout.",
}
_VOCABULARY_CLAUSE = {
    "plain": (
        "Keep the vocabulary plain and concrete. Prefer the shorter, older, "
        "more physical word over the longer Latinate one. No jargon."
    ),
    "elevated": (
        "Reach for precise and uncommon words where they do real work, but never "
        "for ornament alone. Precision, not decoration."
    ),
}
_RHYTHM_CLAUSE = {
    "uniform": (
        "Hold sentence lengths close to even so the rhythm is steady and unhurried."
    ),
    "varied": (
        "Vary sentence length deliberately — follow a long sentence with a short "
        "one so the rhythm breathes."
    ),
    "jagged": (
        "Make the rhythm deliberately uneven: very long sentences set against "
        "fragments, with abrupt stops."
    ),
}
_OPENING_CLAUSE = {
    "claim":        "Open with the boldest claim in the piece, stated flatly, in the first sentence.",
    "image":        "Open on a concrete image or physical detail before any abstraction.",
    "question":     "Open with a question that the rest of the piece answers.",
    "in_media_res": "Open mid-action with no setup, and let the reader catch up.",
}

_NARRATION_TABLES = (
    ("pov", _POV_CLAUSE),
    ("tense", _TENSE_CLAUSE),
    ("vocabulary", _VOCABULARY_CLAUSE),
    ("rhythm", _RHYTHM_CLAUSE),
    ("opening", _OPENING_CLAUSE),
)

#: Ceiling on the writer's own word lists — long lists dilute the instruction
#: and eat the context the draft needs.
_MAX_WORD_LIST = 25


def _split_word_list(raw: str) -> list[str]:
    """Parse a comma- or newline-separated control into clean, de-duplicated terms."""
    if not raw:
        return []
    out: list[str] = []
    seen: set[str] = set()
    for chunk in re.split(r"[,\n;]+", raw):
        term = chunk.strip().strip('"').strip("'").strip()
        key = term.lower()
        if term and key not in seen:
            out.append(term)
            seen.add(key)
    return out[:_MAX_WORD_LIST]


def _controls_clause(controls) -> str:
    """Turn writer controls into an explicit instruction clause."""
    if controls is None:
        return ""
    bits: list[str] = []
    fmt = getattr(controls, "fmt", "prose")
    if fmt in _FORMAT_CLAUSE and fmt != "prose":
        bits.append(_FORMAT_CLAUSE[fmt])
    length = getattr(controls, "length", "match")
    if length in _LENGTH_CLAUSE and length != "match":
        bits.append(_LENGTH_CLAUSE[length])
    divergence = getattr(controls, "divergence", "recast")
    if divergence in _DIVERGENCE_CLAUSE:
        bits.append(_DIVERGENCE_CLAUSE[divergence])
    tone = (getattr(controls, "tone", "") or "").strip()
    if tone:
        bits.append(f"Tone: {tone}.")
    audience = (getattr(controls, "audience", "") or "").strip()
    if audience:
        bits.append(f"Write for this audience: {audience}.")

    for attr, table in _NARRATION_TABLES:
        value = getattr(controls, attr, None)
        if value in table:
            bits.append(table[value])

    # The writer's own lists come last so they read as the final word, and are
    # phrased as hard constraints rather than preferences.
    keeps = _split_word_list(getattr(controls, "keep_phrases", "") or "")
    if keeps:
        quoted = "; ".join(f'"{k}"' for k in keeps)
        bits.append(
            f"These phrases must appear verbatim and unaltered, exactly as written: {quoted}."
        )
    banned = _split_word_list(getattr(controls, "banned_words", "") or "")
    if banned:
        bits.append(
            "Never use these words or phrases, in any form: " + ", ".join(banned) + "."
        )

    if getattr(controls, "avoid_ai_cadence", False):
        bits.append(_AI_CADENCE_BAN)
    if getattr(controls, "preserve_facts", True):
        bits.append(
            "Do NOT invent facts, names, statistics, quotes, publications, or places. "
            "Use only information present in the draft."
        )
    return (" " + " ".join(bits)) if bits else ""


def _voice_anchor(voice_samples: list[str] | None, controls) -> str:
    """
    Verbatim voice few-shot anchoring: show the model real author sentences so it
    can imitate cadence and diction, scaled by voice_strength.
    """
    if not voice_samples:
        return ""
    strength = getattr(controls, "voice_strength", 0.5) if controls else 0.5
    if strength <= 0.05:
        return ""
    # Take up to ~3 short excerpts as concrete anchors.
    excerpts = []
    for s in voice_samples[:3]:
        s = s.strip().replace("\n", " ")
        if s:
            excerpts.append(s[:220])
    if not excerpts:
        return ""
    joined = "\n".join(f"  • {e}" for e in excerpts)
    hug = (
        "Match this author's voice closely — mirror their sentence rhythm, diction, and habits."
        if strength >= 0.66 else
        "Let this author's voice inform the rewrite while still applying the persona."
        if strength >= 0.33 else
        "Keep a light echo of this author's voice."
    )
    return (
        f"\n\nThe author writes like this:\n{joined}\n{hug}"
    )


# ── Baseline (Granite) ────────────────────────────────────────────────────────

def generate_baseline(draft: str) -> str:
    """
    Generate a bland AI-default rewrite of the draft using Granite.
    This is the anchor for the Distinctiveness measurement.
    """
    settings = get_settings()
    if settings.demo_mode:
        return (
            "This text explores an important topic that many people find relevant today. "
            "There are several key points to consider. First, it is important to understand "
            "the context. Additionally, there are various factors that contribute to this. "
            "In conclusion, this subject deserves further attention and exploration."
        )

    model = get_baseline_client()
    prompt = (
        "You are a generic AI writing assistant with no distinctive style. "
        "Rewrite the following text in the most average, safe, corporate-bland way possible. "
        "Use cliches, passive voice, filler phrases, and hedge every claim. "
        "Output only the rewritten text, no commentary.\n\n"
        f"Text to rewrite:\n{draft}"
    )
    response = model.generate_text(prompt=prompt)
    return response.strip()


# ── Directions (Llama) ────────────────────────────────────────────────────────

def _clean_output(text: str, persona_name: str) -> str:
    """
    Strip model scaffolding and stray Markdown from a generated direction.

    Markdown removal matters twice over. It stops raw ``**bold**`` from showing
    up in the rendered card, and — less obviously — it stops the markup from
    corrupting the measurement: ``*``, ``#`` and ``_`` all count toward the
    punctuation-density stylometry feature, which was inflating distinctiveness
    for whichever direction happened to emit the most formatting.
    """
    text = text.strip()

    # Leading labels the model sometimes prepends despite being told not to.
    for prefix in (
        f"{persona_name}:", "Direction:", "Rewrite:", "Output:",
        "Rewritten text:", "Here is the rewritten text:", "Sure!", "Certainly!",
    ):
        if text.lower().startswith(prefix.lower()):
            text = text[len(prefix):].strip()

    # Fenced code blocks — keep the contents, drop the fence.
    text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
    text = re.sub(r"\n?```$", "", text)

    # Inline emphasis: **bold**, __bold__, *italic*, _italic_.
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text, flags=re.DOTALL)
    text = re.sub(r"__(.+?)__", r"\1", text, flags=re.DOTALL)
    text = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"\1", text, flags=re.DOTALL)
    text = re.sub(r"(?<![\w_])_(?!\s)(.+?)(?<!\s)_(?![\w_])", r"\1", text, flags=re.DOTALL)

    # ATX headings — the model occasionally sections its output.
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)

    # Normalise list bullets to a single character so the "bullets" format
    # control still works, without leaving Markdown asterisks behind.
    text = re.sub(r"^\s*[\*\-\+]\s+", "• ", text, flags=re.MULTILINE)

    # Trailing meta-commentary the model adds after the rewrite.
    text = re.sub(
        r"\n+\s*(Note|Notes|Explanation|Word count|Let me know)\b.*$",
        "",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )

    return text.strip()


def generate_single_direction(
    draft: str,
    persona: dict,
    voice_samples: list[str] | None,
    controls,
) -> dict:
    """Generate one persona direction. Called in parallel via ThreadPoolExecutor."""
    model = get_generation_client()
    prompt = (
        f"{build_instruction(persona)}{_controls_clause(controls)}"
        f"{_voice_anchor(voice_samples, controls)}\n\n"
        f"Draft to transform:\n{draft}\n\n"
        f"Write the rewritten text immediately. Plain prose only — no Markdown, "
        f"no asterisks, no headings. Do not add notes, labels, preamble, or "
        f"commentary of any kind. Stop after the rewrite."
    )
    try:
        text = _clean_output(model.generate_text(prompt=prompt), persona["name"])
    except Exception as exc:
        logger.error("Generation failed for persona %s: %s", persona["name"], exc)
        text = draft
    return {"name": persona["name"], "description": persona["description"], "text": text}


def generate_divergent_directions(
    draft: str,
    voice_samples: list[str] | None = None,
    controls=None,
) -> list[dict]:
    """Generate divergent directions IN PARALLEL. Wall-clock ≈ single generation."""
    settings = get_settings()
    if settings.demo_mode:
        return _fixture_directions()

    personas = _resolve_personas(controls)
    # An empty selection is a legitimate state now that clearing the picker is
    # honoured. Bail before ThreadPoolExecutor, which raises on max_workers=0.
    if not personas:
        return []

    results_map: dict[str, dict] = {}

    with ThreadPoolExecutor(max_workers=min(4, len(personas))) as pool:
        futures = {
            pool.submit(generate_single_direction, draft, persona, voice_samples, controls): persona
            for persona in personas
        }
        for future in as_completed(futures):
            persona = futures[future]
            try:
                results_map[persona["name"]] = future.result()
            except Exception as exc:
                logger.error("Persona %s failed: %s", persona["name"], exc)
                results_map[persona["name"]] = {
                    "name": persona["name"],
                    "description": persona["description"],
                    "text": draft,
                }

    return [results_map[p["name"]] for p in personas]


def regenerate_direction(
    draft: str,
    persona_name: str,
    persona_description: str,
    voice_samples: list[str] | None,
    controls,
    feedback: str,
) -> dict:
    """
    Regenerate one direction with corrective feedback appended — used by the
    refine loop when a direction scores poorly or fails the faithfulness guard.
    """
    settings = get_settings()
    if settings.demo_mode:
        return {"name": persona_name, "description": persona_description, "text": draft}

    # Resolve through the same path as a first-pass generation so a refined
    # custom direction keeps the writer's actual brief instead of falling back
    # to a brief reconstructed from its own truncated description.
    persona = resolve_single_style(persona_name, controls) or {
        "name": persona_name,
        "description": persona_description,
        "instruction": f"Style brief: {persona_description}",
        "avoid": "",
    }
    model = get_generation_client()
    prompt = (
        f"{build_instruction(persona)}{_controls_clause(controls)}"
        f"{_voice_anchor(voice_samples, controls)}\n\n"
        f"Previous attempt fell short: {feedback}\n"
        f"Fix exactly that while keeping the style.\n\n"
        f"Draft to transform:\n{draft}\n\n"
        f"Write only the rewritten text. Plain prose, no Markdown. "
        f"No notes, labels, or commentary."
    )
    try:
        text = _clean_output(model.generate_text(prompt=prompt), persona_name)
    except Exception as exc:
        logger.error("Regeneration failed for %s: %s", persona_name, exc)
        text = draft
    return {"name": persona_name, "description": persona_description, "text": text}


def _fixture_directions() -> list[dict]:
    return [
        {
            "name": "Sparse Minimalist",
            "description": "Short sentences. Nothing decorative. Meaning carried by what is left out.",
            "text": "AI erases voices. Not through malice — through averaging. Every writer who leans on it drifts toward the mean. The work gets cleaner. Blander. Safer. That's the cost nobody mentions.",
        },
        {
            "name": "The Arguer",
            "description": "Leads with a bold claim. Builds a case. Anticipates pushback and answers it.",
            "text": "AI homogenisation is the most underreported threat to writing culture right now. Yes, individual quality improves. But read a hundred AI-assisted essays and you'll find the same cadence, the same hedges, the same arc. The counterargument is that good ideas transcend style. That's wrong. Style is how an idea becomes yours.",
        },
        {
            "name": "Sensory-Led",
            "description": "Grounds ideas in physical sensation, texture, and concrete scene.",
            "text": "Paste your draft into any AI assistant. Watch it come back smoother, rounder, emptier — like river stones that lost their edges in the current. That's what homogenisation feels like from the inside: not loss, but a quiet erasure of the grain.",
        },
    ]

