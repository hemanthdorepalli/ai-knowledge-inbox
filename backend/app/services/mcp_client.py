"""Client for connecting to user-configured remote MCP servers.

Only remote (HTTP) MCP servers are supported -- never spawn a subprocess for
a user-supplied command, which would hand any user remote code execution on
this server. Every URL is validated by security.assert_safe_external_url
before we ever connect to it (SSRF protection).

Tool results returned from an MCP server are untrusted data: they get fed
back into the LLM's context as text, never executed or treated as
instructions from us.
"""

import asyncio

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

from app.errors import LlmProviderError
from app.logging_config import get_logger
from app.services.security import assert_safe_external_url

logger = get_logger(__name__)

CONNECT_TIMEOUT_SECONDS = 10.0


def _headers(auth_token: str | None) -> dict[str, str] | None:
    return {"Authorization": f"Bearer {auth_token}"} if auth_token else None


async def _list_tools_async(url: str, auth_token: str | None) -> list[dict]:
    async with streamablehttp_client(url, headers=_headers(auth_token), timeout=CONNECT_TIMEOUT_SECONDS) as (
        read, write, _,
    ):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.list_tools()
            return [
                {"name": t.name, "description": t.description or "", "input_schema": t.inputSchema}
                for t in result.tools
            ]


async def _call_tool_async(url: str, auth_token: str | None, tool_name: str, arguments: dict) -> str:
    async with streamablehttp_client(url, headers=_headers(auth_token), timeout=CONNECT_TIMEOUT_SECONDS) as (
        read, write, _,
    ):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(tool_name, arguments)
            parts = [c.text for c in result.content if hasattr(c, "text")]
            text = "\n".join(parts) if parts else "(tool returned no text content)"
            if result.isError:
                return f"Tool error: {text}"
            return text


def _describe(exc: BaseException) -> str:
    """Flatten an exception into a useful message.

    The MCP client runs inside an anyio task group, so real failures surface as
    ExceptionGroup("unhandled errors in a TaskGroup (1 sub-exception)") -- which
    tells nobody anything. Unwrap to the actual causes.
    """
    if isinstance(exc, BaseExceptionGroup):
        inner = "; ".join(_describe(e) for e in exc.exceptions)
        return inner or str(exc)
    text = str(exc).strip()
    return f"{type(exc).__name__}: {text}" if text else type(exc).__name__


def list_tools(*, url: str, auth_token: str | None = None) -> list[dict]:
    """Connect to an MCP server and return its tools. Raises LlmProviderError on failure."""
    assert_safe_external_url(url)
    try:
        return asyncio.run(_list_tools_async(url, auth_token))
    except Exception as exc:
        detail = _describe(exc)
        logger.error("mcp_list_tools_failed url=%s error=%s", url, detail, exc_info=True)
        raise LlmProviderError(f"Could not connect to MCP server: {detail}") from exc


def call_tool(*, url: str, auth_token: str | None, tool_name: str, arguments: dict) -> str:
    """Call a tool on an MCP server and return its text result."""
    assert_safe_external_url(url)
    try:
        return asyncio.run(_call_tool_async(url, auth_token, tool_name, arguments))
    except Exception as exc:
        detail = _describe(exc)
        logger.error("mcp_call_tool_failed url=%s tool=%s error=%s", url, tool_name, detail, exc_info=True)
        return f"Tool call failed: {detail}"
