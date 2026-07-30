"""
scoring.py — Multi-axis scoring. HIGH = GOOD everywhere.

Three axes, each 0–100 where 100 is the best possible outcome:

  Distinctiveness  — how far the text departs from bland AI defaults.
                     Blends semantic distance (40%) + stylometric distance (60%).
                     60% weight on style because embeddings capture topic, not voice.

  Voice Match      — how closely the text sounds like the author.
                     Blends semantic proximity to voice centroid (50%) + style
                     proximity to voice samples (50%).

  On-Message       — semantic faithfulness to the original draft.
                     Pure embedding proximity; guards against hallucination drift.

Distinctiveness and Voice Match are returned as absolute scores AND as deltas vs
the draft, so the UI can show "this direction is +18 more distinctive than your
draft." On-message is reported against a fixed neutral midpoint instead: the
draft is trivially 100% on-message with itself, so a draft-relative delta would
carry no information.

All blend weights live in named constants below rather than inline, because the
ratios are the editorial argument this file exists to make.
"""
from __future__ import annotations
import numpy as np
from app.services.textutil import cosine_distance, clamp
from app.services.stylometry import style_distance, mean_style_distance

# ── Calibration anchors ───────────────────────────────────────────────────────
# Semantic (embedding cosine distance) ranges — from live Granite probe (M2).
# Distinctiveness: distance from generic baseline
_DIST_SEM_FLOOR = 0.09   # bland-vs-bland → score 0  (sounds like everyone)
_DIST_SEM_CEIL  = 0.50   # distinctive-vs-baseline → score 100

# Voice match: distance from author centroid
_VOICE_SEM_FLOOR = 0.10  # same-author → score 100  (perfect match)
_VOICE_SEM_CEIL  = 0.55  # different writer → score 0

# On-message: distance from original draft
_MSG_SEM_FLOOR = 0.05    # near-identical → score 100
_MSG_SEM_CEIL  = 0.45    # heavily rewritten → score 0

# Style distance is already in [0, 1] from stylometry.style_distance.
# No additional calibration needed; multiply by 100 to get display units.

# ── Blend weights ─────────────────────────────────────────────────────────────
# Named, not inline, because these two ratios *are* the editorial argument the
# product makes and anyone auditing the scores should find them in one place.
#
# Distinctiveness leans on style (60/40) because embeddings encode topic, not
# voice: two rewrites of the same subject sit close together in embedding space
# however different their prose. Weighting semantics higher would score a bold
# stylistic rewrite as generic, which was the original shipped defect.
#
# Voice match splits evenly (50/50) because a voice is legitimately both — the
# subjects someone returns to *and* the way they build a sentence. Neither half
# earns the tiebreak.
DIST_SEMANTIC_WEIGHT = 0.4
DIST_STYLE_WEIGHT    = 0.6

VOICE_SEMANTIC_WEIGHT = 0.5
VOICE_STYLE_WEIGHT    = 0.5

# On-message is deliberately unblended: it asks whether the meaning survived, and
# that is a purely semantic question. Stylometry would only add noise.

# The neutral midpoint the on-message delta is reported against. On-message has no
# draft-relative reading — the draft is trivially 100% on-message with itself — so
# the delta is stated against this midpoint instead.
MSG_NEUTRAL_MIDPOINT = 50.0


def _sem_to_display(raw: float, floor: float, ceil: float, high_is_far: bool) -> float:
    """
    Map a cosine distance to a 0–100 display score.
    high_is_far=True  → larger distance = higher score (distinctiveness).
    high_is_far=False → smaller distance = higher score (voice match, on-message).
    """
    span = ceil - floor if ceil > floor else 1.0
    normalised = clamp((raw - floor) / span, 0.0, 1.0) * 100.0
    return round(normalised if high_is_far else 100.0 - normalised, 1)


# ── Public scoring functions ──────────────────────────────────────────────────

def compute_distinctiveness(
    text_vector: np.ndarray,
    baseline_vector: np.ndarray,
    text_str: str,
    baseline_str: str,
) -> tuple[float, float, float]:
    """
    Returns (score_0_100, raw_semantic_dist, raw_style_dist).
    100 = maximally distinctive from the generic AI baseline.
    """
    raw_sem = cosine_distance(text_vector, baseline_vector)
    raw_sty = style_distance(text_str, baseline_str)

    sem_score = _sem_to_display(raw_sem, _DIST_SEM_FLOOR, _DIST_SEM_CEIL, high_is_far=True)
    sty_score = clamp(raw_sty * 100.0, 0.0, 100.0)

    score = round(DIST_SEMANTIC_WEIGHT * sem_score + DIST_STYLE_WEIGHT * sty_score, 1)
    return score, raw_sem, raw_sty


