"""Tests for API endpoints"""

import pytest
from fastapi.testclient import TestClient


class TestHealthEndpoints:
    """Test health and monitoring endpoints"""

    def test_root_endpoint(self, client: TestClient):
        """Test root endpoint"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "version" in data
        assert data["name"] == "MCP Tool Router"

    def test_readiness_probe(self, client: TestClient):
        """Test readiness probe endpoint"""
        response = client.get("/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"

    def test_liveness_probe(self, client: TestClient):
        """Test liveness probe endpoint"""
        response = client.get("/alive")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "alive"

    def test_health_endpoint(self, client: TestClient):
        """Test health endpoint"""
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "servers" in data
        assert "total_servers" in data
        assert "healthy_servers" in data


class TestServerEndpoints:
    """Test server management endpoints"""

    def test_list_servers_empty(self, client: TestClient):
        """Test listing servers when none connected"""
        response = client.get("/api/v1/servers")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["servers"] == []

    def test_get_server_not_found(self, client: TestClient):
        """Test getting non-existent server"""
        response = client.get("/api/v1/servers/nonexistent")
        assert response.status_code == 404
        data = response.json()
        assert "error" in data


class TestToolEndpoints:
    """Test tool endpoints"""

    def test_list_tools_empty(self, client: TestClient):
        """Test listing tools when no servers connected"""
        response = client.get("/api/v1/tools")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["tools"] == []
        assert data["by_server"] == {}

    def test_get_tool_schema_not_found(self, client: TestClient):
        """Test getting schema for non-existent tool"""
        response = client.get("/api/v1/tools/nonexistent/schema")
        assert response.status_code == 404

    def test_execute_tool_not_found(self, client: TestClient):
        """Test executing non-existent tool"""
        response = client.post(
            "/api/v1/tools/nonexistent/execute",
            json={"arguments": {}},
        )
        assert response.status_code == 404


class TestMetricsEndpoints:
    """Test metrics endpoints"""

    def test_metrics_endpoint(self, client: TestClient):
        """Test metrics endpoint"""
        response = client.get("/api/v1/metrics")
        assert response.status_code == 200
        data = response.json()
        assert "circuit_breakers" in data
        assert "schema_cache" in data
        assert "connection_pool" in data

    def test_stats_endpoint(self, client: TestClient):
        """Test stats endpoint"""
        response = client.get("/api/v1/stats")
        assert response.status_code == 200
        data = response.json()
        assert "servers" in data
        assert "tools" in data
        assert "circuit_breakers" in data
        assert "schema_cache" in data
        assert "connection_pool" in data
