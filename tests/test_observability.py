"""
Unit tests for the Observability and Metrics module.
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from observability.telemetry import (
    REGISTRY,
    HTTP_REQUESTS_TOTAL,
    HTTP_REQUEST_DURATION_SECONDS,
    HTTP_REQUESTS_IN_PROGRESS,
    attach_observability,
    setup_service_logger,
)


@pytest.fixture
def test_app():
    app = FastAPI()
    attach_observability(app, "test-service")

    @app.get("/test/hello")
    def hello():
        return {"message": "hello"}

    @app.get("/test/items/{item_id}")
    def get_item(item_id: str):
        return {"item_id": item_id}

    return app


@pytest.fixture
def client(test_app):
    return TestClient(test_app)


class TestObservabilityMetrics:
    def test_metrics_endpoint_exists(self, client):
        response = client.get("/metrics")
        assert response.status_code == 200
        assert "text/plain" in response.headers["content-type"]

    def test_metrics_recorded_on_request(self, client):
        # Trigger requests
        r1 = client.get("/test/hello")
        assert r1.status_code == 200

        r2 = client.get("/test/items/123")
        assert r2.status_code == 200

        # Scrape metrics
        metrics_resp = client.get("/metrics")
        content = metrics_resp.text

        # Verify prometheus metric names are present
        assert "http_requests_total" in content
        assert "http_request_duration_seconds" in content
        assert 'service="test-service"' in content
        assert 'endpoint="/test/hello"' in content
        assert 'status="200"' in content

    def test_logger_setup(self):
        logger = setup_service_logger("test-logging-svc")
        assert logger.name == "test-logging-svc"
        assert len(logger.handlers) >= 1
