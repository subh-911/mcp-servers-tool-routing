"""Response models for API endpoints"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    """Error response model"""

    error: str = Field(..., description="Error code")
    message: str = Field(..., description="Error message")
    details: Dict[str, Any] = Field(
        default_factory=dict, description="Additional error details"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "error": "ToolNotFoundError",
                "message": "Tool 'unknown_tool' not found",
                "details": {"tool_name": "unknown_tool"},
            }
        }


class ToolExecutionResponse(BaseModel):
    """Response from tool execution"""

    success: bool = Field(..., description="Whether execution was successful")
    tool_name: str = Field(..., description="Name of the executed tool")
    server_name: str = Field(..., description="Name of the server that executed the tool")
    result: Optional[Any] = Field(None, description="Execution result")
    error: Optional[str] = Field(None, description="Error message if failed")
    execution_time_ms: Optional[float] = Field(
        None, description="Execution time in milliseconds"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "tool_name": "query",
                "server_name": "database",
                "result": {"rows": [{"id": 1, "name": "John"}]},
                "execution_time_ms": 123.45,
            }
        }


class BatchExecutionResponse(BaseModel):
    """Response from batch tool execution"""

    total: int = Field(..., description="Total number of tools executed")
    successful: int = Field(..., description="Number of successful executions")
    failed: int = Field(..., description="Number of failed executions")
    results: List[ToolExecutionResponse] = Field(
        ..., description="Individual execution results"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "total": 2,
                "successful": 2,
                "failed": 0,
                "results": [
                    {
                        "success": True,
                        "tool_name": "query",
                        "server_name": "database",
                        "result": {"rows": []},
                    }
                ],
            }
        }


class ServerInfoResponse(BaseModel):
    """Server information response"""

    name: str = Field(..., description="Server name")
    description: str = Field(..., description="Server description")
    enabled: bool = Field(..., description="Whether server is enabled")
    tool_count: int = Field(..., description="Number of available tools")
    tools: List[str] = Field(..., description="List of available tools")
    circuit_breaker: Optional[Dict[str, Any]] = Field(
        None, description="Circuit breaker status"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "name": "database",
                "description": "Database operations server",
                "enabled": True,
                "tool_count": 3,
                "tools": ["database:query", "database:execute", "database:schema"],
                "circuit_breaker": {
                    "state": "closed",
                    "failure_count": 0,
                },
            }
        }


class ServerListResponse(BaseModel):
    """List of servers response"""

    total: int = Field(..., description="Total number of servers")
    servers: List[ServerInfoResponse] = Field(..., description="List of servers")


class ToolSchemaResponse(BaseModel):
    """Tool schema response"""

    name: str = Field(..., description="Tool name")
    description: str = Field(..., description="Tool description")
    server_name: str = Field(..., description="Server name")
    input_schema: Dict[str, Any] = Field(..., description="Tool input schema")
    cached_at: float = Field(..., description="When schema was cached")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "query",
                "description": "Execute a database query",
                "server_name": "database",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "timeout": {"type": "number"},
                    },
                },
                "cached_at": 1234567890.0,
            }
        }


class ToolListResponse(BaseModel):
    """List of tools response"""

    total: int = Field(..., description="Total number of tools")
    tools: List[str] = Field(..., description="List of tool names")
    by_server: Dict[str, List[str]] = Field(
        ..., description="Tools grouped by server"
    )


class ServerHealthStatus(BaseModel):
    """Health status for a single server"""

    name: str = Field(..., description="Server name")
    healthy: bool = Field(..., description="Whether server is healthy")
    connected: bool = Field(..., description="Whether server is connected")
    circuit_state: Optional[str] = Field(None, description="Circuit breaker state")
    last_error: Optional[str] = Field(None, description="Last error if any")


class HealthResponse(BaseModel):
    """Overall health response"""

    status: str = Field(..., description="Overall status (healthy, degraded, unhealthy)")
    timestamp: float = Field(..., description="Timestamp of health check")
    servers: List[ServerHealthStatus] = Field(..., description="Server health statuses")
    total_servers: int = Field(..., description="Total number of servers")
    healthy_servers: int = Field(..., description="Number of healthy servers")

    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "timestamp": 1234567890.0,
                "servers": [
                    {
                        "name": "database",
                        "healthy": True,
                        "connected": True,
                        "circuit_state": "closed",
                    }
                ],
                "total_servers": 1,
                "healthy_servers": 1,
            }
        }


class CircuitBreakerMetrics(BaseModel):
    """Circuit breaker metrics"""

    name: str = Field(..., description="Circuit breaker name")
    state: str = Field(..., description="Current state")
    failure_count: int = Field(..., description="Current failure count")
    total_requests: int = Field(..., description="Total requests")
    successful_requests: int = Field(..., description="Successful requests")
    failed_requests: int = Field(..., description="Failed requests")
    rejected_requests: int = Field(..., description="Rejected requests")
    failure_rate: float = Field(..., description="Failure rate")
    success_rate: float = Field(..., description="Success rate")


class MetricsResponse(BaseModel):
    """Metrics response"""

    circuit_breakers: List[CircuitBreakerMetrics] = Field(
        ..., description="Circuit breaker metrics"
    )
    schema_cache: Dict[str, Any] = Field(..., description="Schema cache statistics")
    connection_pool: Dict[str, Any] = Field(
        ..., description="Connection pool statistics"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "circuit_breakers": [
                    {
                        "name": "database",
                        "state": "closed",
                        "failure_count": 0,
                        "total_requests": 100,
                        "successful_requests": 100,
                        "failed_requests": 0,
                        "rejected_requests": 0,
                        "failure_rate": 0.0,
                        "success_rate": 1.0,
                    }
                ],
                "schema_cache": {
                    "size": 10,
                    "max_size": 1000,
                    "hits": 50,
                    "misses": 10,
                    "hit_rate": 0.83,
                },
                "connection_pool": {
                    "total_clients": 3,
                    "connected_clients": 3,
                },
            }
        }


class RouterStatsResponse(BaseModel):
    """Router statistics response"""

    servers: Dict[str, Any] = Field(..., description="Server statistics")
    tools: Dict[str, Any] = Field(..., description="Tool statistics")
    circuit_breakers: Dict[str, Any] = Field(
        ..., description="Circuit breaker statistics"
    )
    schema_cache: Dict[str, Any] = Field(..., description="Schema cache statistics")
    connection_pool: Dict[str, Any] = Field(
        ..., description="Connection pool statistics"
    )


class ConnectServerResponse(BaseModel):
    """Response from connecting to a server"""

    success: bool = Field(..., description="Whether connection was successful")
    server_name: str = Field(..., description="Server name")
    tool_count: int = Field(..., description="Number of tools discovered")
    tools: List[str] = Field(..., description="List of discovered tools")
    message: str = Field(..., description="Success message")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "server_name": "database",
                "tool_count": 3,
                "tools": ["database:query", "database:execute"],
                "message": "Successfully connected to server 'database'",
            }
        }


class DisconnectServerResponse(BaseModel):
    """Response from disconnecting a server"""

    success: bool = Field(..., description="Whether disconnection was successful")
    server_name: str = Field(..., description="Server name")
    message: str = Field(..., description="Success message")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "server_name": "database",
                "message": "Successfully disconnected server 'database'",
            }
        }
