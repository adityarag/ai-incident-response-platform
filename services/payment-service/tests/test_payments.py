"""
Tests for Payment Service endpoints.
"""

import pytest


class TestPaymentEndpoints:
    def test_health(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "payment-service"
        assert "status" in data

    def test_readiness(self, client):
        response = client.get("/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "payment-service"
        assert "ready" in data

    def test_process_payment_success(self, client):
        payload = {
            "order_id": "ORD-1234",
            "customer_id": "CUST-999",
            "amount": 99.50,
            "currency": "USD",
            "idempotency_key": "key-abc-1",
        }
        response = client.post("/payments/process", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["order_id"] == "ORD-1234"
        assert data["status"] == "SUCCESS"
        assert data["amount"] == 99.50
        assert data["payment_id"].startswith("PAY-")

    def test_process_payment_idempotency(self, client):
        payload = {
            "order_id": "ORD-1234",
            "customer_id": "CUST-999",
            "amount": 99.50,
            "currency": "USD",
            "idempotency_key": "idempotent-key-100",
        }
        res1 = client.post("/payments/process", json=payload)
        assert res1.status_code == 201
        p1 = res1.json()

        # Resend with exact same idempotency_key
        res2 = client.post("/payments/process", json=payload)
        assert res2.status_code == 201
        p2 = res2.json()

        assert p1["payment_id"] == p2["payment_id"]

    def test_get_payment_not_found(self, client):
        response = client.get("/payments/PAY-NONEXISTENT")
        assert response.status_code == 404
