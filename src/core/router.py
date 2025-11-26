"""Core MCP Tool Router implementation"""

import asyncio
from typing import Any, Dict, List, Optional

import structlog
from tenacity import (
    RetryError,
    retry,
    stop_after_attempt,
    wait_exponential,
)

from src.core.circuit_breaker import CircuitBreaker
from src.core.config import MCPServerConfig, get_config
from src.core.exceptions import (
    CircuitBreakerError,
    ServerNotFoundError,
    ToolExecutionError,
    ToolNotFoundError,
)
from src.mcp.client import MCPClientPool
from src.mcp.schemas import ToolSchema, ToolSchemaCache

logger = structlog.get_logger(__name__)


class MCPToolRouter:
    """
    Production-quality MCP Tool Router.

    Manages connections to multiple MCP servers with:
    - Connection pooling
    - Circuit breakers
    - Retry logic with exponential backoff
    - Tool schema caching
    - Tool namespacing
    """

    def __init__(
        self,
        max_retries: int = 3,
        retry_backoff_base: int = 2,
        connection_timeout: int = 30,
        request_timeout: int = 60,
        max_connections_per_server: int = 10,
        enable_tool_namespacing: bool = True,
        namespace_separator: str = ":",
        circuit_breaker_enabled: bool = True,
        circuit_breaker_failure_threshold: int = 5,
        circuit_breaker_timeout: int = 60,
        circuit_breaker_half_open_max_calls: int = 3,
        schema_cache_ttl: int = 3600,
    ) -> None:
        """
        Initialize MCP Tool Router

        Args:
            max_retries: Maximum number of retry attempts
            retry_backoff_base: Base for exponential backoff
            connection_timeout: Connection timeout in seconds
            request_timeout: Request timeout in seconds
            max_connections_per_server: Max concurrent connections per server
            enable_tool_namespacing: Enable tool name prefixing
            namespace_separator: Separator for namespaced tools
            circuit_breaker_enabled: Enable circuit breakers
            circuit_breaker_failure_threshold: Failures before opening circuit
            circuit_breaker_timeout: Circuit breaker timeout in seconds
            circuit_breaker_half_open_max_calls: Max calls in half-open state
            schema_cache_ttl: Schema cache TTL in seconds
        """
        self.max_retries = max_retries
        self.retry_backoff_base = retry_backoff_base
        self.connection_timeout = connection_timeout
        self.request_timeout = request_timeout
        self.enable_tool_namespacing = enable_tool_namespacing
        self.namespace_separator = namespace_separator
        self.circuit_breaker_enabled = circuit_breaker_enabled

        # Initialize connection pool
        self.client_pool = MCPClientPool(
            max_connections_per_server=max_connections_per_server,
            connection_timeout=connection_timeout,
        )

        # Initialize schema cache
        self.schema_cache = ToolSchemaCache(
            ttl_seconds=schema_cache_ttl,
            max_size=1000,
        )

        # Server configurations
        self.servers: Dict[str, MCPServerConfig] = {}

        # Tool mapping: tool_name -> server_name
        self.tool_map: Dict[str, str] = {}

        # Circuit breakers per server
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self._circuit_breaker_config = {
            "failure_threshold": circuit_breaker_failure_threshold,
            "timeout_seconds": circuit_breaker_timeout,
            "half_open_max_calls": circuit_breaker_half_open_max_calls,
        }

        logger.info(
            "mcp_tool_router_initialized",
            max_retries=max_retries,
            circuit_breaker_enabled=circuit_breaker_enabled,
            tool_namespacing=enable_tool_namespacing,
        )

    async def connect_server(
        self,
        name: str,
        server_config: MCPServerConfig,
    ) -> int:
        """
        Connect to an MCP server and discover tools

        Args:
            name: Server name
            server_config: Server configuration

        Returns:
            Number of tools discovered

        Raises:
            MCPConnectionError: If connection fails
        """
        try:
            logger.info("connecting_to_server", server_name=name)

            # Store server config
            self.servers[name] = server_config

            # Create circuit breaker for this server
            if self.circuit_breaker_enabled and name not in self.circuit_breakers:
                self.circuit_breakers[name] = CircuitBreaker(
                    name=name,
                    **self._circuit_breaker_config,
                )

            # Get or create client
            client = await self.client_pool.get_client(name, server_config)

            # Discover tools
            tools = await client.list_tools()

            # Update tool map and cache schemas
            tool_count = 0
            for tool in tools:
                tool_name = self._get_tool_name(tool.name, name)
                self.tool_map[tool_name] = name

                # Cache tool schema
                schema = ToolSchema.from_mcp_tool(tool, name)
                self.schema_cache.set(schema)

                tool_count += 1

            logger.info(
                "server_connected",
                server_name=name,
                tool_count=tool_count,
            )

            return tool_count

        except Exception as e:
            logger.error(
                "server_connection_failed",
                server_name=name,
                error=str(e),
            )
            raise

    async def disconnect_server(self, name: str) -> None:
        """
        Disconnect from an MCP server

        Args:
            name: Server name

        Raises:
            ServerNotFoundError: If server not found
        """
        if name not in self.servers:
            raise ServerNotFoundError(name)

        try:
            logger.info("disconnecting_server", server_name=name)

            # Remove from client pool
            await self.client_pool.remove_client(name)

            # Remove tools from map
            tools_to_remove = [
                tool_name
                for tool_name, server_name in self.tool_map.items()
                if server_name == name
            ]
            for tool_name in tools_to_remove:
                del self.tool_map[tool_name]

            # Invalidate cached schemas
            self.schema_cache.invalidate_server(name)

            # Remove server config
            del self.servers[name]

            # Remove circuit breaker
            if name in self.circuit_breakers:
                del self.circuit_breakers[name]

            logger.info("server_disconnected", server_name=name)

        except Exception as e:
            logger.error(
                "server_disconnect_failed",
                server_name=name,
                error=str(e),
            )
            raise

    async def execute_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
    ) -> Any:
        """
        Execute a tool on the appropriate server with retry logic

        Args:
            tool_name: Name of the tool to execute
            arguments: Tool arguments

        Returns:
            Tool execution result

        Raises:
            ToolNotFoundError: If tool not found
            ToolExecutionError: If execution fails
            CircuitBreakerError: If circuit breaker is open
        """
        # Find server for tool
        if tool_name not in self.tool_map:
            raise ToolNotFoundError(tool_name)

        server_name = self.tool_map[tool_name]

        # Get actual tool name (remove namespace if present)
        actual_tool_name = self._get_actual_tool_name(tool_name, server_name)

        logger.debug(
            "executing_tool",
            tool_name=actual_tool_name,
            server_name=server_name,
        )

        # Execute with circuit breaker and retry logic
        try:
            if self.circuit_breaker_enabled and server_name in self.circuit_breakers:
                circuit_breaker = self.circuit_breakers[server_name]
                result = await circuit_breaker.call(
                    self._execute_with_retry,
                    server_name,
                    actual_tool_name,
                    arguments,
                )
            else:
                result = await self._execute_with_retry(
                    server_name,
                    actual_tool_name,
                    arguments,
                )

            logger.info(
                "tool_executed",
                tool_name=actual_tool_name,
                server_name=server_name,
            )

            return result

        except CircuitBreakerError:
            raise
        except RetryError as e:
            # All retries exhausted
            original_error = e.last_attempt.exception()
            raise ToolExecutionError(
                f"Tool execution failed after {self.max_retries} retries",
                tool_name=actual_tool_name,
                server_name=server_name,
                original_error=original_error,
            )
        except Exception as e:
            raise ToolExecutionError(
                f"Tool execution failed: {str(e)}",
                tool_name=actual_tool_name,
                server_name=server_name,
                original_error=e,
            )

    async def _execute_with_retry(
        self,
        server_name: str,
        tool_name: str,
        arguments: Dict[str, Any],
    ) -> Any:
        """
        Execute tool with retry logic using tenacity

        Args:
            server_name: Name of the server
            tool_name: Name of the tool
            arguments: Tool arguments

        Returns:
            Tool execution result
        """

        @retry(
            stop=stop_after_attempt(self.max_retries),
            wait=wait_exponential(
                multiplier=1,
                min=1,
                max=10,
                exp_base=self.retry_backoff_base,
            ),
            reraise=True,
        )
        async def _execute() -> Any:
            server_config = self.servers[server_name]
            client = await self.client_pool.get_client(server_name, server_config)

            # Execute with timeout
            result = await asyncio.wait_for(
                client.call_tool(tool_name, arguments),
                timeout=self.request_timeout,
            )

            return result

        return await _execute()

    def get_tool_schema(
        self,
        tool_name: str,
    ) -> Optional[ToolSchema]:
        """
        Get cached schema for a tool

        Args:
            tool_name: Name of the tool

        Returns:
            ToolSchema if found, None otherwise
        """
        if tool_name not in self.tool_map:
            return None

        server_name = self.tool_map[tool_name]
        actual_tool_name = self._get_actual_tool_name(tool_name, server_name)

        return self.schema_cache.get(actual_tool_name, server_name)

    def list_tools(
        self,
        server_name: Optional[str] = None,
    ) -> List[str]:
        """
        List available tools

        Args:
            server_name: Optional server name to filter tools

        Returns:
            List of tool names
        """
        if server_name:
            return [
                tool_name
                for tool_name, srv_name in self.tool_map.items()
                if srv_name == server_name
            ]
        return list(self.tool_map.keys())

    def list_servers(self) -> List[str]:
        """
        List connected servers

        Returns:
            List of server names
        """
        return list(self.servers.keys())

    def get_server_info(self, server_name: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a server

        Args:
            server_name: Name of the server

        Returns:
            Server information dictionary
        """
        if server_name not in self.servers:
            return None

        server_config = self.servers[server_name]
        tools = self.list_tools(server_name)

        info = {
            "name": server_name,
            "description": server_config.description,
            "enabled": server_config.enabled,
            "tool_count": len(tools),
            "tools": tools,
        }

        # Add circuit breaker status if enabled
        if self.circuit_breaker_enabled and server_name in self.circuit_breakers:
            cb = self.circuit_breakers[server_name]
            info["circuit_breaker"] = cb.get_status()

        return info

    def get_router_stats(self) -> Dict[str, Any]:
        """
        Get router statistics

        Returns:
            Statistics dictionary
        """
        return {
            "servers": {
                "total": len(self.servers),
                "connected": len(self.client_pool.get_connected_servers()),
                "list": self.list_servers(),
            },
            "tools": {
                "total": len(self.tool_map),
                "by_server": {
                    server: len(self.list_tools(server)) for server in self.servers
                },
            },
            "circuit_breakers": {
                name: cb.get_status()
                for name, cb in self.circuit_breakers.items()
            },
            "schema_cache": self.schema_cache.get_stats(),
            "connection_pool": self.client_pool.get_pool_stats(),
        }

    async def shutdown(self) -> None:
        """Shutdown router and disconnect all servers"""
        logger.info("shutting_down_router")

        # Disconnect all clients
        await self.client_pool.disconnect_all()

        # Clear caches
        self.schema_cache.clear()

        logger.info("router_shutdown_complete")

    def _get_tool_name(self, tool_name: str, server_name: str) -> str:
        """
        Get namespaced tool name

        Args:
            tool_name: Original tool name
            server_name: Server name

        Returns:
            Namespaced tool name if enabled, otherwise original name
        """
        if self.enable_tool_namespacing:
            return f"{server_name}{self.namespace_separator}{tool_name}"
        return tool_name

    def _get_actual_tool_name(self, namespaced_name: str, server_name: str) -> str:
        """
        Get actual tool name (remove namespace)

        Args:
            namespaced_name: Namespaced tool name
            server_name: Server name

        Returns:
            Actual tool name without namespace
        """
        if self.enable_tool_namespacing:
            prefix = f"{server_name}{self.namespace_separator}"
            if namespaced_name.startswith(prefix):
                return namespaced_name[len(prefix) :]
        return namespaced_name


async def create_router_from_config() -> MCPToolRouter:
    """
    Create router instance from configuration

    Returns:
        Configured MCPToolRouter instance
    """
    config = get_config()
    settings = config.settings

    router = MCPToolRouter(
        max_retries=settings.max_retries,
        retry_backoff_base=settings.retry_backoff_base,
        connection_timeout=settings.connection_timeout,
        request_timeout=settings.request_timeout,
        max_connections_per_server=settings.max_connections_per_server,
        enable_tool_namespacing=True,
        namespace_separator=":",
        circuit_breaker_enabled=True,
        circuit_breaker_failure_threshold=settings.circuit_breaker_failure_threshold,
        circuit_breaker_timeout=settings.circuit_breaker_timeout,
        circuit_breaker_half_open_max_calls=settings.circuit_breaker_half_open_max_calls,
        schema_cache_ttl=settings.schema_cache_ttl,
    )

    # Connect to configured servers
    for server_config in config.get_enabled_servers():
        try:
            await router.connect_server(server_config.name, server_config)
        except Exception as e:
            logger.error(
                "failed_to_connect_configured_server",
                server_name=server_config.name,
                error=str(e),
            )

    return router
