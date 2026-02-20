"""Integration tests for Payment API endpoints via TestClient."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from payments.api.routes import payment_router
from payments.payment.payment import Payment, PaymentStatus
from protean import current_domain


@pytest.fixture()
def client():
    app = FastAPI()
    app.include_router(payment_router)
    return TestClient(app)


def _initiate_payment(client, **overrides):
    defaults = {
        "order_id": "ord-api-001",
        "customer_id": "cust-api-001",
        "amount": 59.99,
        "currency": "USD",
        "payment_method_type": "credit_card",
        "last4": "4242",
        "idempotency_key": "api-idem-001",
    }
    defaults.update(overrides)
    response = client.post("/payments", json=defaults)
    assert response.status_code == 201
    return response.json()["payment_id"]


class TestInitiatePaymentAPI:
    def test_initiate_payment_returns_201(self, client):
        response = client.post(
            "/payments",
            json={
                "order_id": "ord-001",
                "customer_id": "cust-001",
                "amount": 59.99,
                "payment_method_type": "credit_card",
                "idempotency_key": "api-test-001",
            },
        )
        assert response.status_code == 201
        assert "payment_id" in response.json()

    def test_initiate_payment_persists(self, client):
        payment_id = _initiate_payment(client)
        payment = current_domain.repository_for(Payment).get(payment_id)
        assert payment.status == PaymentStatus.PENDING.value


class TestRetryPaymentAPI:
    def test_retry_returns_200(self, client):
        payment_id = _initiate_payment(client, idempotency_key="api-retry-001")
        # Fail it first via webhook
        client.post(
            "/payments/webhook",
            json={
                "payment_id": payment_id,
                "gateway_status": "failed",
                "failure_reason": "Declined",
            },
            headers={"X-Gateway-Signature": "test-signature"},
        )
        response = client.post(f"/payments/{payment_id}/retry")
        assert response.status_code == 200
        assert response.json()["status"] == "retry_initiated"


class TestRefundAPI:
    def test_request_refund_returns_200(self, client):
        payment_id = _initiate_payment(client, idempotency_key="api-ref-001")
        client.post(
            "/payments/webhook",
            json={
                "payment_id": payment_id,
                "gateway_transaction_id": "txn-api-001",
                "gateway_status": "succeeded",
            },
            headers={"X-Gateway-Signature": "test-signature"},
        )
        response = client.post(
            f"/payments/{payment_id}/refund",
            json={"amount": 30.00, "reason": "Changed mind"},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "refund_requested"
