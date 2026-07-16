"""Token usage metering: a fixed lifetime budget per user, covering both
ingestion (embeddings) and chat, so the shared Gemini key can't be run up by
one user.

Gemini's chat responses report exact token counts (usage_metadata), so chat
usage is metered precisely. Embedding calls report no usage data at all, so
embedding cost is estimated from character count (~4 chars/token is the
standard rule of thumb for English text) -- accurate enough for a usage cap
without spending an extra API call just to count tokens.
"""

from app import repository
from app.errors import QuotaExceededError
from app.logging_config import get_logger

logger = get_logger(__name__)

CHARS_PER_TOKEN_ESTIMATE = 4


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // CHARS_PER_TOKEN_ESTIMATE)


def get_usage(*, user_id: str) -> dict:
    return repository.get_usage(user_id=user_id)


def check_quota(*, user_id: str, needed_tokens: int = 1) -> None:
    """Raise QuotaExceededError if the user doesn't have enough tokens left."""
    usage = repository.get_usage(user_id=user_id)
    remaining = usage["tokens_limit"] - usage["tokens_used"]
    if remaining < needed_tokens:
        logger.warning(
            "quota_exceeded user_id=%s used=%d limit=%d needed=%d",
            user_id, usage["tokens_used"], usage["tokens_limit"], needed_tokens,
        )
        raise QuotaExceededError(
            f"Token quota exceeded ({usage['tokens_used']}/{usage['tokens_limit']} used). "
            "This account has used its available tokens."
        )


def record_usage(*, user_id: str, tokens: int) -> None:
    if tokens > 0:
        repository.add_tokens_used(user_id=user_id, tokens=tokens)
