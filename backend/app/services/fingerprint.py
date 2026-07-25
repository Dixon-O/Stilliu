"""
fingerprint.py — Voice fingerprint builder.

Takes 2–5 past writing samples from the writer, splits them into
paragraphs, embeds all paragraphs, and returns a single centroid vector
that represents the writer's characteristic embedding space.

No persistence is needed for the POC — the centroid is computed per
request and passed back to the client (or recomputed on each analyze call).
"""
from __future__ import annotations
import logging
import numpy as np

from app.services.embeddings import embed_texts, split_into_paragraphs

logger = logging.getLogger(__name__)


def build_voice_centroid(samples: list[str]) -> np.ndarray:
    """
    Given a list of writing samples (strings), split each into paragraphs,
    embed every paragraph, and return the overall centroid vector.

    Args:
        samples: 2–5 strings of past writing from the author.

    Returns:
        1-D numpy array — the voice fingerprint centroid.
    """
    all_paragraphs: list[str] = []
    for sample in samples:
        paras = split_into_paragraphs(sample)
        all_paragraphs.extend(paras)

    if not all_paragraphs:
        raise ValueError("No non-empty paragraphs found in voice samples.")

    logger.info("Building voice fingerprint from %d paragraphs.", len(all_paragraphs))
    vectors = embed_texts(all_paragraphs)
    centroid = vectors.mean(axis=0)
    return centroid


def extract_style_signals(samples: list[str]) -> dict:
    """
    Extract lightweight textual style signals from writing samples.
    These are injected into generation prompts to anchor voice.

    Returns a dict with:
      - avg_sentence_length: average word count per sentence
      - vocabulary_richness: type-token ratio (unique words / total words)
      - punctuation_style: dominant punctuation characters observed
    """
    import re
    all_text = " ".join(samples)
    sentences = re.split(r"[.!?]+", all_text)
    sentences = [s.strip() for s in sentences if s.strip()]
    words = all_text.lower().split()

    avg_sent_len = round(sum(len(s.split()) for s in sentences) / max(len(sentences), 1), 1)
    vocab_richness = round(len(set(words)) / max(len(words), 1), 3)
    punct_counts = {p: all_text.count(p) for p in ["—", "–", ";", ":", "...", ","]}
    dominant_punct = [p for p, c in punct_counts.items() if c > 1]

    return {
        "avg_sentence_length": avg_sent_len,
        "vocabulary_richness": vocab_richness,
        "dominant_punctuation": dominant_punct or ["standard"],
    }
