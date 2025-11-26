"""Tool schema caching for MCP clients"""

import time
from typing import Any, Dict, Optional

import structlog
from cachetools import TTLCache

logger = structlog.get_logger(__name__)


class ToolSchema:
    """Represents a tool schema with metadata"""

    def __init__(
        self,
        name: str,
        description: str,
        input_schema: Dict[str, Any],
        server_name: str,
    ) -> None:
        self.name = name
        self.description = description
        self.input_schema = input_schema
        self.server_name = server_name
        self.cached_at = time.time()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
            "server_name": self.server_name,
            "cached_at": self.cached_at,
        }

    @classmethod
    def from_mcp_tool(cls, tool: Any, server_name: str) -> "ToolSchema":
        """Create ToolSchema from MCP tool object"""
        return cls(
            name=tool.name,
            description=tool.description or "",
            input_schema=tool.inputSchema if hasattr(tool, "inputSchema") else {},
            server_name=server_name,
        )


class ToolSchemaCache:
    """
    Cache for tool schemas with TTL support.

    Prevents re-fetching tool schemas on every request.
    """

    def __init__(self, ttl_seconds: int = 3600, max_size: int = 1000) -> None:
        """
        Initialize schema cache

        Args:
            ttl_seconds: Time-to-live for cached schemas
            max_size: Maximum number of schemas to cache
        """
        self._cache: TTLCache = TTLCache(maxsize=max_size, ttl=ttl_seconds)
        self.ttl_seconds = ttl_seconds
        self.max_size = max_size
        self._hits = 0
        self._misses = 0

        logger.info(
            "tool_schema_cache_initialized",
            ttl_seconds=ttl_seconds,
            max_size=max_size,
        )

    def get(self, tool_name: str, server_name: str) -> Optional[ToolSchema]:
        """
        Get tool schema from cache

        Args:
            tool_name: Name of the tool
            server_name: Name of the server

        Returns:
            ToolSchema if found, None otherwise
        """
        cache_key = self._make_key(tool_name, server_name)
        schema = self._cache.get(cache_key)

        if schema:
            self._hits += 1
            logger.debug(
                "tool_schema_cache_hit",
                tool_name=tool_name,
                server_name=server_name,
            )
        else:
            self._misses += 1
            logger.debug(
                "tool_schema_cache_miss",
                tool_name=tool_name,
                server_name=server_name,
            )

        return schema

    def set(self, schema: ToolSchema) -> None:
        """
        Store tool schema in cache

        Args:
            schema: ToolSchema to cache
        """
        cache_key = self._make_key(schema.name, schema.server_name)
        self._cache[cache_key] = schema

        logger.debug(
            "tool_schema_cached",
            tool_name=schema.name,
            server_name=schema.server_name,
        )

    def invalidate(self, tool_name: str, server_name: str) -> None:
        """
        Invalidate cached schema

        Args:
            tool_name: Name of the tool
            server_name: Name of the server
        """
        cache_key = self._make_key(tool_name, server_name)
        if cache_key in self._cache:
            del self._cache[cache_key]
            logger.debug(
                "tool_schema_invalidated",
                tool_name=tool_name,
                server_name=server_name,
            )

    def invalidate_server(self, server_name: str) -> None:
        """
        Invalidate all schemas for a server

        Args:
            server_name: Name of the server
        """
        keys_to_delete = [
            key for key in self._cache.keys() if key.endswith(f":{server_name}")
        ]
        for key in keys_to_delete:
            del self._cache[key]

        logger.info(
            "tool_schemas_invalidated_for_server",
            server_name=server_name,
            count=len(keys_to_delete),
        )

    def clear(self) -> None:
        """Clear all cached schemas"""
        self._cache.clear()
        logger.info("tool_schema_cache_cleared")

    def get_all_for_server(self, server_name: str) -> Dict[str, ToolSchema]:
        """
        Get all cached schemas for a server

        Args:
            server_name: Name of the server

        Returns:
            Dictionary mapping tool names to schemas
        """
        schemas = {}
        for key, schema in self._cache.items():
            if schema.server_name == server_name:
                schemas[schema.name] = schema
        return schemas

    def get_all(self) -> Dict[str, ToolSchema]:
        """
        Get all cached schemas

        Returns:
            Dictionary mapping cache keys to schemas
        """
        return dict(self._cache)

    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics

        Returns:
            Dictionary with cache statistics
        """
        total_requests = self._hits + self._misses
        hit_rate = self._hits / total_requests if total_requests > 0 else 0.0

        return {
            "size": len(self._cache),
            "max_size": self.max_size,
            "ttl_seconds": self.ttl_seconds,
            "hits": self._hits,
            "misses": self._misses,
            "total_requests": total_requests,
            "hit_rate": hit_rate,
        }

    @staticmethod
    def _make_key(tool_name: str, server_name: str) -> str:
        """Create cache key from tool and server names"""
        return f"{tool_name}:{server_name}"
