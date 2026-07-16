"""Shared security helpers: SSRF protection for any user-supplied URL the
backend will connect to (MCP servers today; the URL-fetch ingestion path is a
candidate to reuse this too).

Blocks requests to loopback, private, and link-local ranges -- the classic
SSRF targets (internal services, cloud metadata endpoints like
169.254.169.254) -- by resolving the hostname and checking every resolved
address, not just trusting the scheme/hostname string.
"""

import ipaddress
import socket
from urllib.parse import urlparse

from app.config import settings
from app.errors import AppError


class UnsafeUrlError(AppError):
    status_code = 422


def assert_safe_external_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise UnsafeUrlError("URL must start with http:// or https://")
    if not parsed.hostname:
        raise UnsafeUrlError("URL is missing a host")

    if settings.allow_local_mcp_urls:
        return

    try:
        addrs = socket.getaddrinfo(parsed.hostname, None)
    except socket.gaierror as exc:
        raise UnsafeUrlError(f"Could not resolve host: {parsed.hostname}") from exc

    for family, _, _, _, sockaddr in addrs:
        ip = ipaddress.ip_address(sockaddr[0])
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
            or ip.is_unspecified
        ):
            raise UnsafeUrlError(
                f"URL resolves to a non-public address ({ip}); internal/private hosts are not allowed"
            )
