#!/usr/bin/env python3
"""
Mock Database MCP Server

Provides database-like operations for testing and demonstration.
"""

import asyncio
import json
import sys
from typing import Any, Dict, List

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent


# Mock in-memory database
MOCK_DATABASE = {
    "users": [
        {"id": 1, "name": "Alice", "email": "alice@example.com", "role": "admin"},
        {"id": 2, "name": "Bob", "email": "bob@example.com", "role": "user"},
        {"id": 3, "name": "Charlie", "email": "charlie@example.com", "role": "user"},
    ],
    "products": [
        {"id": 1, "name": "Laptop", "price": 999.99, "stock": 50},
        {"id": 2, "name": "Mouse", "price": 29.99, "stock": 200},
        {"id": 3, "name": "Keyboard", "price": 79.99, "stock": 150},
    ],
    "orders": [
        {"id": 1, "user_id": 1, "product_id": 1, "quantity": 1, "total": 999.99},
        {"id": 2, "user_id": 2, "product_id": 2, "quantity": 2, "total": 59.98},
    ],
}


class DatabaseServer:
    """Mock database MCP server"""

    def __init__(self) -> None:
        self.server = Server("database")
        self._setup_handlers()

    def _setup_handlers(self) -> None:
        """Setup MCP server handlers"""

        @self.server.list_tools()
        async def list_tools() -> List[Tool]:
            """List available database tools"""
            return [
                Tool(
                    name="query",
                    description="Execute a SQL-like query on the mock database",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "SQL-like query (e.g., 'SELECT * FROM users')",
                            },
                            "limit": {
                                "type": "number",
                                "description": "Limit number of results",
                                "default": 100,
                            },
                        },
                        "required": ["query"],
                    },
                ),
                Tool(
                    name="execute",
                    description="Execute a write operation (INSERT, UPDATE, DELETE)",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "operation": {
                                "type": "string",
                                "description": "Operation type (insert, update, delete)",
                            },
                            "table": {
                                "type": "string",
                                "description": "Table name",
                            },
                            "data": {
                                "type": "object",
                                "description": "Data for the operation",
                            },
                        },
                        "required": ["operation", "table"],
                    },
                ),
                Tool(
                    name="schema",
                    description="Get database schema information",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "table": {
                                "type": "string",
                                "description": "Optional table name to get schema for",
                            },
                        },
                    },
                ),
            ]

        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
            """Handle tool execution"""

            if name == "query":
                return await self._handle_query(arguments)
            elif name == "execute":
                return await self._handle_execute(arguments)
            elif name == "schema":
                return await self._handle_schema(arguments)
            else:
                raise ValueError(f"Unknown tool: {name}")

    async def _handle_query(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Handle database query"""
        query = arguments.get("query", "").upper()
        limit = arguments.get("limit", 100)

        # Simple query parsing
        if "FROM USERS" in query:
            table_data = MOCK_DATABASE["users"]
        elif "FROM PRODUCTS" in query:
            table_data = MOCK_DATABASE["products"]
        elif "FROM ORDERS" in query:
            table_data = MOCK_DATABASE["orders"]
        else:
            return [
                TextContent(
                    type="text",
                    text=json.dumps(
                        {
                            "error": "Unknown table. Available tables: users, products, orders"
                        }
                    ),
                )
            ]

        # Apply limit
        results = table_data[:limit]

        # Filter by WHERE clause (simple implementation)
        if "WHERE" in query:
            # Extract simple WHERE conditions
            where_part = query.split("WHERE")[1].strip()
            if "ID =" in where_part:
                try:
                    id_value = int(where_part.split("=")[1].strip())
                    results = [row for row in results if row.get("id") == id_value]
                except (ValueError, IndexError):
                    pass

        return [
            TextContent(
                type="text",
                text=json.dumps(
                    {
                        "success": True,
                        "rows": results,
                        "count": len(results),
                    },
                    indent=2,
                ),
            )
        ]

    async def _handle_execute(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Handle database write operation"""
        operation = arguments.get("operation", "").lower()
        table = arguments.get("table", "").lower()
        data = arguments.get("data", {})

        if table not in MOCK_DATABASE:
            return [
                TextContent(
                    type="text",
                    text=json.dumps(
                        {
                            "error": f"Unknown table: {table}. Available tables: users, products, orders"
                        }
                    ),
                )
            ]

        if operation == "insert":
            # Generate new ID
            new_id = max([row["id"] for row in MOCK_DATABASE[table]], default=0) + 1
            new_row = {"id": new_id, **data}
            MOCK_DATABASE[table].append(new_row)

            return [
                TextContent(
                    type="text",
                    text=json.dumps(
                        {
                            "success": True,
                            "operation": "insert",
                            "affected_rows": 1,
                            "new_id": new_id,
                        }
                    ),
                )
            ]

        elif operation == "delete":
            # Delete by ID
            if "id" in data:
                original_count = len(MOCK_DATABASE[table])
                MOCK_DATABASE[table] = [
                    row for row in MOCK_DATABASE[table] if row["id"] != data["id"]
                ]
                affected = original_count - len(MOCK_DATABASE[table])

                return [
                    TextContent(
                        type="text",
                        text=json.dumps(
                            {
                                "success": True,
                                "operation": "delete",
                                "affected_rows": affected,
                            }
                        ),
                    )
                ]

        return [
            TextContent(
                type="text",
                text=json.dumps(
                    {
                        "error": f"Unsupported operation: {operation}",
                    }
                ),
            )
        ]

    async def _handle_schema(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Handle schema information request"""
        table = arguments.get("table")

        if table:
            if table.lower() not in MOCK_DATABASE:
                return [
                    TextContent(
                        type="text",
                        text=json.dumps(
                            {
                                "error": f"Unknown table: {table}",
                            }
                        ),
                    )
                ]

            # Get sample row to infer schema
            sample = MOCK_DATABASE[table.lower()][0] if MOCK_DATABASE[table.lower()] else {}
            schema = {
                "table": table.lower(),
                "columns": list(sample.keys()),
                "row_count": len(MOCK_DATABASE[table.lower()]),
            }
        else:
            # Return all tables
            schema = {
                "tables": list(MOCK_DATABASE.keys()),
                "total_tables": len(MOCK_DATABASE),
            }

        return [
            TextContent(
                type="text",
                text=json.dumps(schema, indent=2),
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
    server = DatabaseServer()
    await server.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\\nShutting down database server...", file=sys.stderr)
        sys.exit(0)
