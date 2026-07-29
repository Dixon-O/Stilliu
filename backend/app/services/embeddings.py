"""
embeddings.py — watsonx embedding calls and cosine distance utilities.

The embedding model is not hardcoded: which embedding models a region hosts
varies per account, and this is the one client the app cannot run without, so
the id is resolved against what the region actually serves (model_registry.py)
rather than named up front.

SDK client is cached at module level after first initialisation.
Cold-start on a fresh Python process takes ~8–10s (IAM token + SDK init).
Subsequent calls take ~1s. Caching eliminates the cold-start penalty on
every request.
"""
from __future__ import annotations
import logging
import numpy as np
from ibm_watsonx_ai import APIClient, Credentials
from ibm_watsonx_ai.foundation_models import Embeddings
from ibm_watsonx_ai.metanames import EmbedTextParamsMetaNames as EmbedParams

from app.config import get_settings
from app.services import model_registry
# Pure helpers live in textutil (no SDK import) so the measurement engine stays
# testable without credentials. Re-exported here for backward compatibility.
from app.services.textutil import cosine_distance, split_into_paragraphs  # noqa: F401

logger = logging.getLogger(__name__)

# ── Module-level client cache ────────────────────────────────────────────────
# Initialised once on first use. Eliminates the ~8s cold-start on every request.
_embedding_client: Embeddings | None = None


def get_embedding_client() -> Embeddings:
    global _embedding_client
    if _embedding_client is None:
        settings = get_settings()
        credentials = Credentials(
            url=settings.watsonx_url,
            api_key=settings.watsonx_api_key,
        )
        api_client = APIClient(credentials=credentials, project_id=settings.watsonx_project_id)

        resolution = model_registry.resolve(api_client, settings)
        candidates = [resolution.embedding.model_id]
        if settings.embedding_model_id not in candidates:
            candidates.append(settings.embedding_model_id)

        last_error: Exception | None = None
        for model_id in candidates:
            try:
                logger.info("Initialising embedding client with %s (one-time cold start)...", model_id)
                _embedding_client = Embeddings(
                    model_id=model_id,
                    api_client=api_client,
                    params={EmbedParams.TRUNCATE_INPUT_TOKENS: 512},
                )
                logger.info("Embedding client ready (%s).", model_id)
                break
            except Exception as exc:  # pragma: no cover - depends on region availability
                last_error = exc
                logger.warning("Embedding model %s unavailable (%s); trying fallback.", model_id, exc)

        if _embedding_client is None:  # pragma: no cover - no usable embedding model at all
            raise RuntimeError(
                "No embedding model could be initialised in this region. Tried: "
                f"{', '.join(candidates)}. Set EMBEDDING_MODEL_ID to one your account hosts, "
                f"or run with DEMO_MODE=true. Last error: {last_error}"
            )
    return _embedding_client


def embed_texts(texts: list[str]) -> np.ndarray:
    """
    Embed a list of text strings using the cached client.
    Returns a 2-D numpy array of shape (len(texts), embedding_dim).
    """
    settings = get_settings()
    if settings.demo_mode:
        rng = np.random.default_rng(seed=42)
        return rng.standard_normal((len(texts), 128)).astype(np.float32)

    client = get_embedding_client()
    response = client.embed_documents(texts=texts)
    return np.array(response, dtype=np.float32)


def mean_embedding(texts: list[str]) -> np.ndarray:
    """Embed all texts and return the mean centroid vector."""
    vectors = embed_texts(texts)
    return vectors.mean(axis=0)

