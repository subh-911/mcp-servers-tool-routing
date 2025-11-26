"""Request models for API endpoints"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class ServerConnectionConfig(BaseModel):
    """Server connection configuration"""

    type: str = Field(..., description="Connection type (stdio, sse, websocket)")
    command: Optional[str] = Field(None, description="Command for stdio connection")
    args: Optional[List[str]] = Field(default_factory=list, description="Command arguments")
    url: Optional[str] = Field(None, description="URL for sse/websocket connection")
    env: Optional[Dict[str, str]] = Field(
        default_factory=dict, description="Environment variables"
    )
    headers: Optional[Dict[str, str]] = Field(
        default_factory=dict, description="Headers for HTTP connections"
    )

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        """Validate connection type"""
        allowed_types = ["stdio", "sse", "websocket"]
        if v not in allowed_types:
            raise ValueError(f"Connection type must be one of {allowed_types}")
        return v


class ServerOptions(BaseModel):
    """Server options configuration"""

    auto_reconnect: bool = Field(default=True, description="Enable auto-reconnection")
    max_reconnect_attempts: int = Field(default=3, description="Max reconnection attempts")
    reconnect_delay: int = Field(default=5, description="Delay between reconnect attempts")
    health_check_interval: int = Field(
        default=30, description="Health check interval in seconds"
    )


class ConnectServerRequest(BaseModel):
    """Request to connect to an MCP server"""

    name: str = Field(..., description="Unique name for the server")
    description: Optional[str] = Field(default="", description="Server description")
    enabled: bool = Field(default=True, description="Whether server is enabled")
    connection: ServerConnectionConfig = Field(..., description="Connection configuration")
    options: Optional[ServerOptions] = Field(
        default_factory=ServerOptions, description="Server options"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "name": "my_database",
                "description": "Database operations server",
                "enabled": True,
                "connection": {
                    "type": "stdio",
                    "command": "python",
                    "args": ["database_server.py"],
                    "env": {},
                },
                "options": {
                    "auto_reconnect": True,
                    "max_reconnect_attempts": 3,
                },
            }
        }


class ExecuteToolRequest(BaseModel):
    """Request to execute a tool"""

    arguments: Dict[str, Any] = Field(
        default_factory=dict, description="Tool arguments"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "arguments": {
                    "query": "SELECT * FROM users WHERE id = 1",
                    "timeout": 30,
                }
            }
        }


class ToolExecutionItem(BaseModel):
    """Single tool execution item for batch requests"""

    tool_name: str = Field(..., description="Name of the tool to execute")
    arguments: Dict[str, Any] = Field(
        default_factory=dict, description="Tool arguments"
    )


class BatchExecuteRequest(BaseModel):
    """Request to execute multiple tools"""

    tools: List[ToolExecutionItem] = Field(..., description="List of tools to execute")
    parallel: bool = Field(
        default=True, description="Execute tools in parallel if possible"
    )

    @field_validator("tools")
    @classmethod
    def validate_tools(cls, v: List[ToolExecutionItem]) -> List[ToolExecutionItem]:
        """Validate tools list"""
        if not v:
            raise ValueError("Tools list cannot be empty")
        if len(v) > 50:
            raise ValueError("Maximum 50 tools allowed per batch request")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "tools": [
                    {
                        "tool_name": "database:query",
                        "arguments": {"query": "SELECT * FROM users"},
                    },
                    {
                        "tool_name": "filesystem:read",
                        "arguments": {"path": "/tmp/data.txt"},
                    },
                ],
                "parallel": True,
            }
        }
