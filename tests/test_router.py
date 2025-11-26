"""Tests for MCPToolRouter"""

import pytest

from src.core.router import MCPToolRouter
from src.core.exceptions import ToolNotFoundError, ServerNotFoundError


@pytest.mark.asyncio
class TestMCPToolRouter:
    """Test MCP Tool Router functionality"""

    async def test_router_initialization(self, router):
        """Test router initializes correctly"""
        assert router is not None
        assert router.max_retries == 2
        assert router.circuit_breaker_enabled is True
        assert router.enable_tool_namespacing is True
        assert len(router.servers) == 0
        assert len(router.tool_map) == 0

    async def test_router_list_servers_empty(self, router):
        """Test listing servers when none connected"""
        servers = router.list_servers()
        assert servers == []

    async def test_router_list_tools_empty(self, router):
        """Test listing tools when no servers connected"""
        tools = router.list_tools()
        assert tools == []

    async def test_router_get_server_info_not_found(self, router):
        """Test getting info for non-existent server"""
        info = router.get_server_info("nonexistent")
        assert info is None

    async def test_router_disconnect_nonexistent_server(self, router):
        """Test disconnecting non-existent server raises error"""
        with pytest.raises(ServerNotFoundError):
            await router.disconnect_server("nonexistent")

    async def test_router_execute_nonexistent_tool(self, router):
        """Test executing non-existent tool raises error"""
        with pytest.raises(ToolNotFoundError):
            await router.execute_tool("nonexistent_tool", {})

    async def test_router_get_tool_schema_not_found(self, router):
        """Test getting schema for non-existent tool"""
        schema = router.get_tool_schema("nonexistent")
        assert schema is None

    async def test_router_stats(self, router):
        """Test getting router statistics"""
        stats = router.get_router_stats()

        assert "servers" in stats
        assert "tools" in stats
        assert "circuit_breakers" in stats
        assert "schema_cache" in stats
        assert "connection_pool" in stats

        assert stats["servers"]["total"] == 0
        assert stats["tools"]["total"] == 0

    async def test_router_shutdown(self, router):
        """Test router shutdown"""
        await router.shutdown()

        # After shutdown, tool map and servers should still be accessible
        assert router.tool_map == {}
        assert router.servers == {}

    def test_router_tool_namespacing(self, router):
        """Test tool namespacing functionality"""
        # With namespacing enabled
        namespaced = router._get_tool_name("my_tool", "my_server")
        assert namespaced == "my_server:my_tool"

        # Get actual tool name
        actual = router._get_actual_tool_name(namespaced, "my_server")
        assert actual == "my_tool"

    def test_router_tool_namespacing_disabled(self):
        """Test tool namespacing when disabled"""
        router = MCPToolRouter(enable_tool_namespacing=False)

        # Without namespacing
        name = router._get_tool_name("my_tool", "my_server")
        assert name == "my_tool"

        actual = router._get_actual_tool_name(name, "my_server")
        assert actual == "my_tool"
