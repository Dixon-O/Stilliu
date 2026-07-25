"""
scoring.py — Distance calculation and score normalisation.

The calibration corpus defines the floor/ceiling for display scores.
Raw cosine distances are real and defensible; the 0–100 display values
are linearly normalised against known anchors so they feel meaningful
to a non-technical user without being fake.

Calibration anchors (manually verified against Granite embeddings):
  GENERIC_FLOOR  — cosine distance of a human distinctive text vs its own
                   bland baseline (high distance = distinctive = low score)
  GENERIC_CEILING — cosine distance of an AI-generated text vs its own
                    baseline (low distance = generic = high score)
"""
from __future__ import annotations
import numpy as np
from app.services.embeddings import cosine_distance

# ── Calibration constants ────────────────────────────────────────────────────
# These are set conservatively so normal human writing maps to 20–80 on the
# display scale. Adjust after M2 live testing if needed.

# Generic distance: high raw distance → more distinctive → lower display score
GENERIC_DIST_FLOOR = 0.05    # raw dist at which we display ~0 (very generic)
GENERIC_DIST_CEIL = 0.55     # raw dist at which we display ~100 (very distinctive)

# Voice distance: low raw distance → sounds like you → lower display score
VOICE_DIST_FLOOR = 0.02      # raw dist at which we display ~0 (perfect match)
VOICE_DIST_CEIL = 0.60       # raw dist at which we display ~100 (very different)


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
