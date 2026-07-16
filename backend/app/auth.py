"""Authentication: turn a Supabase login token into a user id.

The frontend logs in with Google via Supabase and sends the resulting access
token on every request as `Authorization: Bearer <token>`. This dependency
verifies that token with Supabase and returns the authenticated user's id, which
every route then uses to scope data to that user.

We validate by calling Supabase's /auth/v1/user endpoint, which works no matter
how the project signs its tokens. Results are cached briefly so we don't call
Supabase on every single request. (A production optimization would be to verify
the JWT signature locally instead of the network round-trip.)
"""

import time

import httpx
from fastapi import Header

from app.config import settings
from app.errors import AuthError
from app.logging_config import get_logger

logger = get_logger(__name__)

_CACHE_TTL_SECONDS = 60
_cache: dict[str, tuple[float, str]] = {}  # token -> (expires_at, user_id)


def get_current_user_id(authorization: str = Header(default="")) -> str:
    if not authorization.lower().startswith("bearer "):
        raise AuthError("Missing or invalid Authorization header")
    token = authorization[7:].strip()
    if not token:
        raise AuthError("Missing bearer token")

    now = time.time()
    cached = _cache.get(token)
    if cached and cached[0] > now:
        return cached[1]

    try:
        response = httpx.get(
            f"{settings.supabase_url}/auth/v1/user",
            headers={"Authorization": f"Bearer {token}", "apikey": settings.supabase_anon_key},
            timeout=10.0,
        )
    except httpx.RequestError as exc:
        logger.error("auth_verify_failed error=%s", exc)
        raise AuthError("Could not verify token with the auth provider") from exc

    if response.status_code != 200:
        raise AuthError("Invalid or expired login token")

    user_id = response.json().get("id")
    if not user_id:
        raise AuthError("Token did not resolve to a user")

    _cache[token] = (now + _CACHE_TTL_SECONDS, user_id)
    return user_id
