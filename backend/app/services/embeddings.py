import numpy as np
from google.genai import errors, types

from app.config import settings
from app.errors import LlmProviderError
from app.logging_config import get_logger
from app.services.gemini_client import client

logger = get_logger(__name__)


def _embed(texts: list[str], task_type: str) -> list[np.ndarray]:
    """Embed a batch of texts with a Gemini task type. Raises LlmProviderError on failure.

    Gemini embeddings are asymmetric: documents and queries get different
    optimizations. Using RETRIEVAL_DOCUMENT when storing and RETRIEVAL_QUERY
    when searching improves retrieval quality over embedding both the same way.
    """
    if not texts:
        return []
    try:
        response = client.models.embed_content(
            model=settings.embedding_model,
            contents=texts,
            config=types.EmbedContentConfig(
                task_type=task_type,
                output_dimensionality=settings.embedding_dim,  # 768, matches vector(768)
            ),
        )
    except errors.APIError as exc:
        logger.error("embedding_request_failed count=%d error=%s", len(texts), exc)
        raise LlmProviderError(f"Embedding generation failed: {exc}") from exc

    return [np.array(embedding.values, dtype=np.float32) for embedding in response.embeddings]


def embed_texts(texts: list[str]) -> list[np.ndarray]:
    """Embed document chunks for storage."""
    return _embed(texts, task_type="RETRIEVAL_DOCUMENT")


def embed_query(text: str) -> np.ndarray:
    """Embed a single search query."""
    return _embed([text], task_type="RETRIEVAL_QUERY")[0]
