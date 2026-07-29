"""
test_model_registry.py — resolving model ids against what a region actually hosts.

The bug these guard against shipped: eu-gb hosts no Granite instruct model, so
the configured baseline silently fell back to the *creative* model. Baseline and
creative then became the same model at two temperatures, which means
Distinctiveness was measuring "distance from a colder version of myself" rather
than "distance from a generic LLM". The scores looked fine. They meant nothing.

These tests need no credentials and no SDK — model_registry deliberately never
imports ibm_watsonx_ai, so the selection logic stays testable anywhere.
"""
from __future__ import annotations

import pytest

from app.services import model_registry as R


# The real list eu-gb returned on 2026-07-29. Kept verbatim because it is the
# region that exposed the bug.
EU_GB = [
    "meta-llama/llama-3-3-70b-instruct",
    "meta-llama/llama-4-maverick-17b-128e-instruct-fp8",
    "mistralai/mistral-small-3-1-24b-instruct-2503",
]

CONFIGURED_CREATIVE = "meta-llama/llama-3-3-70b-instruct"
CONFIGURED_BASELINE = "ibm/granite-3-3-8b-instruct"
CONFIGURED_EMBEDDING = "ibm/granite-embedding-278m-multilingual"


@pytest.fixture(autouse=True)
def _clear_cache():
    R.reset_cache()
    yield
    R.reset_cache()


# ── family ────────────────────────────────────────────────────────────────────

def test_family_is_the_provider_prefix():
    assert R.family("ibm/granite-3-3-8b-instruct") == "ibm"
    assert R.family("meta-llama/llama-3-3-70b-instruct") == "meta-llama"
    assert R.family("mistralai/mistral-small-3-1-24b-instruct-2503") == "mistralai"


def test_family_tolerates_an_unprefixed_id():
    assert R.family("some-bare-model") == "some-bare-model"


# ── pick ──────────────────────────────────────────────────────────────────────

def test_configured_id_wins_when_the_region_has_it():
    """An explicit env override is a deliberate act; never second-guess it."""
    chosen = R.pick(EU_GB, R.CREATIVE_PREFERENCES, "mistralai/mistral-small-3-1-24b-instruct-2503")
    assert chosen.model_id == "mistralai/mistral-small-3-1-24b-instruct-2503"
    assert chosen.preferred


def test_falls_through_to_the_best_available_preference():
    available = ["meta-llama/llama-4-maverick-17b-128e-instruct-fp8", "mistralai/mistral-large"]
    chosen = R.pick(available, R.CREATIVE_PREFERENCES, CONFIGURED_CREATIVE)
    # llama-4-maverick sits above mistral-large in CREATIVE_PREFERENCES.
    assert chosen.model_id == "meta-llama/llama-4-maverick-17b-128e-instruct-fp8"


def test_takes_an_unknown_model_rather_than_refusing_to_start():
    chosen = R.pick(["some-provider/brand-new-model"], R.CREATIVE_PREFERENCES, CONFIGURED_CREATIVE)
    assert chosen.model_id == "some-provider/brand-new-model"
    assert not chosen.preferred


def test_empty_availability_keeps_the_configured_id():
    """If the query failed we know nothing, so behave exactly as before."""
    chosen = R.pick([], R.CREATIVE_PREFERENCES, CONFIGURED_CREATIVE)
    assert chosen.model_id == CONFIGURED_CREATIVE


# ── pick_baseline ─────────────────────────────────────────────────────────────

def test_baseline_avoids_the_creative_family_in_eu_gb():
    """The regression. Granite is absent, so the anchor must be mistral."""
    chosen = R.pick_baseline(EU_GB, CONFIGURED_CREATIVE, CONFIGURED_BASELINE)
    assert chosen.model_id == "mistralai/mistral-small-3-1-24b-instruct-2503"
    assert R.family(chosen.model_id) != R.family(CONFIGURED_CREATIVE)


def test_baseline_rejects_a_configured_id_from_the_creative_family():
    """Even an explicit override loses here — it would break the measurement."""
    chosen = R.pick_baseline(EU_GB, CONFIGURED_CREATIVE, "meta-llama/llama-4-maverick-17b-128e-instruct-fp8")
    assert R.family(chosen.model_id) != "meta-llama"


def test_baseline_honours_a_configured_id_from_another_family():
    available = EU_GB + [CONFIGURED_BASELINE]
    chosen = R.pick_baseline(available, CONFIGURED_CREATIVE, CONFIGURED_BASELINE)
    assert chosen.model_id == CONFIGURED_BASELINE


def test_baseline_shares_the_creative_model_only_as_a_last_resort():
    single_family = ["meta-llama/llama-3-3-70b-instruct", "meta-llama/llama-3-2-3b-instruct"]
    chosen = R.pick_baseline(single_family, CONFIGURED_CREATIVE, CONFIGURED_BASELINE)
    # A smaller sibling is still better than literally the same model.
    assert chosen.model_id == "meta-llama/llama-3-2-3b-instruct"


