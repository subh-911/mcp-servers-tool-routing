#!/usr/bin/env python3
"""
Mock API MCP Server

Provides HTTP API-like operations for testing and demonstration.
"""

import asyncio
import json
import sys
from typing import Any, Dict, List

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent


# Mock API endpoints and responses
MOCK_API_RESPONSES = {
    "https://api.example.com/users": {
        "users": [
            {"id": 1, "username": "alice"},
            {"id": 2, "username": "bob"},
        ]
    },
    "https://api.example.com/posts": {
        "posts": [
            {"id": 1, "title": "Hello World", "author_id": 1},
            {"id": 2, "title": "Getting Started", "author_id": 2},
        ]
    },
    "https://api.example.com/status": {"status": "operational", "uptime": 99.99},
}

# Mock webhooks registry
MOCK_WEBHOOKS: List[Dict[str, Any]] = []


class APIServer:
    """Mock API MCP server"""

    def __init__(self) -> None:
        self.server = Server("api")
        self._setup_handlers()

    def _setup_handlers(self) -> None:
        """Setup MCP server handlers"""

        @self.server.list_tools()
        async def list_tools() -> List[Tool]:
            """List available API tools"""
            return [
                Tool(
                    name="http_request",
                    description="Make an HTTP request to an external API",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "url": {
                                "type": "string",
                                "description": "URL to request",
                            },
                            "method": {
                                "type": "string",
                                "description": "HTTP method (GET, POST, PUT, DELETE)",
                                "default": "GET",
                            },
                            "headers": {
                                "type": "object",
                                "description": "HTTP headers",
                                "default": {},
                            },
                            "body": {
                                "type": "object",
                                "description": "Request body for POST/PUT",
                                "default": {},
                            },
                        },
                        "required": ["url"],
                    },
                ),
                Tool(
                    name="register_webhook",
                    description="Register a webhook endpoint",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "url": {
                                "type": "string",
                                "description": "Webhook URL",
                            },
                            "events": {
                                "type": "array",
                                "description": "Events to listen for",
                                "items": {"type": "string"},
                            },
                            "secret": {
                                "type": "string",
                                "description": "Webhook secret for verification",
                            },
                        },
                        "required": ["url", "events"],
                    },
                ),
                Tool(
                    name="list_webhooks",
                    description="List registered webhooks",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                    },
                ),
                Tool(
                    name="api_status",
                    description="Get API status and health information",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "service": {
                                "type": "string",
                                "description": "Optional service name to check",
                            },
                        },
                    },
                ),
            ]

        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
            """Handle tool execution"""

            if name == "http_request":
                return await self._handle_http_request(arguments)
            elif name == "register_webhook":
                return await self._handle_register_webhook(arguments)
            elif name == "list_webhooks":
                return await self._handle_list_webhooks(arguments)
            elif name == "api_status":
                return await self._handle_api_status(arguments)
            else:
                raise ValueError(f"Unknown tool: {name}")

    async def _handle_http_request(
        self, arguments: Dict[str, Any]
    ) -> List[TextContent]:
        """Handle HTTP request"""
        url = arguments.get("url", "")
        method = arguments.get("method", "GET").upper()
        headers = arguments.get("headers", {})
        body = arguments.get("body", {})

        # Simulate HTTP request
        if url in MOCK_API_RESPONSES:
            response_data = MOCK_API_RESPONSES[url]
            status_code = 200
        else:
            response_data = {"error": "Not Found"}
            status_code = 404

        # Simulate different responses for different methods
        if method == "POST":
            response_data = {
                "success": True,
                "created": True,
                "data": body,
                "id": len(MOCK_WEBHOOKS) + 1,
            }
            status_code = 201
        elif method == "DELETE":
            response_data = {"success": True, "deleted": True}
            status_code = 200

        return [
            TextContent(
                type="text",
                text=json.dumps(
                    {
                        "success": status_code < 400,
                        "status_code": status_code,
                        "url": url,
                        "method": method,
                        "response": response_data,
                        "headers": headers,
                    },
                    indent=2,
                ),
            )
        ]

    async def _handle_register_webhook(
        self, arguments: Dict[str, Any]
    ) -> List[TextContent]:
        """Handle webhook registration"""
        url = arguments.get("url", "")
        events = arguments.get("events", [])
        secret = arguments.get("secret", "")

        webhook = {
            "id": len(MOCK_WEBHOOKS) + 1,
            "url": url,
            "events": events,
            "secret": secret,
            "active": True,
        }

        MOCK_WEBHOOKS.append(webhook)

        return [
            TextContent(
                type="text",
                text=json.dumps(
                    {
                        "success": True,
                        "webhook": webhook,
                        "message": "Webhook registered successfully",
                    },
                    indent=2,
                ),
            )
        ]

    async def _handle_list_webhooks(
        self, arguments: Dict[str, Any]
    ) -> List[TextContent]:
        """Handle list webhooks"""
        return [
            TextContent(
                type="text",
                text=json.dumps(
                    {
                        "success": True,
                        "webhooks": MOCK_WEBHOOKS,
                        "count": len(MOCK_WEBHOOKS),
                    },
                    indent=2,
                ),
            )
        ]

    async def _handle_api_status(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Handle API status check"""
        service = arguments.get("service")

        if service:
            # Check specific service
            status_data = {
                "service": service,
                "status": "operational",
                "latency_ms": 45,
                "last_check": "2024-01-01T10:00:00Z",
            }
        else:
            # Overall status
            status_data = {
                "overall_status": "operational",
                "services": {
                    "database": "operational",
                    "cache": "operational",
                    "storage": "operational",
                },
                "uptime_percentage": 99.99,
                "total_requests": 1000000,
                "avg_response_time_ms": 50,
            }

        return [
            TextContent(
                type="text",
                text=json.dumps(
                    {
                        "success": True,
                        "status": status_data,
                    },
                    indent=2,
                ),
            )
        ]

    async def run(self) -> None:
        """Run the MCP server"""
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options(),
            )


async def main() -> None:
    """Main entry point"""
    server = APIServer()
    await server.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\\nShutting down API server...", file=sys.stderr)
        sys.exit(0)
