"""Configuration management for MCP Tool Router"""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from src.core.exceptions import ConfigurationError


class AppConfig(BaseSettings):
    """Application configuration"""

    name: str = "MCP Tool Router"
    version: str = "1.0.0"
    description: str = "Production-quality MCP Tool Router with FastAPI"
    environment: str = "development"
    debug: bool = True


class ServerConfig(BaseSettings):
    """Server configuration"""

    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 1
    reload: bool = False


class LoggingConfig(BaseSettings):
    """Logging configuration"""

    level: str = "INFO"
    format: str = "json"
    output: str = "stdout"
    file_path: str = "logs/app.log"


class CORSConfig(BaseSettings):
    """CORS configuration"""

    enabled: bool = True
    origins: List[str] = ["http://localhost:3000", "http://localhost:8000"]
    allow_credentials: bool = True
    allow_methods: List[str] = ["*"]
    allow_headers: List[str] = ["*"]


class RouterConfig(BaseSettings):
    """Router configuration"""

    max_retries: int = 3
    retry_backoff_base: int = 2
    connection_timeout: int = 30
    request_timeout: int = 60
    max_connections_per_server: int = 10
    enable_tool_namespacing: bool = True
    namespace_separator: str = ":"


class CircuitBreakerConfig(BaseSettings):
    """Circuit breaker configuration"""

    enabled: bool = True
    failure_threshold: int = 5
    timeout_seconds: int = 60
    half_open_max_calls: int = 3
    monitoring_window: int = 300


class CacheConfig(BaseSettings):
    """Cache configuration"""

    enabled: bool = True
    ttl_seconds: int = 3600
    max_size: int = 1000


class RateLimitingConfig(BaseSettings):
    """Rate limiting configuration"""

    enabled: bool = True
    requests_per_server: int = 100
    window_seconds: int = 60


class HealthCheckConfig(BaseSettings):
    """Health check configuration"""

    enabled: bool = True
    interval_seconds: int = 30
    timeout_seconds: int = 10


class MetricsConfig(BaseSettings):
    """Metrics configuration"""

    enabled: bool = True
    prometheus_enabled: bool = True
    export_port: int = 9090


