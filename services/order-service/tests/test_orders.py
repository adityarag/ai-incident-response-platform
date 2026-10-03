"""
Tests for Order Service endpoints.
"""

from unittest.mock import AsyncMock, patch

import httpx
import pytest


class TestOrderEndpoints:
    def test_health(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "order-service"
        assert "status" in data

    def test_readiness(self, client):
        response = client.get("/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "order-service"
        assert "ready" in data

    @patch("httpx.AsyncClient.post")
    def test_create_order_payment_success(self, mock_post, client):
        # Mock payment service 201 SUCCESS response
        mock_resp = AsyncMock()
        mock_resp.status_code = 201
        mock_resp.json = lambda: {
            "payment_id": "PAY-TEST-99",
            "order_id": "ORD-123",
            "status": "SUCCESS",
            "amount": 150.0,
        }
        mock_post.return_value = mock_resp

        payload = {
            "customer_id": "CUST-42",
            "item": "Laptop Stand",
            "quantity": 2,
            "amount": 150.0,
            "currency": "USD",
        }
        response = client.post("/orders", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["customer_id"] == "CUST-42"
        assert data["status"] == "COMPLETED"
        assert data["payment_id"] == "PAY-TEST-99"

    @patch("httpx.AsyncClient.post")
    def test_create_order_payment_down(self, mock_post, client):
        # Mock payment service connection error
        mock_post.side_effect = httpx.RequestError("Connection refused")

        payload = {
            "customer_id": "CUST-42",
            "item": "Keyboard",
            "quantity": 1,
            "amount": 75.0,
            "currency": "USD",
        }
        response = client.post("/orders", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "FAILED"
        assert "unreachable" in data["failure_reason"]

    def test_get_order_not_found(self, client):
        response = client.get("/orders/ORD-NONEXISTENT")
        assert response.status_code == 404
