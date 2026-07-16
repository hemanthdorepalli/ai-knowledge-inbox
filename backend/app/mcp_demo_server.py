"""A tiny demo MCP server, mounted into this same app at /mcp-demo.

Exists so the MCP feature is testable without anyone needing to stand up
their own MCP server first. Exposes two safe, side-effect-free tools.
"""

import random
from datetime import datetime, timezone

from mcp.server.fastmcp import FastMCP

demo_mcp = FastMCP("ai-knowledge-inbox-demo", stateless_http=True)


@demo_mcp.tool()
def get_current_time() -> str:
    """Get the current date and time in UTC."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


@demo_mcp.tool()
def roll_dice(sides: int = 6) -> str:
    """Roll a die with the given number of sides (default 6) and return the result."""
    sides = max(2, min(sides, 1000))
    return f"Rolled a {sides}-sided die: {random.randint(1, sides)}"
