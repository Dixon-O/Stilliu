"""
test_styles.py — the style preset library, style selection, and output cleaning.

These cover logic added when the library grew from 3 hardcoded personas to a
grouped, API-served set of 18. Two of them are regression tests for bugs that
actually shipped:

  * Markdown emphasis leaking into rendered direction text (and, worse, into the
    punctuation-density stylometry feature).
  * The style picker silently ignoring unknown names instead of erroring.
"""
from __future__ import annotations

import pytest

from app.models import WriterControls
from app.services import styles as S
from app.services.generation import _clean_output, _resolve_personas, _controls_clause


# ── Library integrity ─────────────────────────────────────────────────────────

def test_library_is_not_empty():
    assert len(S.STYLES) >= 16


def test_style_names_are_unique():
    names = [s["name"] for s in S.STYLES]
    assert len(names) == len(set(names)), "duplicate style name in STYLES"


def test_every_style_has_required_fields():
    for s in S.STYLES:
        for field in ("name", "group", "description", "instruction", "avoid"):
            assert field in s, f"{s.get('name', '?')} missing '{field}'"
        assert s["name"].strip(), "empty style name"
        assert s["description"].strip(), f"{s['name']} has no description"
        assert s["instruction"].strip(), f"{s['name']} has no instruction"


def test_every_style_belongs_to_a_declared_group():
    group_ids = {g["id"] for g in S.GROUPS}
    for s in S.STYLES:
        assert s["group"] in group_ids, f"{s['name']} has unknown group {s['group']}"


def test_every_group_has_at_least_one_style():
    used = {s["group"] for s in S.STYLES}
    for g in S.GROUPS:
        assert g["id"] in used, f"group {g['id']} has no styles"


def test_defaults_exist_in_the_library():
    for name in S.DEFAULT_STYLE_NAMES:
        assert name in S.STYLES_BY_NAME, f"default {name!r} is not a real style"


def test_backwards_compatible_aliases():
    # generation.py and older callers import these names.
    assert S.PERSONAS is S.STYLES
    assert S.PERSONAS_BY_NAME is S.STYLES_BY_NAME


# ── API payload ───────────────────────────────────────────────────────────────

def test_styles_payload_shape():
    payload = S.styles_payload()
    assert set(payload) == {"groups", "styles", "defaults", "max_selected"}
    assert len(payload["styles"]) == len(S.STYLES)
    assert payload["max_selected"] == S.MAX_SELECTED_STYLES


def test_styles_payload_resolves_group_labels():
    labels = {g["id"]: g["label"] for g in S.GROUPS}
    for item in S.styles_payload()["styles"]:
        assert item["group_label"] == labels[item["group"]]


def test_build_instruction_includes_the_ban_list():
    style = S.STYLES_BY_NAME["Sparse Minimalist"]
    out = S.build_instruction(style)
    assert style["instruction"] in out
    assert "Do not use:" in out
    assert style["avoid"] in out


def test_build_instruction_omits_empty_ban_list():
    out = S.build_instruction(
        {"name": "X", "instruction": "Style: X.", "avoid": ""}
    )
    assert "Do not use:" not in out


# ── Style selection ───────────────────────────────────────────────────────────

def test_no_selection_falls_back_to_defaults():
    chosen = _resolve_personas(WriterControls())
    assert [c["name"] for c in chosen] == S.DEFAULT_STYLE_NAMES


def test_selection_preserves_user_order():
    picked = ["Aphorist", "Telegraphic", "Deadpan Ironist"]
    chosen = _resolve_personas(WriterControls(personas=picked))
    assert [c["name"] for c in chosen] == picked


def test_unknown_names_are_ignored_not_fatal():
    # A stale chip in the UI must not fail the whole request.
    chosen = _resolve_personas(
        WriterControls(personas=["Aphorist", "Nonexistent Style"])
    )
    assert [c["name"] for c in chosen] == ["Aphorist"]


