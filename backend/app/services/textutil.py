"""
textutil.py — pure, dependency-light text/vector helpers.

Deliberately imports ONLY numpy + stdlib (no watsonx SDK) so the measurement
engine (scoring, stylometry, guardrails) can be imported and unit-tested with
zero network access or credentials.
"""
from __future__ import annotations
import numpy as np


def cosine_distance(a: np.ndarray, b: np.ndarray) -> float:
    """Cosine distance in [0, 2]; for typical embeddings ~[0, 1]. 0 = identical direction."""
    a_norm = np.linalg.norm(a)
    b_norm = np.linalg.norm(b)
    if a_norm == 0 or b_norm == 0:
        return 1.0
    similarity = float(np.dot(a, b) / (a_norm * b_norm))
    return 1.0 - max(-1.0, min(1.0, similarity))


def split_into_paragraphs(text: str) -> list[str]:
    """Split text into non-empty paragraphs (double-newline delimited)."""
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    return paragraphs if paragraphs else [text.strip()]


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))
