"""Token usage metering: a per-user budget on a rolling window, covering both
ingestion (embeddings) and chat, so one user can't run up the shared API keys.

Chat responses report exact token counts, so chat usage is metered precisely.
Embedding calls report no usage data at all, so embedding cost is estimated from
character count (~4 chars/token is the standard rule of thumb for English text)
-- accurate enough for a usage cap without spending an extra API call just to
count tokens, and it errs toward over-counting rather than under.
"""

from datetime import datetime, timedelta

from app import repository
from app.config import settings
from app.errors import QuotaExceededError
from app.logging_config import get_logger

logger = get_logger(__name__)

CHARS_PER_TOKEN_ESTIMATE = 4


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // CHARS_PER_TOKEN_ESTIMATE)


def resets_at(period_started_at: datetime) -> datetime:
    return period_started_at + timedelta(hours=settings.quota_window_hours)


def get_usage(*, user_id: str) -> dict:
    """Current usage. Rolls the window over first if it has expired."""
    return repository.get_usage(user_id=user_id)


def check_quota(*, user_id: str, needed_tokens: int = 1) -> None:
    """Raise QuotaExceededError if the user doesn't have enough tokens left."""
    usage = repository.get_usage(user_id=user_id)
    remaining = usage["tokens_limit"] - usage["tokens_used"]
    if remaining < needed_tokens:
        when = resets_at(usage["period_started_at"])
        logger.warning(
            "quota_exceeded user_id=%s used=%d limit=%d needed=%d resets_at=%s",
            user_id, usage["tokens_used"], usage["tokens_limit"], needed_tokens, when.isoformat(),
        )
        raise QuotaExceededError(
            f"Token quota exceeded ({usage['tokens_used']:,}/{usage['tokens_limit']:,} used). "
            f"Your quota resets at {when.strftime('%Y-%m-%d %H:%M UTC')}."
        )


def record_usage(*, user_id: str, tokens: int) -> None:
    if tokens > 0:
        repository.add_tokens_used(user_id=user_id, tokens=tokens)
