"""MCP client with connection pooling"""

import asyncio
from typing import Any, Dict, List, Optional

import structlog
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from src.core.config import MCPServerConfig
from src.core.exceptions import MCPConnectionError

logger = structlog.get_logger(__name__)


class MCPClient:
    """
    Wrapper around MCP ClientSession with connection management
    """

    def __init__(
        self,
        server_name: str,
        server_config: MCPServerConfig,
        connection_timeout: int = 30,
    ) -> None:
        self.server_name = server_name
        self.server_config = server_config
        self.connection_timeout = connection_timeout

        self._session: Optional[ClientSession] = None
        self._read_stream: Optional[Any] = None
        self._write_stream: Optional[Any] = None
        self._connected = False
        self._lock = asyncio.Lock()

    async def connect(self) -> None:
        """Establish connection to MCP server"""
        async with self._lock:
            if self._connected:
                logger.debug(
                    "mcp_client_already_connected",
                    server_name=self.server_name,
                )
                return

            try:
                logger.info(
                    "mcp_client_connecting",
                    server_name=self.server_name,
                    connection_type=self.server_config.connection.type,
                )

                if self.server_config.connection.type == "stdio":
                    await self._connect_stdio()
                else:
                    raise MCPConnectionError(
                        f"Unsupported connection type: {self.server_config.connection.type}",
                        server_name=self.server_name,
                    )

                self._connected = True
                logger.info(
                    "mcp_client_connected",
                    server_name=self.server_name,
                )

            except Exception as e:
                logger.error(
                    "mcp_client_connection_failed",
                    server_name=self.server_name,
                    error=str(e),
                )
                raise MCPConnectionError(
                    f"Failed to connect to server '{self.server_name}': {str(e)}",
                    server_name=self.server_name,
                    details={"error": str(e)},
                )

    async def _connect_stdio(self) -> None:
        """Connect using stdio transport"""
        if not self.server_config.connection.command:
            raise MCPConnectionError(
                "Command is required for stdio connection",
                server_name=self.server_name,
            )

        server_params = StdioServerParameters(
            command=self.server_config.connection.command,
            args=self.server_config.connection.args,
            env=self.server_config.connection.env or None,
        )

        # Create stdio client context
        self._read_stream, self._write_stream = stdio_client(server_params)
        self._session = ClientSession(self._read_stream, self._write_stream)

        # Initialize the session
        await self._session.initialize()

    async def disconnect(self) -> None:
        """Disconnect from MCP server"""
        async with self._lock:
            if not self._connected:
                return

            try:
                logger.info(
                    "mcp_client_disconnecting",
                    server_name=self.server_name,
                )

                if self._session:
                    # Close the session gracefully
                    # Note: MCP ClientSession doesn't have explicit close,
                    # cleanup happens via context managers
                    pass

                self._session = None
                self._read_stream = None
                self._write_stream = None
                self._connected = False

                logger.info(
                    "mcp_client_disconnected",
                    server_name=self.server_name,
                )

            except Exception as e:
                logger.error(
                    "mcp_client_disconnect_error",
                    server_name=self.server_name,
                    error=str(e),
                )

    async def list_tools(self) -> List[Any]:
        """
        List available tools from server

        Returns:
            List of tool objects
        """
        if not self._connected or not self._session:
            raise MCPConnectionError(
                f"Not connected to server '{self.server_name}'",
                server_name=self.server_name,
            )

        try:
            result = await self._session.list_tools()
            tools = result.tools if hasattr(result, "tools") else []

            logger.debug(
                "mcp_client_tools_listed",
                server_name=self.server_name,
                tool_count=len(tools),
            )

            return tools

        except Exception as e:
            logger.error(
                "mcp_client_list_tools_failed",
                server_name=self.server_name,
                error=str(e),
            )
            raise MCPConnectionError(
                f"Failed to list tools from server '{self.server_name}': {str(e)}",
                server_name=self.server_name,
                details={"error": str(e)},
            )

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """
        Execute a tool on the server

        Args:
            tool_name: Name of the tool to execute
            arguments: Arguments to pass to the tool

        Returns:
            Tool execution result
        """
        if not self._connected or not self._session:
            raise MCPConnectionError(
                f"Not connected to server '{self.server_name}'",
                server_name=self.server_name,
            )

        try:
            logger.debug(
                "mcp_client_calling_tool",
                server_name=self.server_name,
                tool_name=tool_name,
            )

            result = await self._session.call_tool(tool_name, arguments)

            logger.debug(
                "mcp_client_tool_called",
                server_name=self.server_name,
                tool_name=tool_name,
            )

            return result

        except Exception as e:
            logger.error(
                "mcp_client_tool_call_failed",
                server_name=self.server_name,
                tool_name=tool_name,
                error=str(e),
            )
            raise

    @property
    def is_connected(self) -> bool:
        """Check if client is connected"""
        return self._connected

    async def __aenter__(self) -> "MCPClient":
        """Async context manager entry"""
        await self.connect()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit"""
        await self.disconnect()


class MCPClientPool:
    """
    Connection pool for MCP clients.

    Manages multiple clients with connection pooling and reuse.
    """

    def __init__(
        self,
        max_connections_per_server: int = 10,
        connection_timeout: int = 30,
    ) -> None:
        """
        Initialize client pool

        Args:
            max_connections_per_server: Max concurrent connections per server
            connection_timeout: Connection timeout in seconds
        """
        self.max_connections_per_server = max_connections_per_server
        self.connection_timeout = connection_timeout

        # Single client per server (reuse connection)
        self._clients: Dict[str, MCPClient] = {}
        self._locks: Dict[str, asyncio.Lock] = {}

        logger.info(
            "mcp_client_pool_initialized",
            max_connections_per_server=max_connections_per_server,
            connection_timeout=connection_timeout,
        )

    async def get_client(
        self, server_name: str, server_config: MCPServerConfig
    ) -> MCPClient:
        """
        Get or create client for server

        Args:
            server_name: Name of the server
            server_config: Server configuration

        Returns:
            Connected MCP client
        """
        # Ensure we have a lock for this server
        if server_name not in self._locks:
            self._locks[server_name] = asyncio.Lock()

        async with self._locks[server_name]:
            # Check if client exists and is connected
            if server_name in self._clients:
                client = self._clients[server_name]
                if client.is_connected:
                    logger.debug(
                        "mcp_client_pool_reusing_client",
                        server_name=server_name,
                    )
                    return client
                else:
                    # Client exists but not connected, remove it
                    logger.warning(
                        "mcp_client_pool_client_disconnected",
                        server_name=server_name,
                    )
                    del self._clients[server_name]

            # Create new client
            logger.debug(
                "mcp_client_pool_creating_client",
                server_name=server_name,
            )

            client = MCPClient(
                server_name=server_name,
                server_config=server_config,
                connection_timeout=self.connection_timeout,
            )

            await client.connect()
            self._clients[server_name] = client

            return client

    async def remove_client(self, server_name: str) -> None:
        """
        Remove and disconnect client from pool

        Args:
            server_name: Name of the server
        """
        if server_name not in self._locks:
            return

        async with self._locks[server_name]:
            if server_name in self._clients:
                client = self._clients[server_name]
                await client.disconnect()
                del self._clients[server_name]

                logger.info(
                    "mcp_client_pool_client_removed",
                    server_name=server_name,
                )

    async def disconnect_all(self) -> None:
        """Disconnect all clients in pool"""
        for server_name in list(self._clients.keys()):
            await self.remove_client(server_name)

        logger.info("mcp_client_pool_all_clients_disconnected")

    def get_connected_servers(self) -> List[str]:
        """Get list of connected server names"""
        return [
            name for name, client in self._clients.items() if client.is_connected
        ]

    def get_pool_stats(self) -> Dict[str, Any]:
        """Get pool statistics"""
        return {
            "total_clients": len(self._clients),
            "connected_clients": len(self.get_connected_servers()),
            "max_connections_per_server": self.max_connections_per_server,
            "servers": self.get_connected_servers(),
        }
