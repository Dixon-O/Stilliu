"""
tests/test_scoring.py — Unit tests for the scoring service.

These are deterministic: we pass known vectors with known cosine distances
and assert the display scores land where the calibration model predicts.
"""
import numpy as np
import pytest
from app.services.scoring import compute_generic_score, compute_voice_score, score_summary


def _vec(values: list[float]) -> np.ndarray:
    return np.array(values, dtype=np.float32)


class TestComputeGenericScore:
    def test_identical_vectors_give_low_generic_score(self):
        """
        Zero cosine distance → draft IS the baseline → maximally generic.
        With invert=True: raw=0 (below FLOOR=0.05) → clamped → display=100.
        (High generic score means sounds like everyone.)
        """
        v = _vec([1.0, 0.0, 0.0])
        display, raw = compute_generic_score(v, v)
        assert raw == pytest.approx(0.0, abs=1e-5)
        # raw below FLOOR, invert=True → clamped to 100 (most generic)
        assert display == 100.0

    def test_orthogonal_vectors_give_high_distinctiveness(self):
        """
        Cosine distance of 1.0 → draft is maximally unlike baseline → highly distinctive.
        With invert=True: raw=1.0 (above CEIL=0.55) → clamped → display=0.
        (Low generic score means distinctive.)
        """
        a = _vec([1.0, 0.0])
        b = _vec([0.0, 1.0])
        display, raw = compute_generic_score(a, b)
        assert raw == pytest.approx(1.0, abs=1e-5)
        # raw above CEIL, invert=True → clamped to 0 (most distinctive)
        assert display == 0.0

    def test_moderate_distance_is_in_range(self):
        """A moderate cosine distance should land between 0 and 100."""
        a = _vec([1.0, 0.5, 0.0])
        b = _vec([0.8, 0.5, 0.3])
        display, raw = compute_generic_score(a, b)
        assert 0.0 <= display <= 100.0
        assert 0.0 <= raw <= 1.0

    def test_zero_vector_handled(self):
        """A zero vector should not raise — returns distance of 1.0."""
        a = _vec([0.0, 0.0, 0.0])
        b = _vec([1.0, 0.0, 0.0])
        display, raw = compute_generic_score(a, b)
        assert raw == pytest.approx(1.0, abs=1e-5)


class TestComputeVoiceScore:
    def test_same_vector_returns_low_voice_distance(self):
        """Draft identical to voice centroid → sounds exactly like the writer → ~0."""
        v = _vec([0.5, 0.5, 0.5])
        display, raw = compute_voice_score(v, v)
        assert raw == pytest.approx(0.0, abs=1e-5)
        assert display == 0.0

    def test_opposite_vector_returns_high_voice_distance(self):
        a = _vec([1.0, 0.0])
        b = _vec([0.0, 1.0])
        display, raw = compute_voice_score(a, b)
        assert display == 100.0


class TestScoreSummary:
    def test_returns_string(self):
        result = score_summary(65.0, 42.0)
        assert isinstance(result, str)
        assert "65" in result
        assert "42" in result

    def test_no_voice_samples(self):
        result = score_summary(40.0, None)
        assert "Voice" not in result