def compute_voice_match(
    text_vector: np.ndarray,
    voice_centroid: np.ndarray,
    text_str: str,
    voice_samples: list[str],
) -> tuple[float, float, float]:
    """
    Returns (score_0_100, raw_semantic_dist, raw_style_dist).
    100 = sounds exactly like the author.
    """
    raw_sem = cosine_distance(text_vector, voice_centroid)
    raw_sty = mean_style_distance(text_str, voice_samples) if voice_samples else 0.5

    sem_score = _sem_to_display(raw_sem, _VOICE_SEM_FLOOR, _VOICE_SEM_CEIL, high_is_far=False)
    sty_score = clamp((1.0 - raw_sty) * 100.0, 0.0, 100.0)  # invert: close = good

    score = round(VOICE_SEMANTIC_WEIGHT * sem_score + VOICE_STYLE_WEIGHT * sty_score, 1)
    return score, raw_sem, raw_sty


def compute_on_message(
    text_vector: np.ndarray,
    draft_vector: np.ndarray,
) -> tuple[float, float]:
    """
    Returns (score_0_100, raw_semantic_dist).
    100 = semantically faithful to the original draft.
    """
    raw_sem = cosine_distance(text_vector, draft_vector)
    score = _sem_to_display(raw_sem, _MSG_SEM_FLOOR, _MSG_SEM_CEIL, high_is_far=False)
    return score, raw_sem


def score_axes(
    *,
    draft_vector: np.ndarray,
    draft_str: str,
    baseline_vector: np.ndarray,
    baseline_str: str,
    voice_centroid: np.ndarray,
    voice_samples: list[str],
    direction_vector: np.ndarray,
    direction_str: str,
) -> dict:
    """
    Compute all three axes for a direction AND for the draft, returning
    absolute scores plus deltas (direction − draft, positive = improvement).

    Returned dict keys:
      distinctiveness, voice_match, on_message          — direction scores (0-100)
      draft_distinctiveness, draft_voice_match           — draft baselines
      delta_distinctiveness, delta_voice_match           — direction − draft
      delta_on_message                                   — direction − neutral midpoint
      raw_*                                              — raw distances for debugging
    """
    dir_dist,  dir_dist_sem,  dir_dist_sty  = compute_distinctiveness(
        direction_vector, baseline_vector, direction_str, baseline_str)
    dir_voice, dir_voice_sem, dir_voice_sty = compute_voice_match(
        direction_vector, voice_centroid, direction_str, voice_samples)
    dir_msg,   dir_msg_sem                  = compute_on_message(
        direction_vector, draft_vector)

    dft_dist,  _,  _ = compute_distinctiveness(
        draft_vector, baseline_vector, draft_str, baseline_str)
    dft_voice, _,  _ = compute_voice_match(
        draft_vector, voice_centroid, draft_str, voice_samples)

    return {
        # Direction absolute scores
        "distinctiveness":       dir_dist,
        "voice_match":           dir_voice,
        "on_message":            dir_msg,
        # Draft baselines (for delta display)
        "draft_distinctiveness": dft_dist,
        "draft_voice_match":     dft_voice,
        # Deltas — positive means the direction improved on the draft
        "delta_distinctiveness": round(dir_dist  - dft_dist,  1),
        "delta_voice_match":     round(dir_voice - dft_voice, 1),
        # Against a fixed midpoint, not the draft — see MSG_NEUTRAL_MIDPOINT.
        "delta_on_message":      round(dir_msg - MSG_NEUTRAL_MIDPOINT, 1),
        # Raw distances for debugging / calibration
        "raw_dist_sem":          round(dir_dist_sem,  4),
        "raw_dist_sty":          round(dir_dist_sty,  4),
        "raw_voice_sem":         round(dir_voice_sem, 4),
        "raw_voice_sty":         round(dir_voice_sty, 4),
        "raw_msg_sem":           round(dir_msg_sem,   4),
    }


def score_summary(axes: dict) -> str:
    """One-liner for prompt context and API responses."""
    d = axes["distinctiveness"]
    v = axes.get("voice_match")
    m = axes["on_message"]
    dist_label = "highly distinctive" if d >= 70 else "moderately distinctive" if d >= 45 else "leaning generic"
    msg_label  = "faithful"           if m >= 70 else "moderate drift"          if m >= 45 else "heavy drift"
    parts = [
        f"Distinctiveness {d:.0f}/100 ({dist_label})",
    ]
    if v is not None:
        voice_label = "strong voice match" if v >= 70 else "partial voice match" if v >= 45 else "voice drift"
        parts.append(f"Voice {v:.0f}/100 ({voice_label})")
    parts.append(f"On-message {m:.0f}/100 ({msg_label})")
    return " · ".join(parts)

