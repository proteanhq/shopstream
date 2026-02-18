"""Tests for Order aggregate creation and structure."""

import pytest
from ordering.order.events import OrderCreated
from ordering.order.order import Order, OrderPricing, OrderStatus, ShippingAddress
from protean.exceptions import ValidationError


def _make_order(**overrides):
    defaults = {
        "customer_id": "cust-001",
        "items_data": [
            {
                "product_id": "prod-001",
                "variant_id": "var-001",
                "sku": "TSHIRT-BLK-M",
                "title": "Black T-Shirt (M)",
                "quantity": 2,
                "unit_price": 29.99,
            }
        ],
        "shipping_address": {
            "street": "123 Main St",
            "city": "Springfield",
            "state": "IL",
            "postal_code": "62701",
            "country": "US",
        },
        "billing_address": {
            "street": "456 Oak Ave",
            "city": "Springfield",
            "state": "IL",
            "postal_code": "62701",
            "country": "US",
        },
        "pricing": {
            "subtotal": 59.98,
            "shipping_cost": 5.99,
            "tax_total": 4.80,
            "discount_total": 0.0,
            "grand_total": 70.77,
            "currency": "USD",
        },
    }
    defaults.update(overrides)
    return Order.create(**defaults)


class TestOrderCreation:
    def test_create_sets_customer_id(self):
        order = _make_order()
        assert str(order.customer_id) == "cust-001"

    def test_create_sets_status_to_created(self):
        order = _make_order()
        assert order.status == OrderStatus.CREATED.value

    def test_create_populates_items(self):
        order = _make_order()
        assert len(order.items) == 1
        item = order.items[0]
        assert item.sku == "TSHIRT-BLK-M"
        assert item.quantity == 2
        assert item.unit_price == 29.99

    def test_create_sets_shipping_address(self):
        order = _make_order()
        assert order.shipping_address.street == "123 Main St"
        assert order.shipping_address.city == "Springfield"
        assert order.shipping_address.country == "US"

    def test_create_sets_billing_address(self):
        order = _make_order()
        assert order.billing_address.street == "456 Oak Ave"

    def test_create_sets_pricing(self):
        order = _make_order()
        assert order.pricing.subtotal == 59.98
        assert order.pricing.shipping_cost == 5.99
        assert order.pricing.tax_total == 4.80
        assert order.pricing.grand_total == 70.77
        assert order.pricing.currency == "USD"

    def test_create_sets_timestamps(self):
        order = _make_order()
        assert order.created_at is not None
        assert order.updated_at is not None

    def test_create_generates_id(self):
        order = _make_order()
        assert order.id is not None

    def test_create_with_multiple_items(self):
        order = _make_order(
            items_data=[
                {
                    "product_id": "prod-001",
                    "variant_id": "var-001",
                    "sku": "TSHIRT-BLK-M",
                    "title": "Black T-Shirt",
                    "quantity": 1,
                    "unit_price": 29.99,
                },
                {
                    "product_id": "prod-002",
                    "variant_id": "var-002",
                    "sku": "JEANS-BLU-32",
                    "title": "Blue Jeans",
                    "quantity": 1,
                    "unit_price": 49.99,
                },
            ],
            pricing={
                "subtotal": 79.98,
                "shipping_cost": 0.0,
                "tax_total": 0.0,
                "discount_total": 0.0,
                "grand_total": 79.98,
                "currency": "USD",
            },
        )
        assert len(order.items) == 2


class TestOrderCreatedEvent:
    def test_create_raises_order_created_event(self):
        order = _make_order()
        assert len(order._events) == 1
        event = order._events[0]
        assert isinstance(event, OrderCreated)

    def test_event_contains_order_id(self):
        order = _make_order()
        event = order._events[0]
        assert event.order_id == str(order.id)

    def test_event_contains_customer_id(self):
        order = _make_order()
        event = order._events[0]
        assert event.customer_id == "cust-001"

    def test_event_contains_pricing(self):
        order = _make_order()
        event = order._events[0]
        assert event.subtotal == 59.98
        assert event.grand_total == 70.77

    def test_event_contains_items_json(self):
        order = _make_order()
        event = order._events[0]
        assert event.items is not None
        assert "TSHIRT-BLK-M" in event.items

    def test_event_contains_addresses_json(self):
        order = _make_order()
        event = order._events[0]
        assert "123 Main St" in event.shipping_address
        assert "456 Oak Ave" in event.billing_address

    def test_event_contains_timestamp(self):
        order = _make_order()
        event = order._events[0]
        assert event.created_at is not None


class TestShippingAddressVO:
    def test_construction(self):
        addr = ShippingAddress(
            street="123 Main St",
            city="Springfield",
            state="IL",
            postal_code="62701",
            country="US",
        )
        assert addr.street == "123 Main St"
        assert addr.city == "Springfield"

    def test_requires_street(self):
        with pytest.raises(ValidationError):
            ShippingAddress(
                city="Springfield",
                postal_code="62701",
                country="US",
            )

    def test_state_is_optional(self):
        addr = ShippingAddress(
            street="123 Main St",
            city="Springfield",
            postal_code="62701",
            country="US",
        )
        assert addr.state is None


class TestOrderPricingVO:
    def test_construction(self):
        pricing = OrderPricing(
            subtotal=100.0,
            shipping_cost=10.0,
            tax_total=8.0,
            discount_total=5.0,
            grand_total=113.0,
            currency="USD",
        )
        assert pricing.grand_total == 113.0

    def test_defaults(self):
        pricing = OrderPricing()
        assert pricing.subtotal == 0.0
        assert pricing.shipping_cost == 0.0
        assert pricing.currency == "USD"
