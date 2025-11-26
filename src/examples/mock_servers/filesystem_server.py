#!/usr/bin/env python3
"""
Mock Filesystem MCP Server

Provides filesystem-like operations for testing and demonstration.
"""

import asyncio
import json
import sys
from typing import Any, Dict, List

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent


# Mock in-memory filesystem
MOCK_FILESYSTEM = {
    "/home/user/documents/readme.txt": "Welcome to the MCP Tool Router!",
    "/home/user/documents/config.json": '{"setting": "value", "enabled": true}',
    "/home/user/data/data.csv": "id,name,value\\n1,test,100\\n2,demo,200",
    "/tmp/log.txt": "2024-01-01 10:00:00 INFO Application started\\n2024-01-01 10:01:00 INFO Request processed",
}


class FilesystemServer:
    """Mock filesystem MCP server"""

    def __init__(self) -> None:
        self.server = Server("filesystem")
        self._setup_handlers()

    def _setup_handlers(self) -> None:
        """Setup MCP server handlers"""

        @self.server.list_tools()
        async def list_tools() -> List[Tool]:
            """List available filesystem tools"""
            return [
                Tool(
                    name="read",
                    description="Read contents of a file",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "File path to read",
                            },
                            "encoding": {
                                "type": "string",
                                "description": "File encoding",
                                "default": "utf-8",
                            },
                        },
                        "required": ["path"],
                    },
                ),
                Tool(
                    name="write",
                    description="Write contents to a file",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "File path to write",
                            },
                            "content": {
                                "type": "string",
                                "description": "Content to write",
                            },
                            "append": {
                                "type": "boolean",
                                "description": "Append to file instead of overwriting",
                                "default": False,
                            },
                        },
                        "required": ["path", "content"],
                    },
                ),
                Tool(
                    name="list",
                    description="List files in a directory",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "Directory path to list",
                            },
                            "recursive": {
                                "type": "boolean",
                                "description": "List recursively",
                                "default": False,
                            },
                        },
                        "required": ["path"],
                    },
                ),
                Tool(
                    name="delete",
                    description="Delete a file",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "File path to delete",
                            },
                        },
                        "required": ["path"],
                    },
                ),
            ]

        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
            """Handle tool execution"""

            if name == "read":
                return await self._handle_read(arguments)
            elif name == "write":
                return await self._handle_write(arguments)
            elif name == "list":
                return await self._handle_list(arguments)
            elif name == "delete":
                return await self._handle_delete(arguments)
            else:
                raise ValueError(f"Unknown tool: {name}")

    async def _handle_read(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Handle file read"""
        path = arguments.get("path", "")

        if path not in MOCK_FILESYSTEM:
            return [
                TextContent(
                    type="text",
                    text=json.dumps(
                        {
                            "error": f"File not found: {path}",
                            "available_files": list(MOCK_FILESYSTEM.keys()),
                        }
                    ),
                )
            ]

        content = MOCK_FILESYSTEM[path]

        return [
            TextContent(
                type="text",
                text=json.dumps(
                    {
                        "success": True,
                        "path": path,
                        "content": content,
                        "size": len(content),
                    },
                    indent=2,
                ),
            )
        ]

    async def _handle_write(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Handle file write"""
        path = arguments.get("path", "")
        content = arguments.get("content", "")
        append = arguments.get("append", False)

        if append and path in MOCK_FILESYSTEM:
            MOCK_FILESYSTEM[path] += content
        else:
            MOCK_FILESYSTEM[path] = content

        return [
            TextContent(
                type="text",
                text=json.dumps(
                    {
                        "success": True,
                        "path": path,
                        "operation": "append" if append else "write",
                        "bytes_written": len(content),
                    }
                ),
            )
        ]

    async def _handle_list(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Handle directory listing"""
        path = arguments.get("path", "/")
        recursive = arguments.get("recursive", False)

        # Normalize path
        if not path.endswith("/") and path != "/":
            path += "/"

        # Filter files by path
        if path == "/":
            files = list(MOCK_FILESYSTEM.keys())
        else:
            files = [
                file_path
                for file_path in MOCK_FILESYSTEM.keys()
                if file_path.startswith(path)
            ]

        # If not recursive, only show immediate children
        if not recursive and path != "/":
            immediate_files = []
            for file_path in files:
                relative = file_path[len(path) :]
                if "/" not in relative:
                    immediate_files.append(file_path)
            files = immediate_files

        return [
            TextContent(
                type="text",
                text=json.dumps(
                    {
                        "success": True,
                        "path": path,
                        "files": files,
                        "count": len(files),
                    },
                    indent=2,
                ),
            )
        ]

    async def _handle_delete(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Handle file deletion"""
        path = arguments.get("path", "")

        if path not in MOCK_FILESYSTEM:
            return [
                TextContent(
                    type="text",
                    text=json.dumps(
                        {
                            "error": f"File not found: {path}",
                        }
                    ),
                )
            ]

        del MOCK_FILESYSTEM[path]

        return [
            TextContent(
                type="text",
                text=json.dumps(
                    {
                        "success": True,
                        "path": path,
                        "operation": "delete",
                    }
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
    server = FilesystemServer()
    await server.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\\nShutting down filesystem server...", file=sys.stderr)
        sys.exit(0)
