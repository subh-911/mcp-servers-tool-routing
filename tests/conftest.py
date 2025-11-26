"""Pytest configuration and fixtures"""

import pytest
from typing import AsyncGenerator

from fastapi.testclient import TestClient
from httpx import AsyncClient

from src.core.config import reset_config
from src.core.router import MCPToolRouter
from src.main import create_app


@pytest.fixture(autouse=True)
def reset_configuration():
    """Reset configuration before each test"""
    reset_config()
    yield
    reset_config()


@pytest.fixture
def router() -> MCPToolRouter:
    """Create a fresh router instance for testing"""
    return MCPToolRouter(
        max_retries=2,
        retry_backoff_base=2,
        connection_timeout=10,
        request_timeout=30,
        circuit_breaker_enabled=True,
        circuit_breaker_failure_threshold=3,
        circuit_breaker_timeout=30,
        schema_cache_ttl=3600,
    )


@pytest.fixture
def app():
    """Create FastAPI application for testing"""
    return create_app()


@pytest.fixture
def client(app):
    """Create test client"""
    return TestClient(app)


@pytest.fixture
async def async_client(app) -> AsyncGenerator:
    """Create async test client"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
