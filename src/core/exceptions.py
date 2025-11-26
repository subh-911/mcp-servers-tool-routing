"""Custom exceptions for MCP Tool Router"""

from typing import Any, Dict, Optional


class MCPToolRouterError(Exception):
    """Base exception for all MCP Tool Router errors"""

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for API responses"""
        return {
            "error": self.error_code,
            "message": self.message,
            "details": self.details,
        }


class ConfigurationError(MCPToolRouterError):
    """Raised when there's a configuration error"""

    pass


class MCPConnectionError(MCPToolRouterError):
    """Raised when connection to MCP server fails"""

    def __init__(
        self,
        message: str,
        server_name: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message, details=details)
        self.server_name = server_name
        if server_name:
            self.details["server_name"] = server_name


class ServerNotFoundError(MCPToolRouterError):
    """Raised when requested server is not found"""

    def __init__(self, server_name: str) -> None:
        super().__init__(
            f"Server '{server_name}' not found",
            details={"server_name": server_name},
        )
        self.server_name = server_name


class ToolNotFoundError(MCPToolRouterError):
    """Raised when requested tool is not found"""

    def __init__(self, tool_name: str) -> None:
        super().__init__(
            f"Tool '{tool_name}' not found",
            details={"tool_name": tool_name},
        )
        self.tool_name = tool_name


class ToolExecutionError(MCPToolRouterError):
    """Raised when tool execution fails"""

    def __init__(
        self,
        message: str,
        tool_name: Optional[str] = None,
        server_name: Optional[str] = None,
        original_error: Optional[Exception] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        details = details or {}
        if tool_name:
            details["tool_name"] = tool_name
        if server_name:
            details["server_name"] = server_name
        if original_error:
            details["original_error"] = str(original_error)
        super().__init__(message, details=details)
        self.tool_name = tool_name
        self.server_name = server_name
        self.original_error = original_error


class CircuitBreakerError(MCPToolRouterError):
    """Raised when circuit breaker is open"""

    def __init__(
        self,
        message: str,
        server_name: str,
        state: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        details = details or {}
        details["server_name"] = server_name
        details["circuit_state"] = state
        super().__init__(message, details=details)
        self.server_name = server_name
        self.state = state


class RateLimitError(MCPToolRouterError):
    """Raised when rate limit is exceeded"""

    def __init__(
        self,
        message: str,
        server_name: str,
        retry_after: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        details = details or {}
        details["server_name"] = server_name
        if retry_after:
            details["retry_after"] = retry_after
        super().__init__(message, details=details)
        self.server_name = server_name
        self.retry_after = retry_after


class ValidationError(MCPToolRouterError):
    """Raised when input validation fails"""

    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        details = details or {}
        if field:
            details["field"] = field
        super().__init__(message, details=details)
        self.field = field
