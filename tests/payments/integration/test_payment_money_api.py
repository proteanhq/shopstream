"""The payment and invoice APIs take money as a JSON number or a string."""

from decimal import Decimal

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from protean import current_domain
from protean.integrations.fastapi import register_exception_handlers

from payments.api.routes import invoice_router, payment_router
from payments.invoice.invoice import Invoice
from payments.payment.payment import Payment


@pytest.fixture()
def client():
    app = FastAPI()
    app.include_router(payment_router)
    app.include_router(invoice_router)
    register_exception_handlers(app)
    return TestClient(app)


def _post_payment(client, key, amount):
    return client.post(
        "/payments",
        json={
            "order_id": f"ord-{key}",
            "customer_id": "cust-money-api",
            "amount": amount,
            "payment_method_type": "credit_card",
            "idempotency_key": f"money-api-{key}",
        },
    )


def _post_invoice(client, unit_price, tax):
    return client.post(
        "/invoices",
        json={
            "order_id": "ord-invoice-money",
            "customer_id": "cust-money-api",
            "line_items": [{"description": "Widget", "quantity": 2, "unit_price": unit_price}],
            "tax": tax,
        },
    )


class TestPaymentMoneyIn:
    @pytest.mark.parametrize(("key", "amount"), [("number", 49.99), ("string", "49.99"), ("padded", "49.9900")])
    def test_number_and_string_amounts_store_the_same_decimal(self, client, key, amount):
        response = _post_payment(client, key, amount)
        assert response.status_code == 201

        payment = current_domain.repository_for(Payment).get(response.json()["payment_id"])
        assert str(payment.amount.value) == "49.9900"

    @pytest.mark.parametrize(
        ("key", "amount"),
        [
            ("five-places", "49.99001"),
            ("eight-places", "49.99000001"),
            ("large-five-places", "123456789012.00001"),
            ("below-a-cent", "0.00000001"),
        ],
    )
    def test_string_amount_with_a_fifth_place_is_rejected(self, client, key, amount):
        response = _post_payment(client, key, amount)

        assert response.status_code == 400
        assert f"Amount ({Decimal(amount)}) must have no more than 4 decimal places" in str(response.json())

    def test_number_amount_with_float_error_is_rounded(self, client):
        response = _post_payment(client, "float-error", 0.1 + 0.2)
        assert response.status_code == 201

        payment = current_domain.repository_for(Payment).get(response.json()["payment_id"])
        assert str(payment.amount.value) == "0.3000"

    def test_refund_amount_as_a_string_is_accepted(self, client):
        payment_id = _post_payment(client, "refund-string", 20).json()["payment_id"]
        client.post(
            "/payments/webhook",
            json={
                "payment_id": payment_id,
                "gateway_transaction_id": "txn-refund-string",
                "gateway_status": "succeeded",
            },
            headers={"X-Gateway-Signature": "test-signature"},
        )

        response = client.post(f"/payments/{payment_id}/refund", json={"amount": "7.25", "reason": "Partial"})

        assert response.status_code == 200
        refunds = current_domain.repository_for(Payment).get(payment_id).refunds
        assert [str(refund.amount) for refund in refunds] == ["7.2500"]


class TestInvoiceMoneyIn:
    @pytest.mark.parametrize(("unit_price", "tax"), [(25.5, 4.0), ("25.5", "4"), ("25.5000", "4.0000")])
    def test_number_and_string_amounts_total_the_invoice_the_same(self, client, unit_price, tax):
        response = _post_invoice(client, unit_price, tax)
        assert response.status_code == 201

        invoice = current_domain.repository_for(Invoice).get(response.json()["invoice_id"])
        assert str(invoice.line_items[0].unit_price) == "25.5000"
        assert (str(invoice.subtotal), str(invoice.tax), str(invoice.total)) == ("51.0000", "4.0000", "55.0000")

    @pytest.mark.parametrize(
        ("unit_price", "tax"),
        [("25.50001", "4"), ("25.5", "4.00001"), ("25.50000001", "4"), ("123456789012.00001", "4")],
    )
    def test_a_fifth_place_is_rejected(self, client, unit_price, tax):
        response = _post_invoice(client, unit_price, tax)
        assert response.status_code == 422
