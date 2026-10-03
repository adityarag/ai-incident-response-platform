"""
Proxy routing tests for API Gateway.
"""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


class TestGatewayProxyRouting:
    @patch("httpx.AsyncClient.post")
    def test_proxy_create_order(self, mock_post, client):
        mock_resp = AsyncMock()
        mock_resp.status_code = 201
        mock_resp.content = b'{"order_id": "ORD-123", "status": "COMPLETED"}'
        mock_post.return_value = mock_resp

        payload = {"customer_id": "C-1", "item": "Desk", "amount": 120.0}
        response = client.post("/api/v1/orders", json=payload, headers={"X-Correlation-ID": "test-corr-id"})
        assert response.status_code == 201
        data = response.json()
        assert data["order_id"] == "ORD-123"
        assert response.headers.get("X-Correlation-ID") == "test-corr-id"

    @patch("httpx.AsyncClient.get")
    def test_proxy_get_order(self, mock_get, client):
        mock_resp = AsyncMock()
        mock_resp.status_code = 200
        mock_resp.content = b'{"order_id": "ORD-123", "status": "COMPLETED"}'
        mock_get.return_value = mock_resp

        response = client.get("/api/v1/orders/ORD-123")
        assert response.status_code == 200
        data = response.json()
        assert data["order_id"] == "ORD-123"

    @patch("httpx.AsyncClient.get")
    def test_proxy_get_payment(self, mock_get, client):
        mock_resp = AsyncMock()
        mock_resp.status_code = 200
        mock_resp.content = b'{"payment_id": "PAY-888", "status": "SUCCESS"}'
        mock_get.return_value = mock_resp

        response = client.get("/api/v1/payments/PAY-888")
        assert response.status_code == 200
        data = response.json()
        assert data["payment_id"] == "PAY-888"
