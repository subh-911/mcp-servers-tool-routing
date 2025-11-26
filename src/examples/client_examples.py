"""
Client usage examples for MCP Tool Router

This file demonstrates how to interact with the MCP Tool Router API.
"""

import asyncio
import httpx


BASE_URL = "http://localhost:8000"


async def example_list_servers():
    """Example: List all connected servers"""
    print("\\n=== Listing Servers ===")

    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/api/v1/servers")
        data = response.json()

        print(f"Total servers: {data['total']}")
        for server in data["servers"]:
            print(f"  - {server['name']}: {server['tool_count']} tools")


async def example_list_tools():
    """Example: List all available tools"""
    print("\\n=== Listing Tools ===")

    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/api/v1/tools")
        data = response.json()

        print(f"Total tools: {data['total']}")
        for server, tools in data["by_server"].items():
            print(f"\\n{server}:")
            for tool in tools:
                print(f"  - {tool}")


async def example_execute_database_query():
    """Example: Execute a database query"""
    print("\\n=== Executing Database Query ===")

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/api/v1/tools/database:query/execute",
            json={
                "arguments": {
                    "query": "SELECT * FROM users WHERE id = 1",
                }
            },
        )

        if response.status_code == 200:
            data = response.json()
            print(f"Success: {data['success']}")
            print(f"Result: {data['result']}")
            print(f"Execution time: {data['execution_time_ms']}ms")
        else:
            print(f"Error: {response.json()}")


async def example_read_file():
    """Example: Read a file using filesystem server"""
    print("\\n=== Reading File ===")

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/api/v1/tools/filesystem:read/execute",
            json={
                "arguments": {
                    "path": "/home/user/documents/readme.txt",
                }
            },
        )

        if response.status_code == 200:
            data = response.json()
            print(f"File content: {data['result']}")
        else:
            print(f"Error: {response.json()}")


async def example_batch_execution():
    """Example: Execute multiple tools in batch"""
    print("\\n=== Batch Execution ===")

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/api/v1/tools/batch",
            json={
                "tools": [
                    {
                        "tool_name": "database:query",
                        "arguments": {"query": "SELECT * FROM users"},
                    },
                    {
                        "tool_name": "filesystem:read",
                        "arguments": {"path": "/home/user/documents/readme.txt"},
                    },
                    {
                        "tool_name": "api:api_status",
                        "arguments": {},
                    },
                ],
                "parallel": True,
            },
        )

        if response.status_code == 200:
            data = response.json()
            print(f"Total: {data['total']}")
            print(f"Successful: {data['successful']}")
            print(f"Failed: {data['failed']}")

            for result in data["results"]:
                print(f"\\n{result['tool_name']}:")
                print(f"  Success: {result['success']}")
                if result["success"]:
                    print(f"  Result: {result['result']}")
        else:
            print(f"Error: {response.json()}")


async def example_health_check():
    """Example: Check system health"""
    print("\\n=== Health Check ===")

    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/api/v1/health")
        data = response.json()

        print(f"Overall status: {data['status']}")
        print(f"Total servers: {data['total_servers']}")
        print(f"Healthy servers: {data['healthy_servers']}")

        print("\\nServer statuses:")
        for server in data["servers"]:
            print(f"  - {server['name']}: {'✓' if server['healthy'] else '✗'}")
            if server.get("circuit_state"):
                print(f"    Circuit: {server['circuit_state']}")


async def example_get_metrics():
    """Example: Get metrics and statistics"""
    print("\\n=== Metrics ===")

    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/api/v1/metrics")
        data = response.json()

        print("Circuit Breakers:")
        for cb in data["circuit_breakers"]:
            print(f"  {cb['name']}:")
            print(f"    State: {cb['state']}")
            print(f"    Success rate: {cb['success_rate']:.2%}")
            print(f"    Total requests: {cb['total_requests']}")

        print("\\nSchema Cache:")
        cache = data["schema_cache"]
        print(f"  Size: {cache['size']}/{cache['max_size']}")
        print(f"  Hit rate: {cache['hit_rate']:.2%}")


async def example_connect_server():
    """Example: Connect to a new MCP server"""
    print("\\n=== Connecting to New Server ===")

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/api/v1/servers",
            json={
                "name": "custom_server",
                "description": "My custom MCP server",
                "enabled": True,
                "connection": {
                    "type": "stdio",
                    "command": "python",
                    "args": ["path/to/my_server.py"],
                },
            },
        )

        if response.status_code == 201:
            data = response.json()
            print(f"Connected: {data['success']}")
            print(f"Tools discovered: {data['tool_count']}")
            print(f"Tools: {data['tools']}")
        else:
            print(f"Error: {response.json()}")


async def example_get_tool_schema():
    """Example: Get tool schema"""
    print("\\n=== Getting Tool Schema ===")

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/api/v1/tools/database:query/schema"
        )

        if response.status_code == 200:
            data = response.json()
            print(f"Tool: {data['name']}")
            print(f"Description: {data['description']}")
            print(f"Server: {data['server_name']}")
            print(f"Input schema: {data['input_schema']}")
        else:
            print(f"Error: {response.json()}")


async def main():
    """Run all examples"""
    print("=================================================")
    print("     MCP Tool Router - Client Examples")
    print("=================================================")

    try:
        # Basic operations
        await example_list_servers()
        await example_list_tools()
        await example_get_tool_schema()

        # Tool execution
        await example_execute_database_query()
        await example_read_file()
        await example_batch_execution()

        # Monitoring
        await example_health_check()
        await example_get_metrics()

        # Note: Connect server example is commented out
        # to avoid modifying the running configuration
        # await example_connect_server()

    except Exception as e:
        print(f"\\nError running examples: {e}")
        print("\\nMake sure the MCP Tool Router is running at http://localhost:8000")


if __name__ == "__main__":
    asyncio.run(main())
