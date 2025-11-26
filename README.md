# MCP Tool Router

A production-quality Multi-Tool Integration system for routing tool executions across multiple MCP (Model Context Protocol) servers with FastAPI.

## Features

✨ **Core Capabilities**
- Connect to 3+ MCP servers simultaneously
- Unified tool interface for executing tools across all connected servers
- Tool discovery and schema caching
- Automatic tool namespacing to avoid conflicts

🛡️ **Production-Ready Features**
- **Circuit Breakers**: Automatic failure detection and server isolation
- **Connection Pooling**: Efficient connection reuse across requests
- **Retry Logic**: Exponential backoff for transient failures
- **Schema Caching**: TTL-based caching to reduce redundant tool schema fetches
- **Error Handling**: Comprehensive error handling with detailed error responses
- **Health Monitoring**: Health checks, metrics, and circuit breaker status endpoints

🚀 **API & Integration**
- RESTful API with FastAPI
- OpenAPI/Swagger documentation
- CORS support
- Request validation with Pydantic
- Async/await throughout for high performance

## Architecture

```
┌─────────────────────────────────────────┐
│         FastAPI Application             │
│  ┌───────────────────────────────────┐  │
│  │     MCP Tool Router               │  │
│  │  ┌─────────────────────────────┐  │  │
│  │  │  Circuit Breakers           │  │  │
│  │  │  Connection Pool            │  │  │
│  │  │  Schema Cache (TTL)         │  │  │
│  │  └─────────────────────────────┘  │  │
│  └───────────────────────────────────┘  │
└─────────────────────────────────────────┘
         │         │         │
    ┌────┴───┐ ┌──┴───┐ ┌──┴────┐
    │ MCP    │ │ MCP  │ │ MCP   │
    │ Server │ │ Server│ │ Server│
    │   #1   │ │  #2  │ │  #3   │
    └────────┘ └──────┘ └───────┘
```

## Quick Start

### Prerequisites

- Python 3.10+
- pip
- (Optional) Docker & Docker Compose

### Installation

1. **Clone the repository**
```bash
git clone <your-repo-url>
cd mcp-servers-tool-routing
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Copy environment file**
```bash
cp .env.example .env
```

5. **Configure servers**
Edit `config/servers.yaml` to configure your MCP servers.

### Running the Application

#### Option 1: Local Development

```bash
# Start the application
python src/main.py

# Or using uvicorn directly
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

#### Option 2: Docker

```bash
# Build and start all services
docker-compose up --build

# Or run in background
docker-compose up -d
```

### Accessing the API

- **API Documentation**: http://localhost:8000/api/docs
- **ReDoc**: http://localhost:8000/api/redoc
- **Health Check**: http://localhost:8000/api/v1/health

## API Endpoints

### Tool Execution

- `POST /api/v1/tools/{tool_name}/execute` - Execute a specific tool
- `POST /api/v1/tools/batch` - Execute multiple tools in batch

### Server Management

- `POST /api/v1/servers` - Connect to a new MCP server
- `GET /api/v1/servers` - List all connected servers
- `GET /api/v1/servers/{name}` - Get server details
- `DELETE /api/v1/servers/{name}` - Disconnect from a server

### Tool Discovery

- `GET /api/v1/tools` - List all available tools
- `GET /api/v1/tools/{tool_name}/schema` - Get tool input schema

### Health & Monitoring

- `GET /api/v1/health` - Overall health status
- `GET /api/v1/health/servers` - Per-server health status
- `GET /api/v1/metrics` - Circuit breaker metrics and statistics
- `GET /api/v1/stats` - Router statistics

## Usage Examples

### Execute a Tool

```bash
curl -X POST "http://localhost:8000/api/v1/tools/database:query/execute" \
  -H "Content-Type: application/json" \
  -d '{
    "arguments": {
      "query": "SELECT * FROM users WHERE id = 1"
    }
  }'
```

### List Available Tools

```bash
curl "http://localhost:8000/api/v1/tools"
```

### Connect to a New Server

```bash
curl -X POST "http://localhost:8000/api/v1/servers" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "my_server",
    "description": "My custom MCP server",
    "enabled": true,
    "connection": {
      "type": "stdio",
      "command": "python",
      "args": ["path/to/server.py"]
    }
  }'
```

### Check Health

```bash
curl "http://localhost:8000/api/v1/health"
```

## Configuration

### Environment Variables

Key environment variables (see `.env.example` for full list):

- `APP_ENV` - Application environment (development, production)
- `DEBUG` - Enable debug mode
- `LOG_LEVEL` - Logging level (INFO, DEBUG, WARNING, ERROR)
- `HOST` - Server host (default: 0.0.0.0)
- `PORT` - Server port (default: 8000)
- `MAX_RETRIES` - Maximum retry attempts (default: 3)
- `CIRCUIT_BREAKER_FAILURE_THRESHOLD` - Failures before opening circuit (default: 5)
- `SCHEMA_CACHE_TTL` - Schema cache TTL in seconds (default: 3600)

