from fastapi import APIRouter, Depends

from app import repository
from app.auth import get_current_user_id
from app.schemas import McpServerCreate, McpServerSummary
from app.services import mcp_client

router = APIRouter(tags=["mcp"])


@router.post("/mcp-servers", response_model=McpServerSummary, status_code=201)
def add_mcp_server(
    request: McpServerCreate, user_id: str = Depends(get_current_user_id)
) -> McpServerSummary:
    # Connect now so we fail fast with a clear error if the URL is unreachable,
    # unsafe, or not a valid MCP server -- and cache its tool list.
    tools = mcp_client.list_tools(url=request.url, auth_token=request.auth_token)
    server = repository.create_mcp_server(
        user_id=user_id, name=request.name, url=request.url, auth_token=request.auth_token, tools=tools
    )
    return server


@router.get("/mcp-servers", response_model=list[McpServerSummary])
def list_mcp_servers(user_id: str = Depends(get_current_user_id)) -> list[McpServerSummary]:
    return repository.list_mcp_servers(user_id=user_id)


@router.post("/mcp-servers/{server_id}/refresh", response_model=McpServerSummary)
def refresh_mcp_server(
    server_id: str, user_id: str = Depends(get_current_user_id)
) -> McpServerSummary:
    server = repository.get_mcp_server(user_id=user_id, server_id=server_id)
    tools = mcp_client.list_tools(url=server["url"], auth_token=server["auth_token"])
    return repository.update_mcp_server_tools(user_id=user_id, server_id=server_id, tools=tools)


@router.patch("/mcp-servers/{server_id}", response_model=McpServerSummary)
def toggle_mcp_server(
    server_id: str, enabled: bool, user_id: str = Depends(get_current_user_id)
) -> McpServerSummary:
    return repository.set_mcp_server_enabled(user_id=user_id, server_id=server_id, enabled=enabled)


@router.delete("/mcp-servers/{server_id}", status_code=204)
def delete_mcp_server(server_id: str, user_id: str = Depends(get_current_user_id)) -> None:
    repository.delete_mcp_server(user_id=user_id, server_id=server_id)
