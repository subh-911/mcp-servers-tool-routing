"""Server management endpoints"""

import structlog
from fastapi import APIRouter, HTTPException, Request, status

from src.api.models.requests import ConnectServerRequest
from src.api.models.responses import (
    ConnectServerResponse,
    DisconnectServerResponse,
    ErrorResponse,
    ServerInfoResponse,
    ServerListResponse,
)
from src.core.config import MCPServerConfig, MCPServerConnectionConfig
from src.core.exceptions import MCPToolRouterError, ServerNotFoundError

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/servers", tags=["Servers"])


@router.post(
    "",
    response_model=ConnectServerResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request"},
        500: {"model": ErrorResponse, "description": "Connection failed"},
    },
    summary="Connect to a new MCP server",
    description="Connect to a new MCP server and discover its tools",
)
async def connect_server(
    request_body: ConnectServerRequest,
    request: Request,
) -> ConnectServerResponse:
    """
    Connect to a new MCP server

    Args:
        request_body: Server connection request
        request: FastAPI request object

    Returns:
        Connection response with discovered tools

    Raises:
        HTTPException: If connection fails
    """
    router_instance = request.app.state.router

    logger.info("api_connect_server_request", server_name=request_body.name)

    try:
        # Create server config from request
        connection_config = MCPServerConnectionConfig(
            type=request_body.connection.type,
            command=request_body.connection.command,
            args=request_body.connection.args or [],
            url=request_body.connection.url,
            env=request_body.connection.env or {},
            headers=request_body.connection.headers or {},
        )

        server_config = MCPServerConfig(
            name=request_body.name,
            description=request_body.description or "",
            enabled=request_body.enabled,
            connection=connection_config,
            options=request_body.options.model_dump() if request_body.options else {},
        )

        # Connect to server
        tool_count = await router_instance.connect_server(
            name=request_body.name,
            server_config=server_config,
        )

        # Get discovered tools
        tools = router_instance.list_tools(server_name=request_body.name)

        logger.info(
            "api_connect_server_success",
            server_name=request_body.name,
            tool_count=tool_count,
        )

        return ConnectServerResponse(
            success=True,
            server_name=request_body.name,
            tool_count=tool_count,
            tools=tools,
            message=f"Successfully connected to server '{request_body.name}'",
        )

    except MCPToolRouterError as e:
        logger.error(
            "api_connect_server_failed",
            server_name=request_body.name,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=e.to_dict(),
        )

    except Exception as e:
        logger.error(
            "api_connect_server_unexpected_error",
            server_name=request_body.name,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "InternalServerError",
                "message": f"Unexpected error: {str(e)}",
                "details": {},
            },
        )


@router.delete(
    "/{server_name}",
    response_model=DisconnectServerResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Server not found"},
        500: {"model": ErrorResponse, "description": "Disconnection failed"},
    },
    summary="Disconnect from an MCP server",
    description="Disconnect from an MCP server and remove its tools",
)
async def disconnect_server(
    server_name: str,
    request: Request,
) -> DisconnectServerResponse:
    """
    Disconnect from an MCP server

    Args:
        server_name: Name of the server to disconnect
        request: FastAPI request object

    Returns:
        Disconnection response

    Raises:
        HTTPException: If server not found or disconnection fails
    """
    router_instance = request.app.state.router

    logger.info("api_disconnect_server_request", server_name=server_name)

    try:
        await router_instance.disconnect_server(server_name)

        logger.info("api_disconnect_server_success", server_name=server_name)

        return DisconnectServerResponse(
            success=True,
            server_name=server_name,
            message=f"Successfully disconnected server '{server_name}'",
        )

    except ServerNotFoundError as e:
        logger.warning("api_disconnect_server_not_found", server_name=server_name)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.to_dict(),
        )

    except MCPToolRouterError as e:
        logger.error(
            "api_disconnect_server_failed",
            server_name=server_name,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=e.to_dict(),
        )

    except Exception as e:
        logger.error(
            "api_disconnect_server_unexpected_error",
            server_name=server_name,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "InternalServerError",
                "message": f"Unexpected error: {str(e)}",
                "details": {},
            },
        )


@router.get(
    "",
    response_model=ServerListResponse,
    summary="List all connected servers",
    description="Get a list of all connected MCP servers",
)
async def list_servers(request: Request) -> ServerListResponse:
    """
    List all connected servers

    Args:
        request: FastAPI request object

    Returns:
        List of servers
    """
    router_instance = request.app.state.router

    logger.debug("api_list_servers_request")

    server_names = router_instance.list_servers()
    servers = []

    for server_name in server_names:
        server_info = router_instance.get_server_info(server_name)
        if server_info:
            servers.append(ServerInfoResponse(**server_info))

    logger.debug("api_list_servers_success", server_count=len(servers))

    return ServerListResponse(
        total=len(servers),
        servers=servers,
    )


@router.get(
    "/{server_name}",
    response_model=ServerInfoResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Server not found"},
    },
    summary="Get server information",
    description="Get detailed information about a specific server",
)
async def get_server(
    server_name: str,
    request: Request,
) -> ServerInfoResponse:
    """
    Get server information

    Args:
        server_name: Name of the server
        request: FastAPI request object

    Returns:
        Server information

    Raises:
        HTTPException: If server not found
    """
    router_instance = request.app.state.router

    logger.debug("api_get_server_request", server_name=server_name)

    server_info = router_instance.get_server_info(server_name)

    if not server_info:
        logger.warning("api_get_server_not_found", server_name=server_name)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "ServerNotFoundError",
                "message": f"Server '{server_name}' not found",
                "details": {"server_name": server_name},
            },
        )

    logger.debug("api_get_server_success", server_name=server_name)

    return ServerInfoResponse(**server_info)
