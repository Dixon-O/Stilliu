"""
tests/test_stylometry.py — Unit tests for the stylometry service.
"""
import numpy as np
import pytest
from app.services.stylometry import (
    style_features, style_vector, style_distance, mean_style_distance,
    FEATURE_NAMES,
)

MINIMAL = "She left. He stayed. Rain fell."
VERBOSE = (
    "The extraordinarily complex situation unfolded with remarkable, almost "
    "breathtaking, deliberateness; each participant, whether consciously or not, "
    "contributed to the inexorable momentum of events."
)


class TestStyleFeatures:
    def test_returns_all_feature_keys(self):
        feats = style_features(MINIMAL)
        assert set(feats.keys()) == set(FEATURE_NAMES)

    def test_minimal_shorter_sentences_than_verbose(self):
        assert style_features(MINIMAL)["mean_sentence_len"] < style_features(VERBOSE)["mean_sentence_len"]

    def test_verbose_longer_words(self):
        assert style_features(MINIMAL)["mean_word_len"] < style_features(VERBOSE)["mean_word_len"]

    def test_empty_text_does_not_raise(self):
        feats = style_features("")
        assert all(isinstance(v, float) for v in feats.values())


class TestStyleVector:
    def test_shape(self):
        v = style_vector(MINIMAL)
        assert v.shape == (len(FEATURE_NAMES),)

    def test_values_in_unit_range(self):
        v = style_vector(VERBOSE)
        assert np.all(v >= 0.0) and np.all(v <= 1.0)


class TestStyleDistance:
    def test_self_distance_is_zero(self):
        assert style_distance(MINIMAL, MINIMAL) == pytest.approx(0.0, abs=1e-6)

    def test_distance_in_unit_range(self):
        d = style_distance(MINIMAL, VERBOSE)
        assert 0.0 <= d <= 1.0

    def test_different_styles_nonzero(self):
        assert style_distance(MINIMAL, VERBOSE) > 0.1


class TestMeanStyleDistance:
    def test_empty_refs_returns_zero(self):
        assert mean_style_distance(MINIMAL, []) == 0.0

    def test_single_ref_equals_style_distance(self):
        expected = style_distance(MINIMAL, VERBOSE)
        assert mean_style_distance(MINIMAL, [VERBOSE]) == pytest.approx(expected, abs=1e-6)
