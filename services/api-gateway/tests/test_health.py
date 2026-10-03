"""
Tests for API Gateway health and root endpoints.

These tests verify:
1. The health endpoint returns correct structure
2. The readiness endpoint works
3. The root endpoint returns API info
4. Response schemas match expectations
"""

import pytest


class TestHealthEndpoint:
    """Tests for GET /health."""

    def test_health_returns_200(self, client):
        """Health endpoint should return 200 OK."""
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_has_status(self, client):
        """Health response must include a 'status' field."""
        response = client.get("/health")
        data = response.json()
        assert "status" in data
        assert data["status"] in ("healthy", "degraded")

    def test_health_has_service_name(self, client):
        """Health response must identify the service."""
        response = client.get("/health")
        data = response.json()
        assert data["service"] == "api-gateway"

    def test_health_has_version(self, client):
        """Health response must include version."""
        response = client.get("/health")
        data = response.json()
        assert "version" in data

    def test_health_has_timestamp(self, client):
        """Health response must include a timestamp."""
        response = client.get("/health")
        data = response.json()
        assert "timestamp" in data

    def test_health_has_checks(self, client):
        """Health response must include subsystem checks."""
        response = client.get("/health")
        data = response.json()
        assert "checks" in data
        assert "database" in data["checks"]


class TestReadinessEndpoint:
    """Tests for GET /ready."""

    def test_ready_returns_200(self, client):
        """Readiness endpoint should return 200 OK."""
        response = client.get("/ready")
        assert response.status_code == 200

    def test_ready_has_ready_field(self, client):
        """Readiness response must include 'ready' boolean."""
        response = client.get("/ready")
        data = response.json()
        assert "ready" in data
        assert isinstance(data["ready"], bool)

    def test_ready_has_service_name(self, client):
        """Readiness response must identify the service."""
        response = client.get("/ready")
        data = response.json()
        assert data["service"] == "api-gateway"


class TestRootEndpoint:
    """Tests for GET /."""

    def test_root_returns_200(self, client):
        """Root endpoint should return 200 OK."""
        response = client.get("/")
        assert response.status_code == 200

    def test_root_has_service_info(self, client):
        """Root should return service identification."""
        response = client.get("/")
        data = response.json()
        assert data["service"] == "api-gateway"
        assert "version" in data
        assert "description" in data

    def test_root_has_docs_link(self, client):
        """Root should point to API docs."""
        response = client.get("/")
        data = response.json()
        assert data["docs"] == "/docs"


class TestOpenAPIDocs:
    """Tests for auto-generated API documentation."""

    def test_openapi_schema_accessible(self, client):
        """OpenAPI schema should be accessible."""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        data = response.json()
        assert "openapi" in data
        assert "info" in data

    def test_docs_page_accessible(self, client):
        """Swagger UI docs page should be accessible."""
        response = client.get("/docs")
        assert response.status_code == 200