class Settings(BaseSettings):
    """Main settings class combining all configurations"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        case_sensitive=False,
        extra="ignore",
    )

    # Application settings
    app_name: str = Field(default="MCP Tool Router", alias="APP_NAME")
    app_version: str = Field(default="1.0.0", alias="APP_VERSION")
    app_env: str = Field(default="development", alias="APP_ENV")
    debug: bool = Field(default=True, alias="DEBUG")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    # Server settings
    host: str = Field(default="0.0.0.0", alias="HOST")
    port: int = Field(default=8000, alias="PORT")
    workers: int = Field(default=1, alias="WORKERS")

    # CORS settings
    cors_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        alias="CORS_ORIGINS",
    )
    cors_allow_credentials: bool = Field(default=True, alias="CORS_ALLOW_CREDENTIALS")
    cors_allow_methods: List[str] = Field(default=["*"], alias="CORS_ALLOW_METHODS")
    cors_allow_headers: List[str] = Field(default=["*"], alias="CORS_ALLOW_HEADERS")

    # Router settings
    max_retries: int = Field(default=3, alias="MAX_RETRIES")
    retry_backoff_base: int = Field(default=2, alias="RETRY_BACKOFF_BASE")
    connection_timeout: int = Field(default=30, alias="CONNECTION_TIMEOUT")
    request_timeout: int = Field(default=60, alias="REQUEST_TIMEOUT")
    max_connections_per_server: int = Field(
        default=10, alias="MAX_CONNECTIONS_PER_SERVER"
    )

    # Circuit breaker settings
    circuit_breaker_failure_threshold: int = Field(
        default=5, alias="CIRCUIT_BREAKER_FAILURE_THRESHOLD"
    )
    circuit_breaker_timeout: int = Field(default=60, alias="CIRCUIT_BREAKER_TIMEOUT")
    circuit_breaker_half_open_max_calls: int = Field(
        default=3, alias="CIRCUIT_BREAKER_HALF_OPEN_MAX_CALLS"
    )

    # Cache settings
    schema_cache_ttl: int = Field(default=3600, alias="SCHEMA_CACHE_TTL")

    # Rate limiting
    rate_limit_per_server: int = Field(default=100, alias="RATE_LIMIT_PER_SERVER")
    rate_limit_window: int = Field(default=60, alias="RATE_LIMIT_WINDOW")

    # Configuration file paths
    servers_config_path: str = Field(
        default="config/servers.yaml", alias="SERVERS_CONFIG_PATH"
    )
    settings_config_path: str = Field(
        default="config/settings.yaml", alias="SETTINGS_CONFIG_PATH"
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Any) -> List[str]:
        """Parse CORS origins from string or list"""
        if isinstance(v, str):
            # Handle JSON string or comma-separated string
            if v.startswith("["):
                import json

                return json.loads(v)
            return [origin.strip() for origin in v.split(",")]
        return v

    @field_validator("cors_allow_methods", "cors_allow_headers", mode="before")
    @classmethod
    def parse_list_fields(cls, v: Any) -> List[str]:
        """Parse list fields from string or list"""
        if isinstance(v, str):
            if v.startswith("["):
                import json

                return json.loads(v)
            return [item.strip() for item in v.split(",")]
        return v


class MCPServerConnectionConfig:
    """Configuration for MCP server connection"""

    def __init__(
        self,
        type: str,
        command: Optional[str] = None,
        args: Optional[List[str]] = None,
        url: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> None:
        self.type = type
        self.command = command
        self.args = args or []
        self.url = url
        self.env = env or {}
        self.headers = headers or {}


class MCPServerConfig:
    """Configuration for individual MCP server"""

    def __init__(
        self,
        name: str,
        description: str,
        enabled: bool,
        connection: MCPServerConnectionConfig,
        options: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.name = name
        self.description = description
        self.enabled = enabled
        self.connection = connection
        self.options = options or {}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MCPServerConfig":
        """Create MCPServerConfig from dictionary"""
        connection_data = data.get("connection", {})
        connection = MCPServerConnectionConfig(
            type=connection_data.get("type", "stdio"),
            command=connection_data.get("command"),
            args=connection_data.get("args", []),
            url=connection_data.get("url"),
            env=connection_data.get("env", {}),
            headers=connection_data.get("headers", {}),
        )

        return cls(
            name=data["name"],
            description=data.get("description", ""),
            enabled=data.get("enabled", True),
            connection=connection,
            options=data.get("options", {}),
        )


class ConfigManager:
    """Manager for loading and accessing configuration"""

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self.settings = settings or Settings()
        self._servers_config: List[MCPServerConfig] = []
        self._yaml_settings: Dict[str, Any] = {}

    def load_yaml_settings(self, config_path: Optional[str] = None) -> None:
        """Load settings from YAML file"""
        path = config_path or self.settings.settings_config_path
        try:
            file_path = Path(path)
            if file_path.exists():
                with open(file_path, "r") as f:
                    self._yaml_settings = yaml.safe_load(f) or {}
        except Exception as e:
            raise ConfigurationError(
                f"Failed to load settings from {path}: {str(e)}",
                details={"path": path, "error": str(e)},
            )

    def load_servers_config(self, config_path: Optional[str] = None) -> None:
        """Load server configurations from YAML file"""
        path = config_path or self.settings.servers_config_path
        try:
            file_path = Path(path)
            if not file_path.exists():
                raise ConfigurationError(
                    f"Servers configuration file not found: {path}",
                    details={"path": path},
                )

            with open(file_path, "r") as f:
                config_data = yaml.safe_load(f) or {}

            servers_data = config_data.get("servers", [])
            self._servers_config = []

            for server_data in servers_data:
                # Substitute environment variables in config
                server_data = self._substitute_env_vars(server_data)
                server_config = MCPServerConfig.from_dict(server_data)
                self._servers_config.append(server_config)

        except ConfigurationError:
            raise
        except Exception as e:
            raise ConfigurationError(
                f"Failed to load servers configuration from {path}: {str(e)}",
                details={"path": path, "error": str(e)},
            )

    def _substitute_env_vars(self, data: Any) -> Any:
        """Recursively substitute environment variables in configuration"""
        if isinstance(data, dict):
            return {k: self._substitute_env_vars(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._substitute_env_vars(item) for item in data]
        elif isinstance(data, str):
            # Replace ${VAR_NAME} with environment variable value
            if data.startswith("${") and data.endswith("}"):
                var_name = data[2:-1]
                return os.getenv(var_name, data)
        return data

    def get_enabled_servers(self) -> List[MCPServerConfig]:
        """Get list of enabled server configurations"""
        return [server for server in self._servers_config if server.enabled]

    def get_server_config(self, name: str) -> Optional[MCPServerConfig]:
        """Get configuration for specific server"""
        for server in self._servers_config:
            if server.name == name:
                return server
        return None

    def get_yaml_setting(self, path: str, default: Any = None) -> Any:
        """
        Get setting from YAML configuration using dot notation

        Example: get_yaml_setting("router.max_retries")
        """
        keys = path.split(".")
        value = self._yaml_settings

        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default

        return value


# Global configuration instance
_config_manager: Optional[ConfigManager] = None


def get_config() -> ConfigManager:
    """Get global configuration manager instance"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
        try:
            _config_manager.load_yaml_settings()
        except ConfigurationError:
            pass  # YAML settings are optional
        try:
            _config_manager.load_servers_config()
        except ConfigurationError:
            pass  # Servers config may not exist yet

    return _config_manager


def reset_config() -> None:
    """Reset global configuration (useful for testing)"""
    global _config_manager
    _config_manager = None
