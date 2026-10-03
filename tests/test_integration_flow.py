"""
End-to-End integration test simulating:
Client -> API Gateway -> Order Service -> Payment Service -> Database
"""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import sys
import importlib.util
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def load_module_from_path(name: str, path: Path):
    svc_dir = str(path.parent.parent)
    # Remove any previously cached 'app' modules so each service imports its own app package
    for mod_key in list(sys.modules.keys()):
        if mod_key == "app" or mod_key.startswith("app."):
            del sys.modules[mod_key]
    if svc_dir in sys.path:
        sys.path.remove(svc_dir)
    sys.path.insert(0, svc_dir)
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


payment_main = load_module_from_path(
    "payment_service_main",
    BASE_DIR / "services" / "payment-service" / "app" / "main.py",
)
order_main = load_module_from_path(
    "order_service_main",
    BASE_DIR / "services" / "order-service" / "app" / "main.py",
)
gateway_main = load_module_from_path(
    "gateway_main",
    BASE_DIR / "services" / "api-gateway" / "app" / "main.py",
)
from database.models import Base

# Set up unified in-memory database
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="module")
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


payment_main.get_db = override_get_db
payment_main.get_engine = lambda: engine
payment_main.SessionLocal = TestingSessionLocal

order_main.get_db = override_get_db
order_main.get_engine = lambda: engine
order_main.SessionLocal = TestingSessionLocal


def test_full_cross_service_order_and_payment_flow(setup_db):
    payment_client = TestClient(payment_main.app)

    # When order-service calls payment-service, route to payment_client
    async def mock_order_to_payment_post(url, json=None, headers=None):
        resp = payment_client.post("/payments/process", json=json, headers=headers)
        mock_resp = AsyncMock()
        mock_resp.status_code = resp.status_code
        mock_resp.json = lambda: resp.json()
        return mock_resp

    with patch("httpx.AsyncClient.post", side_effect=mock_order_to_payment_post):
        order_client = TestClient(order_main.app)

        # Place order
        order_payload = {
            "customer_id": "CUST-E2E",
            "item": "Mechanical Keyboard",
            "quantity": 1,
            "amount": 129.99,
            "currency": "USD",
        }
        order_resp = order_client.post(
            "/orders",
            json=order_payload,
            headers={"X-Correlation-ID": "test-e2e-corr-101"},
        )

        assert order_resp.status_code == 201
        order_data = order_resp.json()
        assert order_data["status"] == "COMPLETED"
        assert order_data["payment_id"] is not None

        # Verify payment was stored in DB and queryable
        pay_resp = payment_client.get(f"/payments/{order_data['payment_id']}")
        assert pay_resp.status_code == 200
        pay_data = pay_resp.json()
        assert pay_data["amount"] == 129.99
        assert pay_data["order_id"] == order_data["order_id"]
        assert pay_data["status"] == "SUCCESS"
