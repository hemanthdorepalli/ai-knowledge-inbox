import re
import time

import numpy as np
from google.genai import errors, types

from app.config import settings
from app.errors import LlmProviderError
from app.logging_config import get_logger
from app.services.gemini_client import client

logger = get_logger(__name__)

# Gemini's embedContent batch endpoint rejects more than 100 texts in one call.
# Large documents (a PDF chapter, a long article) routinely chunk into more
# than that, so we split into batches of this size and embed sequentially.
MAX_BATCH_SIZE = 100

# The free tier also caps embedding *requests* per minute (separate from the
# per-call batch-size limit above), so back-to-back batches for a big document
# can still get rate-limited. Retry with the delay Gemini suggests -- but only
# for the per-minute quota, which actually resets soon. A per-*day* quota
# won't recover no matter how long we wait within one request, so that one
# fails fast with a clear message instead of burning minutes on futile retries.
MAX_RETRIES = 6
DEFAULT_RETRY_DELAY_SECONDS = 20
_RETRY_DELAY_RE = re.compile(r"'retryDelay':\s*'(\d+)s'")
_QUOTA_ID_RE = re.compile(r"'quotaId':\s*'([^']+)'")


def _embed_batch(texts: list[str], task_type: str) -> list[np.ndarray]:
    last_exc: errors.APIError | None = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = client.models.embed_content(
                model=settings.embedding_model,
                contents=texts,
                config=types.EmbedContentConfig(
                    task_type=task_type,
                    output_dimensionality=settings.embedding_dim,  # 768, matches vector(768)
                ),
            )
            return [np.array(e.values, dtype=np.float32) for e in response.embeddings]
        except errors.APIError as exc:
            last_exc = exc
            if getattr(exc, "code", None) == 429:
                if _is_daily_quota_error(exc):
                    logger.error("embedding_daily_quota_exceeded count=%d error=%s", len(texts), exc)
                    raise LlmProviderError(
                        "The Gemini free-tier daily embedding quota has been used up. "
                        "Try again after the quota resets, or upgrade the Gemini API plan."
                    ) from exc
                if attempt < MAX_RETRIES:
                    delay = _extract_retry_delay(exc)
                    logger.warning(
                        "embedding_rate_limited count=%d attempt=%d/%d retry_in=%ds",
                        len(texts), attempt, MAX_RETRIES, delay,
                    )
                    time.sleep(delay)
                    continue
            logger.error("embedding_request_failed count=%d error=%s", len(texts), exc)
            raise LlmProviderError(f"Embedding generation failed: {exc}") from exc

    raise LlmProviderError(f"Embedding generation failed: {last_exc}") from last_exc


def _is_daily_quota_error(exc: errors.APIError) -> bool:
    match = _QUOTA_ID_RE.search(str(exc))
    return bool(match) and "PerDay" in match.group(1)


def _extract_retry_delay(exc: errors.APIError) -> int:
    match = _RETRY_DELAY_RE.search(str(exc))
    return int(match.group(1)) + 1 if match else DEFAULT_RETRY_DELAY_SECONDS


def _embed(texts: list[str], task_type: str) -> list[np.ndarray]:
    """Embed texts with a Gemini task type, batching to stay under Gemini's
    100-texts-per-request limit and retrying on the free tier's per-minute
    rate limit. Raises LlmProviderError on failure.

    Gemini embeddings are asymmetric: documents and queries get different
    optimizations. Using RETRIEVAL_DOCUMENT when storing and RETRIEVAL_QUERY
    when searching improves retrieval quality over embedding both the same way.
    """
    if not texts:
        return []

    embeddings: list[np.ndarray] = []
    for i in range(0, len(texts), MAX_BATCH_SIZE):
        embeddings.extend(_embed_batch(texts[i : i + MAX_BATCH_SIZE], task_type))
    return embeddings


def embed_texts(texts: list[str]) -> list[np.ndarray]:
    """Embed document chunks for storage."""
    return _embed(texts, task_type="RETRIEVAL_DOCUMENT")


def embed_query(text: str) -> np.ndarray:
    """Embed a single search query."""
    return _embed([text], task_type="RETRIEVAL_QUERY")[0]