### Server Configuration

Edit `config/servers.yaml` to define MCP servers:

```yaml
servers:
  - name: "database"
    description: "Database operations server"
    enabled: true
    connection:
      type: "stdio"
      command: "python"
      args: ["src/examples/mock_servers/database_server.py"]
    options:
      auto_reconnect: true
      max_reconnect_attempts: 3
```

## Testing

### Run All Tests

```bash
pytest
```

### Run with Coverage

```bash
pytest --cov=src --cov-report=html --cov-report=term-missing
```

### Run Specific Test File

```bash
pytest tests/test_router.py
```

## Mock Servers

The project includes 3 mock MCP servers for testing and demonstration:

1. **Database Server** (`src/examples/mock_servers/database_server.py`)
   - Tools: `query`, `execute`, `schema`
   - Simulates database operations

2. **Filesystem Server** (`src/examples/mock_servers/filesystem_server.py`)
   - Tools: `read`, `write`, `list`, `delete`
   - Simulates file system operations

3. **API Server** (`src/examples/mock_servers/api_server.py`)
   - Tools: `http_request`, `register_webhook`, `list_webhooks`, `api_status`
   - Simulates HTTP API operations

### Running Mock Servers Standalone

```bash
python src/examples/mock_servers/database_server.py
python src/examples/mock_servers/filesystem_server.py
python src/examples/mock_servers/api_server.py
```

## Project Structure

```
mcp-servers-tool-routing/
├── src/
│   ├── main.py                    # FastAPI application entry point
│   ├── core/                      # Core router implementation
│   │   ├── router.py              # MCPToolRouter
│   │   ├── circuit_breaker.py    # Circuit breaker pattern
│   │   ├── config.py              # Configuration management
│   │   └── exceptions.py          # Custom exceptions
│   ├── mcp/                       # MCP client implementation
│   │   ├── client.py              # Connection pooling
│   │   └── schemas.py             # Schema caching
│   ├── api/                       # API routes and models
│   │   ├── routes/                # FastAPI routes
│   │   └── models/                # Pydantic models
│   └── examples/                  # Example servers
│       └── mock_servers/          # Mock MCP servers
├── tests/                         # Test suite
├── config/                        # Configuration files
├── scripts/                       # Utility scripts
├── Dockerfile                     # Docker image definition
├── docker-compose.yml             # Multi-container setup
├── requirements.txt               # Production dependencies
├── requirements-dev.txt           # Development dependencies
└── README.md                      # This file
```

## Best Practices Implemented

✅ **Connection Pooling**: Reuses MCP connections instead of creating per-request

✅ **Tool Namespacing**: Prefixes tools with server name to avoid conflicts (e.g., `database:query`)

✅ **Circuit Breakers**: Temporarily disables failing servers to prevent cascade failures

✅ **Schema Caching**: Caches tool schemas with TTL to reduce unnecessary fetches

✅ **Retry Logic**: Exponential backoff for transient failures

✅ **Type Safety**: Full type hints throughout the codebase

✅ **Async/Await**: Non-blocking I/O for high performance

✅ **Structured Logging**: JSON-formatted logs for easy parsing

✅ **Health Checks**: Ready/alive probes for container orchestration

✅ **Error Handling**: Comprehensive error handling with detailed responses

## Development

### Code Quality Tools

```bash
# Format code
black src/ tests/

# Sort imports
isort src/ tests/

# Lint
flake8 src/ tests/
pylint src/

# Type checking
mypy src/
```

### Adding a New MCP Server

1. Create server configuration in `config/servers.yaml`
2. Restart the application
3. The router will automatically connect and discover tools

### Creating a Custom MCP Server

See the mock servers in `src/examples/mock_servers/` for reference implementations.

## Performance Considerations

- **Connection Pooling**: Connections are reused across requests
- **Schema Caching**: Tool schemas are cached with configurable TTL
- **Circuit Breakers**: Failed servers are temporarily isolated
- **Async Operations**: All I/O operations are non-blocking
- **Request Timeouts**: Configurable timeouts prevent hanging requests

## Troubleshooting

### Application won't start

1. Check that all dependencies are installed: `pip install -r requirements.txt`
2. Verify configuration files exist in `config/`
3. Check logs for detailed error messages

### Server connection fails

1. Verify server configuration in `config/servers.yaml`
2. Check that the MCP server command/path is correct
3. Review circuit breaker status: `GET /api/v1/health/servers`

### Tools not appearing

1. Ensure server is connected: `GET /api/v1/servers`
2. Check server logs for errors
3. Verify tool discovery completed: `GET /api/v1/tools`

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

## License

MIT License - See LICENSE file for details

## Support

For issues, questions, or contributions, please open an issue on GitHub.

---

**Built with ❤️ using FastAPI and the MCP Protocol**
