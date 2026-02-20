"""Integration tests for webhook API endpoints."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from payments.api.routes import payment_router
from payments.payment.payment import Payment, PaymentStatus, RefundStatus
from protean import current_domain


@pytest.fixture()
def client():
    app = FastAPI()
    app.include_router(payment_router)
    return TestClient(app)


_idem_counter = 0


def _create_payment(client):
    global _idem_counter
    _idem_counter += 1
    response = client.post(
        "/payments",
        json={
            "order_id": "ord-wh-001",
            "customer_id": "cust-wh-001",
            "amount": 99.99,
            "payment_method_type": "credit_card",
            "idempotency_key": f"wh-idem-{_idem_counter:04d}",
        },
    )
    return response.json()["payment_id"]


def _succeed_payment(client, payment_id):
    client.post(
        "/payments/webhook",
        json={
            "payment_id": payment_id,
            "gateway_transaction_id": f"txn-{payment_id}",
            "gateway_status": "succeeded",
        },
        headers={"X-Gateway-Signature": "test-signature"},
    )


class TestWebhookEndpoint:
    def test_success_webhook(self, client):
        payment_id = _create_payment(client)
        response = client.post(
            "/payments/webhook",
            json={
                "payment_id": payment_id,
                "gateway_transaction_id": "txn-wh-001",
                "gateway_status": "succeeded",
            },
            headers={"X-Gateway-Signature": "test-signature"},
        )
        assert response.status_code == 200
        payment = current_domain.repository_for(Payment).get(payment_id)
        assert payment.status == PaymentStatus.SUCCEEDED.value

    def test_failure_webhook(self, client):
        payment_id = _create_payment(client)
        response = client.post(
            "/payments/webhook",
            json={
                "payment_id": payment_id,
                "gateway_status": "failed",
                "failure_reason": "Card expired",
            },
            headers={"X-Gateway-Signature": "test-signature"},
        )
        assert response.status_code == 200
        payment = current_domain.repository_for(Payment).get(payment_id)
        assert payment.status == PaymentStatus.FAILED.value

    def test_invalid_signature_rejected(self, client):
        payment_id = _create_payment(client)
        response = client.post(
            "/payments/webhook",
            json={
                "payment_id": payment_id,
                "gateway_status": "succeeded",
            },
            headers={"X-Gateway-Signature": "bad-signature"},
        )
        assert response.status_code == 401


class TestRefundWebhookEndpoint:
    def test_refund_webhook_processes_successfully(self, client):
        payment_id = _create_payment(client)
        _succeed_payment(client, payment_id)

        # Request a refund
        client.post(
            f"/payments/{payment_id}/refund",
            json={"amount": 50.00, "reason": "Partial refund"},
        )

        # Get the refund_id from the persisted aggregate
        payment = current_domain.repository_for(Payment).get(payment_id)
        refund_id = str(payment.refunds[0].id)

        # Process refund webhook
        response = client.post(
            "/payments/refund/webhook",
            json={
                "payment_id": payment_id,
                "refund_id": refund_id,
                "gateway_refund_id": "gw-ref-wh-001",
            },
            headers={"X-Gateway-Signature": "test-signature"},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "refund_processed"

        # Verify refund was completed
        payment = current_domain.repository_for(Payment).get(payment_id)
        refund = payment.refunds[0]
        assert refund.status == RefundStatus.COMPLETED.value
        assert refund.gateway_refund_id == "gw-ref-wh-001"

    def test_refund_webhook_invalid_signature(self, client):
        response = client.post(
            "/payments/refund/webhook",
            json={
                "payment_id": "pay-001",
                "refund_id": "ref-001",
                "gateway_refund_id": "gw-ref-001",
            },
            headers={"X-Gateway-Signature": "bad-signature"},
        )
        assert response.status_code == 401


class TestGatewayConfigureEndpoint:
    def test_configure_gateway_default(self, client):
        response = client.post(
            "/payments/gateway/configure",
            json={"should_succeed": True, "failure_reason": "Card declined"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["gateway"] == "FakeGateway"
        assert data["should_succeed"] is True

    def test_configure_gateway_to_fail(self, client):
        response = client.post(
            "/payments/gateway/configure",
            json={"should_succeed": False, "failure_reason": "Insufficient funds"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["should_succeed"] is False
        assert data["failure_reason"] == "Insufficient funds"

    def test_configure_blocked_in_production(self, client, monkeypatch):
        monkeypatch.setenv("PROTEAN_ENV", "production")
        response = client.post(
            "/payments/gateway/configure",
            json={"should_succeed": True},
        )
        assert response.status_code == 403

    def test_configure_blocked_for_non_fake_gateway(self, client):
        from payments.gateway import set_gateway
        from payments.gateway.stripe_adapter import StripeGateway

        set_gateway(StripeGateway(api_key="sk_test", webhook_secret="whsec_test"))
        try:
            response = client.post(
                "/payments/gateway/configure",
                json={"should_succeed": True},
            )
            assert response.status_code == 400
        finally:
            from payments.gateway import reset_gateway

            reset_gateway()
