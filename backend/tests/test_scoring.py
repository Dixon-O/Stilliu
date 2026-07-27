"""
tests/test_scoring.py — Unit tests for the multi-axis scoring service.

Deterministic: known vectors with known cosine distances, asserting the
0–100 display scores land where the calibration model predicts. HIGH = GOOD
on every axis.
"""
import numpy as np
import pytest
from app.services.scoring import (
    compute_distinctiveness, compute_voice_match, compute_on_message,
    score_axes, score_summary,
)

MINIMAL = "She left. He stayed. Rain fell."
VERBOSE = (
    "The extraordinarily complex situation unfolded with remarkable deliberateness; "
    "each participant contributed to the inexorable momentum of events."
)


def _vec(values):
    return np.array(values, dtype=np.float32)


class TestDistinctiveness:
    def test_identical_to_baseline_is_low(self):
        """Draft == bland baseline → not distinctive → low score."""
        v = _vec([1.0, 0.0, 0.0])
        score, raw_sem, raw_sty = compute_distinctiveness(v, v, MINIMAL, MINIMAL)
        assert raw_sem == pytest.approx(0.0, abs=1e-5)
        assert raw_sty == pytest.approx(0.0, abs=1e-5)
        assert score < 20  # near-zero semantic AND style distance

    def test_orthogonal_and_stylistically_far_is_high(self):
        a, b = _vec([1.0, 0.0]), _vec([0.0, 1.0])
        score, raw_sem, _ = compute_distinctiveness(a, b, MINIMAL, VERBOSE)
        assert raw_sem == pytest.approx(1.0, abs=1e-5)
        assert score > 60  # far on both axes

    def test_in_range(self):
        a, b = _vec([1.0, 0.5, 0.0]), _vec([0.8, 0.5, 0.3])
        score, _, _ = compute_distinctiveness(a, b, MINIMAL, VERBOSE)
        assert 0.0 <= score <= 100.0


class TestVoiceMatch:
    def test_identical_voice_is_high(self):
        """Text == voice centroid and same style → high voice match."""
        v = _vec([0.5, 0.5, 0.5])
        score, raw_sem, _ = compute_voice_match(v, v, MINIMAL, [MINIMAL])
        assert raw_sem == pytest.approx(0.0, abs=1e-5)
        assert score > 80

    def test_opposite_voice_is_low(self):
        a, b = _vec([1.0, 0.0]), _vec([0.0, 1.0])
        score, _, _ = compute_voice_match(a, b, MINIMAL, [VERBOSE])
        assert score < 50


class TestOnMessage:
    def test_identical_is_100(self):
        v = _vec([1.0, 0.0, 0.0])
        score, raw = compute_on_message(v, v)
        assert raw == pytest.approx(0.0, abs=1e-5)
        assert score == 100.0

    def test_orthogonal_is_0(self):
        a, b = _vec([1.0, 0.0]), _vec([0.0, 1.0])
        score, _ = compute_on_message(a, b)
        assert score == 0.0


class TestScoreAxes:
    def test_returns_all_keys_and_deltas(self):
        rng = np.random.default_rng(1)
        dv, bv, vc, dirv = (rng.standard_normal(64).astype(np.float32) for _ in range(4))
        axes = score_axes(
            draft_vector=dv, draft_str=MINIMAL,
            baseline_vector=bv, baseline_str=VERBOSE,
            voice_centroid=vc, voice_samples=[VERBOSE],
            direction_vector=dirv, direction_str=VERBOSE,
        )
        for key in ("distinctiveness", "voice_match", "on_message",
                    "delta_distinctiveness", "delta_voice_match", "delta_on_message"):
            assert key in axes
        for axis in ("distinctiveness", "voice_match", "on_message"):
            assert 0.0 <= axes[axis] <= 100.0

    def test_delta_is_direction_minus_draft(self):
        v = _vec([1.0, 0.0, 0.0])
        bv = _vec([0.0, 1.0, 0.0])
        axes = score_axes(
            draft_vector=v, draft_str=MINIMAL,
            baseline_vector=bv, baseline_str=VERBOSE,
            voice_centroid=v, voice_samples=[MINIMAL],
            direction_vector=v, direction_str=MINIMAL,
        )
        # direction == draft → distinctiveness delta should be ~0
        assert axes["delta_distinctiveness"] == pytest.approx(0.0, abs=0.1)


class TestScoreSummary:
    def test_contains_all_axes(self):
        axes = {"distinctiveness": 72.0, "voice_match": 60.0, "on_message": 80.0}
        result = score_summary(axes)
        assert "Distinctiveness" in result and "Voice" in result and "On-message" in result
        assert "72" in result
