"""Bridges a user's connected MCP servers into Gemini function calling.

We never let Gemini connect to an MCP server directly (it has a native
mcp_servers field, but that would hand our SSRF validation and execution
control to Google's infrastructure). Instead we describe each server's cached
tools as Gemini FunctionDeclarations, and when Gemini asks to call one, we
make the actual MCP call ourselves and feed the (untrusted) result back as
plain text -- never as instructions.
"""

from dataclasses import dataclass

from google.genai import types

from app import repository
from app.logging_config import get_logger
from app.schemas import ToolCallInfo
from app.services import mcp_client

logger = get_logger(__name__)


@dataclass
class _ServerRef:
    server_id: str
    name: str
    url: str
    auth_token: str | None


def build_gemini_tools(*, user_id: str) -> tuple[list[types.Tool] | None, dict[str, tuple[_ServerRef, str]]]:
    """Returns (tools_for_gemini, name_map). name_map maps the prefixed
    function name Gemini sees back to (server, real_tool_name), since
    multiple servers' tools share one flat namespace."""
    servers = repository.list_enabled_mcp_servers_with_auth(user_id=user_id)

    declarations: list[types.FunctionDeclaration] = []
    name_map: dict[str, tuple[_ServerRef, str]] = {}

    for i, server in enumerate(servers):
        ref = _ServerRef(
            server_id=server["id"], name=server["name"], url=server["url"], auth_token=server["auth_token"]
        )
        for tool in server["tools"] or []:
            # Prefix with a short server index (not the server name/id) to
            # keep function names simple and guaranteed valid, and to avoid
            # collisions if two servers expose a tool with the same name.
            prefixed_name = f"s{i}__{tool['name']}"
            name_map[prefixed_name] = (ref, tool["name"])
            declarations.append(
                types.FunctionDeclaration(
                    name=prefixed_name,
                    description=f"[{server['name']}] {tool.get('description', '')}",
                    parameters_json_schema=tool.get("input_schema") or {"type": "object", "properties": {}},
                )
            )

    if not declarations:
        return None, {}
    return [types.Tool(function_declarations=declarations)], name_map


def execute_tool_call(
    *, function_call: types.FunctionCall, name_map: dict[str, tuple[_ServerRef, str]]
) -> ToolCallInfo:
    entry = name_map.get(function_call.name)
    if entry is None:
        return ToolCallInfo(
            server_name="unknown", tool_name=function_call.name, arguments={},
            result="Tool not found (it may have been removed).",
        )

    server, real_tool_name = entry
    arguments = dict(function_call.args or {})
    logger.info("mcp_tool_call server=%s tool=%s args=%s", server.name, real_tool_name, arguments)

    result = mcp_client.call_tool(
        url=server.url, auth_token=server.auth_token, tool_name=real_tool_name, arguments=arguments
    )
    return ToolCallInfo(server_name=server.name, tool_name=real_tool_name, arguments=arguments, result=result)
