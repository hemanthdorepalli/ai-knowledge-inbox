"""A tiny demo MCP server, mounted into this same app at /mcp-demo.

Exists so the MCP feature is testable without anyone needing to stand up
their own MCP server first. Exposes two safe, side-effect-free tools.

Note on transport security: the MCP SDK enables DNS-rebinding protection by
default, which validates the incoming Host header against an allowlist that
defaults to localhost only. We keep that protection ON and explicitly allow
this deployment's public host (PUBLIC_HOST) -- otherwise requests to the
deployed URL are rejected with 421 Misdirected Request.
"""

import random
from datetime import datetime, timezone

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

from app.config import settings


def _allowed_hosts() -> list[str]:
    hosts = ["localhost", "localhost:8000", "127.0.0.1", "127.0.0.1:8000"]
    if settings.public_host:
        # Both bare host and :443 form, since proxies vary in what they forward.
        hosts += [settings.public_host, f"{settings.public_host}:443"]
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
