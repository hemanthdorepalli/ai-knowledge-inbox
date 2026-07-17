"""Bridges a user's connected MCP servers into the chat model's function calling.

We never let the model provider connect to an MCP server directly -- that would
hand our SSRF validation and execution control to a third party. Instead we
describe each server's cached tools as function declarations, and when the model
asks to call one, we make the actual MCP call ourselves and feed the (untrusted)
result back as plain text -- never as instructions.

Tools are declared in the OpenAI tool format, which is what Groq speaks.
MCP tool input schemas are already JSON Schema, so they drop straight in.
"""

import json
from dataclasses import dataclass

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


def build_chat_tools(*, user_id: str) -> tuple[list[dict] | None, dict[str, tuple[_ServerRef, str]]]:
    """Returns (tools, name_map). name_map maps the prefixed function name the
    model sees back to (server, real_tool_name), since multiple servers' tools
    share one flat namespace."""
    servers = repository.list_enabled_mcp_servers_with_auth(user_id=user_id)

    tools: list[dict] = []
    name_map: dict[str, tuple[_ServerRef, str]] = {}

    for i, server in enumerate(servers):
        ref = _ServerRef(
            server_id=server["id"], name=server["name"], url=server["url"], auth_token=server["auth_token"]
        )
        for tool in server["tools"] or []:
            # Prefix with a short server index (not the server name/id) to keep
            # function names simple and guaranteed valid, and to avoid collisions
            # if two servers expose a tool with the same name.
            prefixed_name = f"s{i}__{tool['name']}"
            name_map[prefixed_name] = (ref, tool["name"])
            tools.append(
                {
                    "type": "function",
                    "function": {
                        "name": prefixed_name,
                        "description": f"[{server['name']}] {tool.get('description', '')}",
                        "parameters": tool.get("input_schema") or {"type": "object", "properties": {}},
                    },
                }
            )

    if not tools:
        return None, {}
    return tools, name_map


def execute_tool_call(
    *, name: str, raw_arguments: str, name_map: dict[str, tuple[_ServerRef, str]]
) -> ToolCallInfo:
    entry = name_map.get(name)
    if entry is None:
        return ToolCallInfo(
            server_name="unknown", tool_name=name, arguments={},
            result="Tool not found (it may have been removed).",
        )

    server, real_tool_name = entry

    # The model returns arguments as a JSON string. Two things to be careful of:
    # a malformed string shouldn't take down the request, and for zero-argument
    # tools the model may send "null" (or ""), which json.loads turns into None
    # rather than an empty dict -- so coerce anything that isn't a dict to {}.
    try:
        parsed = json.loads(raw_arguments) if raw_arguments else {}
    except json.JSONDecodeError:
        logger.warning("mcp_tool_bad_arguments tool=%s raw=%r", real_tool_name, raw_arguments)
        return ToolCallInfo(
            server_name=server.name, tool_name=real_tool_name, arguments={},
            result="Tool call failed: the model produced invalid JSON arguments.",
        )
    arguments = parsed if isinstance(parsed, dict) else {}

    logger.info("mcp_tool_call server=%s tool=%s args=%s", server.name, real_tool_name, arguments)
    result = mcp_client.call_tool(
        url=server.url, auth_token=server.auth_token, tool_name=real_tool_name, arguments=arguments
    )
    return ToolCallInfo(server_name=server.name, tool_name=real_tool_name, arguments=arguments, result=result)
