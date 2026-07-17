"""A tiny demo MCP server, mounted into this same app at /mcp-demo.

Exists so the MCP feature is testable without anyone needing to stand up
their own MCP server first. Exposes two safe, side-effect-free tools.

Note on transport security: the MCP SDK enables DNS-rebinding protection by
default, which validates the incoming Host header against an allowlist that
defaults to localhost only. We keep that protection ON and allow this
deployment's own public host -- otherwise requests to the deployed URL are
rejected with 421 Misdirected Request.

The host is auto-detected from the platform (Render sets
RENDER_EXTERNAL_HOSTNAME), so this works out of the box; PUBLIC_HOST is only
needed as an override or on a platform we can't detect.
"""

import random
from datetime import datetime, timezone

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

from app.config import settings
from app.logging_config import get_logger

logger = get_logger(__name__)


def _allowed_hosts() -> list[str]:
    hosts = ["localhost", "127.0.0.1", "localhost:*", "127.0.0.1:*"]
    host = settings.public_hostname
    if host:
        # Bare host plus a port wildcard, since proxies differ in whether they
        # forward the port in the Host header.
        hosts += [host, f"{host}:*"]
        logger.info("mcp_demo_allowed_host host=%s", host)
    else:
        logger.warning(
            "mcp_demo_no_public_host: /mcp-demo will reject non-local requests with 421. "
            "Set PUBLIC_HOST to this service's hostname."
        )
    return hosts


demo_mcp = FastMCP(
    "ai-knowledge-inbox-demo",
    stateless_http=True,
    transport_security=TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=_allowed_hosts(),
        allowed_origins=["*"],
    ),
)


@demo_mcp.tool()
def get_current_time() -> str:
    """Get the current date and time in UTC."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


@demo_mcp.tool()
def roll_dice(sides: int = 6) -> str:
    """Roll a die with the given number of sides (default 6) and return the result."""
    sides = max(2, min(sides, 1000))
    return f"Rolled a {sides}-sided die: {random.randint(1, sides)}"
