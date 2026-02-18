"""Integration tests for Order API endpoints via TestClient."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from ordering.api.routes import cart_router, order_router
from ordering.order.order import Order, OrderStatus
from protean import current_domain


@pytest.fixture()
def client():
    app = FastAPI()
    app.include_router(order_router)
    app.include_router(cart_router)
    return TestClient(app)


def _create_order(client):
    """Helper: POST /orders and return the order_id."""
    response = client.post(
        "/orders",
        json={
            "customer_id": "cust-api-001",
            "items": [
                {
                    "product_id": "prod-001",
                    "variant_id": "var-001",
                    "sku": "SKU-001",
                    "title": "Widget",
                    "quantity": 2,
                    "unit_price": 25.0,
                }
            ],
            "shipping_address": {
                "street": "123 Main",
                "city": "Town",
                "state": "CA",
                "postal_code": "90210",
                "country": "US",
            },
            "billing_address": {
                "street": "123 Main",
                "city": "Town",
                "state": "CA",
                "postal_code": "90210",
                "country": "US",
            },
            "shipping_cost": 5.0,
            "tax_total": 0.0,
            "discount_total": 0.0,
        },
    )
    assert response.status_code == 201
    return response.json()["order_id"]


def _advance_to_paid(client, order_id):
    """Helper: Advance order through confirm → payment pending → paid."""
    client.put(f"/orders/{order_id}/confirm")
    client.put(
        f"/orders/{order_id}/payment/pending",
        json={"payment_id": "pay-001", "payment_method": "card"},
    )
    client.put(
        f"/orders/{order_id}/payment/success",
        json={"payment_id": "pay-001", "amount": 55.0, "payment_method": "card"},
    )


def _advance_to_delivered(client, order_id):
    """Helper: Advance order from paid through processing → shipped → delivered."""
    client.put(f"/orders/{order_id}/processing")
    client.put(
        f"/orders/{order_id}/ship",
        json={
            "shipment_id": "ship-001",
            "carrier": "FedEx",
            "tracking_number": "TRACK-001",
        },
    )
    client.put(f"/orders/{order_id}/deliver")


class TestCreateOrderEndpoint:
    def test_create_order(self, client):
        order_id = _create_order(client)
        assert order_id is not None

        order = current_domain.repository_for(Order).get(order_id)
        assert order.customer_id == "cust-api-001"
        assert order.status == OrderStatus.CREATED.value

    def test_create_order_response_format(self, client):
        response = client.post(
            "/orders",
            json={
                "customer_id": "cust-002",
                "items": [
                    {
                        "product_id": "p1",
                        "variant_id": "v1",
                        "sku": "S1",
                        "title": "Item",
                        "quantity": 1,
                        "unit_price": 10.0,
                    }
                ],
                "shipping_address": {
                    "street": "1 St",
                    "city": "C",
                    "state": "S",
                    "postal_code": "00000",
                    "country": "US",
                },
                "billing_address": {
                    "street": "1 St",
                    "city": "C",
                    "state": "S",
                    "postal_code": "00000",
                    "country": "US",
                },
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert "order_id" in data


class TestOrderConfirmEndpoint:
    def test_confirm_order(self, client):
        order_id = _create_order(client)
        response = client.put(f"/orders/{order_id}/confirm")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

        order = current_domain.repository_for(Order).get(order_id)
        assert order.status == OrderStatus.CONFIRMED.value


class TestOrderPaymentEndpoints:
    def test_payment_pending(self, client):
        order_id = _create_order(client)
        client.put(f"/orders/{order_id}/confirm")
        response = client.put(
            f"/orders/{order_id}/payment/pending",
            json={"payment_id": "pay-001", "payment_method": "credit_card"},
        )
        assert response.status_code == 200

        order = current_domain.repository_for(Order).get(order_id)
        assert order.status == OrderStatus.PAYMENT_PENDING.value

    def test_payment_success(self, client):
        order_id = _create_order(client)
        client.put(f"/orders/{order_id}/confirm")
        client.put(
            f"/orders/{order_id}/payment/pending",
            json={"payment_id": "pay-001", "payment_method": "card"},
        )
        response = client.put(
            f"/orders/{order_id}/payment/success",
            json={"payment_id": "pay-001", "amount": 55.0, "payment_method": "card"},
        )
        assert response.status_code == 200

        order = current_domain.repository_for(Order).get(order_id)
        assert order.status == OrderStatus.PAID.value

    def test_payment_failure(self, client):
        order_id = _create_order(client)
        client.put(f"/orders/{order_id}/confirm")
        client.put(
            f"/orders/{order_id}/payment/pending",
            json={"payment_id": "pay-001", "payment_method": "card"},
        )
        response = client.put(
            f"/orders/{order_id}/payment/failure",
            json={"payment_id": "pay-001", "reason": "Declined"},
        )
        assert response.status_code == 200

        order = current_domain.repository_for(Order).get(order_id)
        assert order.status == OrderStatus.CONFIRMED.value


class TestOrderFulfillmentEndpoints:
    def test_full_fulfillment_flow(self, client):
        order_id = _create_order(client)
        _advance_to_paid(client, order_id)

        # Processing
        response = client.put(f"/orders/{order_id}/processing")
        assert response.status_code == 200

        # Ship
        response = client.put(
            f"/orders/{order_id}/ship",
            json={
                "shipment_id": "ship-001",
                "carrier": "UPS",
                "tracking_number": "1Z999",
            },
        )
        assert response.status_code == 200

        # Deliver
        response = client.put(f"/orders/{order_id}/deliver")
        assert response.status_code == 200

        # Complete
        response = client.put(f"/orders/{order_id}/complete")
        assert response.status_code == 200

        order = current_domain.repository_for(Order).get(order_id)
        assert order.status == OrderStatus.COMPLETED.value


class TestOrderCancellationEndpoints:
    def test_cancel_order(self, client):
        order_id = _create_order(client)
        response = client.put(
            f"/orders/{order_id}/cancel",
            json={"reason": "Changed mind", "cancelled_by": "Customer"},
        )
        assert response.status_code == 200

        order = current_domain.repository_for(Order).get(order_id)
        assert order.status == OrderStatus.CANCELLED.value

    def test_refund_after_cancel(self, client):
        order_id = _create_order(client)
        _advance_to_paid(client, order_id)

        client.put(
            f"/orders/{order_id}/cancel",
            json={"reason": "Defective", "cancelled_by": "Customer"},
        )
        response = client.put(
            f"/orders/{order_id}/refund",
            json={},
        )
        assert response.status_code == 200

        order = current_domain.repository_for(Order).get(order_id)
        assert order.status == OrderStatus.REFUNDED.value


class TestOrderReturnEndpoints:
    def test_return_flow(self, client):
        order_id = _create_order(client)
        _advance_to_paid(client, order_id)
        _advance_to_delivered(client, order_id)

        # Request return
        response = client.put(
            f"/orders/{order_id}/return/request",
            json={"reason": "Wrong size"},
        )
        assert response.status_code == 200

        # Approve return
        response = client.put(f"/orders/{order_id}/return/approve")
        assert response.status_code == 200

        # Record return
        response = client.put(
            f"/orders/{order_id}/return/record",
            json={},
        )
        assert response.status_code == 200

        order = current_domain.repository_for(Order).get(order_id)
        assert order.status == OrderStatus.RETURNED.value


class TestOrderItemEndpoints:
    def test_add_item(self, client):
        order_id = _create_order(client)
        response = client.post(
            f"/orders/{order_id}/items",
            json={
                "product_id": "prod-002",
                "variant_id": "var-002",
                "sku": "SKU-002",
                "title": "Gadget",
                "quantity": 1,
                "unit_price": 15.0,
            },
        )
        assert response.status_code == 200

        order = current_domain.repository_for(Order).get(order_id)
        assert len(order.items) == 2

    def test_apply_coupon(self, client):
        order_id = _create_order(client)
        response = client.post(
            f"/orders/{order_id}/coupon",
            json={"coupon_code": "SAVE20"},
        )
        assert response.status_code == 200

        order = current_domain.repository_for(Order).get(order_id)
        assert order.coupon_code == "SAVE20"
