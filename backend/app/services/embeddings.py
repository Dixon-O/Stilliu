"""
embeddings.py — Granite embedding calls and cosine distance utilities.

All embedding work funnels through here so the rest of the app
never touches the raw SDK or numpy directly.
"""
from __future__ import annotations
import logging
import numpy as np
from ibm_watsonx_ai import APIClient, Credentials
from ibm_watsonx_ai.foundation_models import Embeddings
from ibm_watsonx_ai.metanames import EmbedTextParamsMetaNames as EmbedParams

from app.config import get_settings

logger = logging.getLogger(__name__)


def _get_embedding_client() -> Embeddings:
    settings = get_settings()
    credentials = Credentials(
        url=settings.watsonx_url,
        api_key=settings.watsonx_api_key,
    )
    client = APIClient(credentials=credentials, project_id=settings.watsonx_project_id)
    return Embeddings(
        model_id=settings.embedding_model_id,
        api_client=client,
        params={EmbedParams.TRUNCATE_INPUT_TOKENS: 512},
    )


def embed_texts(texts: list[str]) -> np.ndarray:
    """
    Embed a list of text strings and return a 2-D numpy array
    of shape (len(texts), embedding_dim).
    Each text is a paragraph or sentence-group.
    """
    settings = get_settings()
    if settings.demo_mode:
        # Return deterministic fake embeddings for offline use
        rng = np.random.default_rng(seed=42)
        return rng.standard_normal((len(texts), 128)).astype(np.float32)

    client = _get_embedding_client()
    response = client.embed_documents(texts=texts)
    vectors = np.array(response, dtype=np.float32)
    return vectors


def mean_embedding(texts: list[str]) -> np.ndarray:
    """
    Embed all texts and return the mean vector (centroid).
    Used for both draft representation and voice fingerprint.
    """
    vectors = embed_texts(texts)
    return vectors.mean(axis=0)


def cosine_distance(a: np.ndarray, b: np.ndarray) -> float:
    """
    Cosine distance in [0, 1].  0 = identical direction, 1 = orthogonal/opposite.
    """
    a_norm = np.linalg.norm(a)
    b_norm = np.linalg.norm(b)
    if a_norm == 0 or b_norm == 0:
        return 1.0
    similarity = float(np.dot(a, b) / (a_norm * b_norm))
    # Clamp for floating-point safety
    similarity = max(-1.0, min(1.0, similarity))
    return 1.0 - similarity


def split_into_paragraphs(text: str) -> list[str]:
    """
    Split a block of text into non-empty paragraphs.
    Falls back to treating the whole text as one unit if no breaks found.
    """
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if not paragraphs:
        paragraphs = [text.strip()]
    return paragraphs
