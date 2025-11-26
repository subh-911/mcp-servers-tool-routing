"""Tool discovery endpoints"""

from typing import Optional

import structlog
from fastapi import APIRouter, HTTPException, Query, Request, status

from src.api.models.responses import (
    ErrorResponse,
    ToolListResponse,
    ToolSchemaResponse,
)

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/tools", tags=["Discovery"])


@router.get(
    "",
    response_model=ToolListResponse,
    summary="List all available tools",
    description="Get a list of all available tools across all servers",
)
async def list_tools(
    request: Request,
    server_name: Optional[str] = Query(
        None, description="Filter tools by server name"
    ),
) -> ToolListResponse:
    """
    List all available tools

    Args:
        request: FastAPI request object
        server_name: Optional server name to filter tools

    Returns:
        List of tools
    """
    router_instance = request.app.state.router

    logger.debug("api_list_tools_request", server_name=server_name)

    if server_name:
        # Filter by server
        tools = router_instance.list_tools(server_name=server_name)
        by_server = {server_name: tools}
    else:
        # Get all tools
        tools = router_instance.list_tools()

        # Group by server
        by_server = {}
        for server in router_instance.list_servers():
            server_tools = router_instance.list_tools(server_name=server)
            if server_tools:
                by_server[server] = server_tools

    logger.debug(
        "api_list_tools_success",
        total_tools=len(tools),
        server_count=len(by_server),
    )

    return ToolListResponse(
        total=len(tools),
        tools=tools,
        by_server=by_server,
    )


@router.get(
    "/{tool_name}/schema",
    response_model=ToolSchemaResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Tool not found"},
    },
    summary="Get tool schema",
    description="Get the input schema for a specific tool",
)
async def get_tool_schema(
    tool_name: str,
    request: Request,
) -> ToolSchemaResponse:
    """
    Get tool schema

    Args:
        tool_name: Name of the tool
        request: FastAPI request object

    Returns:
        Tool schema

    Raises:
        HTTPException: If tool not found
    """
    router_instance = request.app.state.router

    logger.debug("api_get_tool_schema_request", tool_name=tool_name)

    schema = router_instance.get_tool_schema(tool_name)

    if not schema:
        logger.warning("api_get_tool_schema_not_found", tool_name=tool_name)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "ToolNotFoundError",
                "message": f"Tool '{tool_name}' not found",
                "details": {"tool_name": tool_name},
            },
        )

    logger.debug("api_get_tool_schema_success", tool_name=tool_name)

    return ToolSchemaResponse(
        name=schema.name,
        description=schema.description,
        server_name=schema.server_name,
        input_schema=schema.input_schema,
        cached_at=schema.cached_at,
    )
