"""
scoring.py — Distance calculation and score normalisation.

The calibration corpus defines the floor/ceiling for display scores.
Raw cosine distances are real and defensible; the 0–100 display values
are linearly normalised against known anchors so they feel meaningful
to a non-technical user without being fake.

Calibration anchors — derived from live Granite embedding probe (M2):
  Corpus: bland AI pairs, distinctive human pairs, mixed medium.
  Embedding model: ibm/granite-embedding-278m-multilingual (768-dim).

  Observed distances:
    bland_ai vs bland_ai      → 0.089  (very generic, close together)
    distinct vs distinct       → 0.281  (distinctive but same style)
    bland vs distinct          → 0.461–0.501  (clear cross-style gap)
    draft vs its own baseline  → 0.348  (real-world typical case)

  Mapping intent:
    raw ~0.09 → display ~100 (very generic, matches its own bland baseline)
    raw ~0.35 → display ~50  (typical draft — in the interesting middle)
    raw ~0.50 → display ~0   (maximally distinctive, nothing like the baseline)
"""
from __future__ import annotations
import numpy as np
from app.services.embeddings import cosine_distance

# ── Calibration constants (live-probed, M2) ──────────────────────────────────

# Generic distance: high raw distance → more distinctive → lower display score
# Floor: bland-vs-bland baseline (0.089) → display 100 (very generic)
# Ceil:  distinctive-vs-baseline (0.50)  → display 0   (very distinctive)
GENERIC_DIST_FLOOR = 0.09    # raw dist → display 100 (sounds like everyone)
GENERIC_DIST_CEIL  = 0.50    # raw dist → display 0   (distinctly yours)

# Voice distance: low raw distance → sounds like you → lower display score
# Floor: same-author repeated phrase → near 0.10
# Ceil:  different writer entirely   → near 0.55
VOICE_DIST_FLOOR = 0.10      # raw dist → display 0   (perfect voice match)
VOICE_DIST_CEIL  = 0.55      # raw dist → display 100 (sounds unlike you)


def _normalise(raw: float, floor: float, ceil: float, invert: bool = False) -> float:
    """
    Linearly map raw ∈ [floor, ceil] to display ∈ [0, 100].
    Clamps values outside the calibrated range.
    If invert=True, a higher raw value → lower display score.
    """
    clamped = max(floor, min(ceil, raw))
    normalised = (clamped - floor) / (ceil - floor) * 100.0
    if invert:
        normalised = 100.0 - normalised
    return round(normalised, 1)


def compute_generic_score(
    draft_vector: np.ndarray,
    baseline_vector: np.ndarray,
) -> tuple[float, float]:
    """
    Returns (display_score, raw_distance).
    display_score: 0 = maximally distinctive, 100 = sounds like bland AI default.
    High raw distance → low display score (distinctive).
    Low raw distance → high display score (generic).
    """
    raw = cosine_distance(draft_vector, baseline_vector)
    # High distance from baseline = distinctive = LOW generic score → invert=True
    display = _normalise(raw, GENERIC_DIST_FLOOR, GENERIC_DIST_CEIL, invert=True)
    return display, raw


def compute_voice_score(
    draft_vector: np.ndarray,
    voice_centroid: np.ndarray,
) -> tuple[float, float]:
    """
    Returns (display_score, raw_distance).
    display_score: 0 = sounds exactly like you, 100 = sounds nothing like you.
    Low raw distance → low display score (sounds like you).
    """
    raw = cosine_distance(draft_vector, voice_centroid)
    # Low distance from voice = sounds like you = LOW voice-distance score → invert=False
    display = _normalise(raw, VOICE_DIST_FLOOR, VOICE_DIST_CEIL, invert=False)
    return display, raw


def score_summary(generic_display: float, voice_display: float | None) -> str:
    """
    Returns a human-readable one-liner for the score state.
    Used in API responses and as prompt context.
    """
    g = generic_display
    label = (
        "highly distinctive" if g < 30 else
        "moderately distinctive" if g < 55 else
        "leaning generic" if g < 75 else
        "strongly generic"
    )
    base = f"Generic score: {g:.0f}/100 ({label})"
    if voice_display is not None:
        v = voice_display
        voice_label = (
            "clearly your voice" if v < 30 else
            "mostly your voice" if v < 55 else
            "drifting from your voice" if v < 75 else
            "significantly unlike your voice"
        )
        return f"{base} · Voice drift: {v:.0f}/100 ({voice_label})"
    return base
