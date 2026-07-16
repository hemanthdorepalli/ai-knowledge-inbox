class AppError(Exception):
    """Base class for domain errors that map to a specific HTTP status code."""

    status_code = 500

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class UrlFetchError(AppError):
    """Raised when a source URL cannot be fetched or parsed into usable text."""

    status_code = 502


class ItemNotFoundError(AppError):
    status_code = 404


class AuthError(AppError):
    """Raised when a request has a missing, invalid, or expired auth token."""

    status_code = 401


class EmptyContentError(AppError):
    status_code = 422


class DocumentError(AppError):
    """Raised when an uploaded document is unsupported, too large, or unreadable."""

    status_code = 422


class LlmProviderError(AppError):
    """Raised when the embeddings or chat completion API call fails."""

    status_code = 502


class QuotaExceededError(AppError):
    """Raised when a user has used up their lifetime token budget."""

    status_code = 429