def test_all_unknown_names_fall_back_to_defaults():
    chosen = _resolve_personas(WriterControls(personas=["Nope", "Also Nope"]))
    assert [c["name"] for c in chosen] == S.DEFAULT_STYLE_NAMES


def test_duplicate_selections_are_collapsed():
    chosen = _resolve_personas(WriterControls(personas=["Aphorist", "Aphorist"]))
    assert [c["name"] for c in chosen] == ["Aphorist"]


def test_custom_style_is_appended_as_an_extra_direction():
    chosen = _resolve_personas(
        WriterControls(personas=["Aphorist"], custom_persona="Like a ship's log.")
    )
    assert [c["name"] for c in chosen] == ["Aphorist", "Your Custom Direction"]
    assert "ship's log" in chosen[-1]["instruction"]


def test_blank_custom_style_is_ignored():
    chosen = _resolve_personas(WriterControls(personas=["Aphorist"], custom_persona="   "))
    assert [c["name"] for c in chosen] == ["Aphorist"]


def test_selection_is_capped():
    everything = [s["name"] for s in S.STYLES]
    assert len(everything) > S.MAX_SELECTED_STYLES
    chosen = _resolve_personas(WriterControls(personas=everything))
    assert len(chosen) == S.MAX_SELECTED_STYLES


# ── Controls → prompt clause ──────────────────────────────────────────────────

@pytest.mark.parametrize("notch", ["nudge", "recast", "break"])
def test_each_divergence_notch_emits_a_clause(notch):
    clause = _controls_clause(WriterControls(divergence=notch))
    assert clause.strip(), f"divergence={notch} produced no instruction"


def test_divergence_notches_differ_from_one_another():
    clauses = {
        n: _controls_clause(WriterControls(divergence=n))
        for n in ("nudge", "recast", "break")
    }
    assert len(set(clauses.values())) == 3


def test_ai_cadence_ban_is_opt_in():
    off = _controls_clause(WriterControls(avoid_ai_cadence=False))
    on = _controls_clause(WriterControls(avoid_ai_cadence=True))
    assert "delve" not in off
    assert "delve" in on


def test_preserve_facts_clause_toggles():
    on = _controls_clause(WriterControls(preserve_facts=True))
    off = _controls_clause(WriterControls(preserve_facts=False))
    assert "Do NOT invent facts" in on
    assert "Do NOT invent facts" not in off


# ── Output cleaning (regression: Markdown leak) ───────────────────────────────

def test_strips_bold_asterisks():
    assert _clean_output("The **cost** nobody mentions.", "X") == "The cost nobody mentions."


def test_strips_underscore_bold_and_italic():
    assert _clean_output("A __firm__ and _quiet_ voice.", "X") == "A firm and quiet voice."


def test_strips_single_asterisk_italics():
    assert _clean_output("It was *never* the plan.", "X") == "It was never the plan."


def test_leaves_bare_asterisk_alone():
    # A lone asterisk isn't emphasis and shouldn't be swallowed.
    assert "*" in _clean_output("Rated 4 * out of 5.", "X")


def test_strips_headings():
    assert _clean_output("## The Turn\nShe left.", "X") == "The Turn\nShe left."


def test_normalises_markdown_bullets():
    out = _clean_output("- one\n- two", "X")
    assert out == "• one\n• two"
    assert "*" not in out and "- " not in out


def test_strips_code_fences():
    assert _clean_output("```\nShe left.\n```", "X") == "She left."


def test_strips_persona_label_prefix():
    assert _clean_output("Aphorist: She left.", "Aphorist") == "She left."


def test_strips_assistant_preamble():
    assert _clean_output("Certainly! She left.", "X") == "She left."


def test_strips_trailing_meta_commentary():
    out = _clean_output("She left.\n\nNote: I kept it short.", "X")
    assert out == "She left."


def test_clean_output_is_idempotent():
    once = _clean_output("The **cost** nobody mentions.", "X")
    assert _clean_output(once, "X") == once


def test_clean_output_preserves_plain_prose():
    prose = "She left. He stayed. Rain fell on the empty road."
    assert _clean_output(prose, "X") == prose
