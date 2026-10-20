"""Money written by new events comes back exact from the event store.

A payment of ``0.1 + 0.2`` and orders with totals of ``0.3`` and ``0.6`` are processed,
then read back twice: as the raw stored message, where the amount is a 4-place
string, and through the repository, where it is an exact ``Decimal``. The
tests use only the public store API, so they run the same way on the memory
store and on Message DB.
"""

from decimal import Decimal

from protean import current_domain

_ADDRESS = {"street": "1 St", "city": "C", "state": "S", "postal_code": "00000", "country": "US"}


def test_payment_amount_round_trips_as_a_4_place_string(payments_ctx):
    from payments.payment.initiation import InitiatePayment
    from payments.payment.payment import Payment

    payment_id = current_domain.process(
        InitiatePayment(
            order_id="ord-round-trip-001",
            customer_id="cust-round-trip-001",
            amount=0.1 + 0.2,
            payment_method_type="credit_card",
            idempotency_key="round-trip-idem-001",
        ),
        asynchronous=False,
    )

    messages = current_domain.event_store.store.read(f"payments::payment-{payment_id}")
    assert len(messages) >= 1
    assert messages[0].metadata.headers.type == "Payments.PaymentInitiated.v2"
    assert messages[0].data["amount"] == "0.3000"
    assert messages[0].to_domain_object().amount == Decimal("0.3")

    payment = current_domain.repository_for(Payment).get(payment_id)
    assert payment.amount.value == Decimal("0.3")


def test_order_money_round_trips_and_rebuilds_exactly(ordering_ctx):
    from ordering.order.creation import CreateOrder
    from ordering.order.order import Order

    order_id = current_domain.process(
        CreateOrder(
            customer_id="cust-round-trip-001",
            items=[
                {
                    "product_id": "prod-001",
                    "variant_id": "var-001",
                    "sku": "SKU-001",
                    "title": "Widget",
                    "quantity": 3,
                    "unit_price": 0.1,
                }
            ],
            shipping_address=_ADDRESS,
            billing_address=_ADDRESS,
            subtotal=Decimal("0.30"),
            grand_total="0.3",
        ),
        asynchronous=False,
    )

    messages = current_domain.event_store.store.read(f"ordering::order-{order_id}")
    assert len(messages) >= 1
    data = messages[0].data
    assert messages[0].metadata.headers.type == "Ordering.OrderCreated.v3"
    assert (data["subtotal"], data["grand_total"]) == ("0.3000", "0.3000")
    assert data["items"][0]["unit_price"] == "0.1000"

    # Order is event-sourced, so this load replays the stored events.
    order = current_domain.repository_for(Order).get(order_id)
    assert order.pricing.grand_total == Decimal("0.3")
    assert order.items[0].unit_price == Decimal("0.1")


def test_order_float_error_from_the_api_round_trips_and_rebuilds_exactly(ordering_ctx):
    # A client sends money as JSON numbers, so 0.1 + 0.2 arrives as
    # 0.30000000000000004. The API is where a float reaches an order.
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from ordering.api.routes import order_router
    from ordering.order.order import Order

    app = FastAPI()
    app.include_router(order_router)
    response = TestClient(app).post(
        "/orders",
        json={
            "customer_id": "cust-round-trip-002",
            "items": [
                {
                    "product_id": "prod-001",
                    "variant_id": "var-001",
                    "sku": "SKU-001",
                    "title": "Widget",
                    "quantity": 1,
                    "unit_price": 0.1 + 0.2,
                }
            ],
            "shipping_address": _ADDRESS,
            "billing_address": _ADDRESS,
            "shipping_cost": 0.1 + 0.2,
        },
    )
    assert response.status_code == 201
    order_id = response.json()["order_id"]

    messages = current_domain.event_store.store.read(f"ordering::order-{order_id}")
    assert len(messages) >= 1
    data = messages[0].data
    assert (data["subtotal"], data["shipping_cost"], data["grand_total"]) == ("0.3000", "0.3000", "0.6000")
    assert data["items"][0]["unit_price"] == "0.3000"

    order = current_domain.repository_for(Order).get(order_id)
    assert order.pricing.shipping_cost == Decimal("0.3")
    assert order.pricing.grand_total == Decimal("0.6")
    assert order.items[0].unit_price == Decimal("0.3")