def test_baseline_falls_back_to_the_creative_model_when_nothing_else_exists():
    chosen = R.pick_baseline([CONFIGURED_CREATIVE], CONFIGURED_CREATIVE, CONFIGURED_BASELINE)
    assert chosen.model_id == CONFIGURED_CREATIVE
    assert not chosen.preferred


# ── _ids_from ─────────────────────────────────────────────────────────────────

def test_ids_parsed_from_a_specs_payload():
    payload = {"resources": [{"model_id": "a/one"}, {"model_id": "b/two"}]}
    assert R._ids_from(payload) == ["a/one", "b/two"]


def test_ids_parsed_from_a_bare_list_and_from_id_keys():
    assert R._ids_from([{"id": "a/one"}, "b/two"]) == ["a/one", "b/two"]


def test_ids_from_garbage_is_empty_not_an_exception():
    assert R._ids_from(None) == []
    assert R._ids_from({"resources": "nope"}) == []
    assert R._ids_from([{"no_id_here": 1}]) == []


def test_withdrawn_models_are_not_offered():
    """They are still listed. Selecting one gives an id that 404s on first call."""
    payload = {
        "resources": [
            {"model_id": "a/gone", "lifecycle": [{"id": "available"}, {"id": "withdrawn"}]},
            {"model_id": "b/here", "lifecycle": [{"id": "available"}]},
        ]
    }
    assert R._ids_from(payload) == ["b/here"]


def test_a_scheduled_future_withdrawal_is_still_usable_today():
    payload = {
        "resources": [
            {"model_id": "a/soon", "lifecycle": [{"id": "withdrawn", "start_date": "2027-01-01"}]},
        ]
    }
    assert R._ids_from(payload) == ["a/soon"]


def test_models_that_do_not_do_the_job_are_filtered_out():
    payload = {
        "resources": [
            {"model_id": "a/embed-only", "functions": [{"id": "embedding"}]},
            {"model_id": "b/generator", "functions": [{"id": "text_generation"}]},
        ]
    }
    assert R._ids_from(payload, "text_generation") == ["b/generator"]


def test_an_unparseable_functions_field_keeps_the_model():
    """Never discard a candidate because we failed to understand the payload."""
    payload = {"resources": [{"model_id": "a/one"}, {"model_id": "b/two", "functions": "???"}]}
    assert R._ids_from(payload, "text_generation") == ["a/one", "b/two"]


# ── resolve ───────────────────────────────────────────────────────────────────

class _Settings:
    generation_model_id = CONFIGURED_CREATIVE
    baseline_model_id = CONFIGURED_BASELINE
    embedding_model_id = CONFIGURED_EMBEDDING


class _Catalogue:
    """Stands in for api_client.foundation_models."""

    def __init__(self, text: list[str], embed: list[str]):
        self._text = text
        self._embed = embed
        self.calls = 0

    def get_model_specs(self):
        self.calls += 1
        return {"resources": [{"model_id": m} for m in self._text]}

    def get_embeddings_model_specs(self):
        return {"resources": [{"model_id": m} for m in self._embed]}


class _Client:
    def __init__(self, catalogue):
        self.foundation_models = catalogue


def test_resolve_in_eu_gb_gives_an_independent_baseline():
    catalogue = _Catalogue(EU_GB, [CONFIGURED_EMBEDDING])
    resolution = R.resolve(_Client(catalogue), _Settings())

    assert resolution.creative.model_id == "meta-llama/llama-3-3-70b-instruct"
    assert resolution.baseline.model_id == "mistralai/mistral-small-3-1-24b-instruct-2503"
    assert resolution.embedding.model_id == CONFIGURED_EMBEDDING


def test_resolve_queries_the_region_once():
    catalogue = _Catalogue(EU_GB, [CONFIGURED_EMBEDDING])
    client = _Client(catalogue)
    R.resolve(client, _Settings())
    R.resolve(client, _Settings())
    assert catalogue.calls == 1


def test_resolve_survives_an_sdk_without_a_catalogue():
    """A renamed accessor must degrade to the configured ids, never crash."""
    class _Bare:
        pass

    resolution = R.resolve(_Bare(), _Settings())
    assert resolution.creative.model_id == CONFIGURED_CREATIVE
    assert resolution.baseline.model_id == CONFIGURED_BASELINE
    assert resolution.embedding.model_id == CONFIGURED_EMBEDDING


def test_resolve_survives_a_catalogue_that_raises():
    class _Angry:
        def get_model_specs(self):
            raise RuntimeError("403 Forbidden")

        def get_embeddings_model_specs(self):
            raise RuntimeError("403 Forbidden")

    resolution = R.resolve(_Client(_Angry()), _Settings())
    assert resolution.creative.model_id == CONFIGURED_CREATIVE


def test_region_without_granite_embeddings_picks_a_slate_retriever():
    catalogue = _Catalogue(EU_GB, ["ibm/slate-125m-english-rtrvr-v2", "ibm/slate-30m-english-rtrvr-v2"])
    resolution = R.resolve(_Client(catalogue), _Settings())
    assert resolution.embedding.model_id == "ibm/slate-125m-english-rtrvr-v2"
