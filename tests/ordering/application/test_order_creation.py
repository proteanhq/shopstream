"""Application tests for order creation via domain.process()."""

import json

from ordering.order.creation import CreateOrder
from ordering.order.order import Order, OrderStatus
from protean import current_domain


def _create_order(**overrides):
    defaults = {
        "customer_id": "cust-001",
        "items": json.dumps(
            [
                {
                    "product_id": "prod-001",
                    "variant_id": "var-001",
                    "sku": "SKU-001",
                    "title": "Widget",
                    "quantity": 2,
                    "unit_price": 25.0,
                },
            ]
        ),
        "shipping_address": json.dumps(
            {
                "street": "123 Main St",
                "city": "Anytown",
                "state": "CA",
                "postal_code": "90210",
                "country": "US",
            }
        ),
        "billing_address": json.dumps(
            {
                "street": "123 Main St",
                "city": "Anytown",
                "state": "CA",
                "postal_code": "90210",
                "country": "US",
            }
        ),
        "subtotal": 50.0,
        "shipping_cost": 5.0,
        "tax_total": 4.5,
        "discount_total": 0.0,
        "grand_total": 59.5,
        "currency": "USD",
    }
    defaults.update(overrides)
    command = CreateOrder(**defaults)
    return current_domain.process(command, asynchronous=False)


class TestCreateOrderFlow:
    def test_create_order_returns_id(self):
        order_id = _create_order()
        assert order_id is not None

    def test_create_order_persists_in_event_store(self):
        order_id = _create_order()
        order = current_domain.repository_for(Order).get(order_id)
        assert str(order.id) == order_id

    def test_create_order_sets_customer(self):
        order_id = _create_order(customer_id="cust-999")
        order = current_domain.repository_for(Order).get(order_id)
        assert str(order.customer_id) == "cust-999"

    def test_create_order_sets_status_created(self):
        order_id = _create_order()
        order = current_domain.repository_for(Order).get(order_id)
        assert order.status == OrderStatus.CREATED.value

    def test_create_order_stores_events(self):
        _create_order()

        messages = current_domain.event_store.store.read("ordering::order")
        order_created_events = [
            m
            for m in messages
            if m.metadata and m.metadata.headers and m.metadata.headers.type == "Ordering.OrderCreated.v1"
        ]
        assert len(order_created_events) >= 1

    def test_create_order_with_multiple_items(self):
        items = json.dumps(
            [
                {
                    "product_id": "prod-001",
                    "variant_id": "var-001",
                    "sku": "SKU-001",
                    "title": "Widget A",
                    "quantity": 1,
                    "unit_price": 10.0,
                },
                {
                    "product_id": "prod-002",
                    "variant_id": "var-002",
                    "sku": "SKU-002",
                    "title": "Widget B",
                    "quantity": 3,
                    "unit_price": 20.0,
                },
            ]
        )
        order_id = _create_order(items=items, subtotal=70.0, grand_total=79.5)
        order = current_domain.repository_for(Order).get(order_id)
        assert len(order.items) == 2
