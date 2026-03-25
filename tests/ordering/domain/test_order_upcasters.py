"""Tests for Order event upcasters — schema evolution."""

from ordering.order.events import OrderCreated
from ordering.order.upcasters import UpcastOrderCreatedV1ToV2


class TestUpcastOrderCreatedV1ToV2:
    """Unit tests for the v1 → v2 upcaster."""

    def test_adds_order_source_field(self):
        """v1 data without order_source gets 'web' added."""
        upcaster = UpcastOrderCreatedV1ToV2()
        data = {
            "order_id": "ord-001",
            "customer_id": "cust-001",
            "items": [{"sku": "S1"}],
            "shipping_address": {"street": "1 St"},
            "billing_address": {"street": "2 St"},
            "subtotal": 100.0,
            "grand_total": 110.0,
            "currency": "USD",
        }
        result = upcaster.upcast(data)
        assert result["order_source"] == "web"

    def test_preserves_existing_fields(self):
        """All existing v1 fields pass through unchanged."""
        upcaster = UpcastOrderCreatedV1ToV2()
        data = {
            "order_id": "ord-099",
            "customer_id": "cust-099",
            "items": [{"sku": "ABC"}],
            "shipping_address": {"street": "99 Elm"},
            "billing_address": {"street": "99 Oak"},
            "subtotal": 50.0,
            "shipping_cost": 5.0,
            "tax_total": 3.0,
            "discount_total": 0.0,
            "grand_total": 58.0,
            "currency": "EUR",
        }
        result = upcaster.upcast(data)
        assert result["order_id"] == "ord-099"
        assert result["customer_id"] == "cust-099"
        assert result["currency"] == "EUR"
        assert result["grand_total"] == 58.0
        assert result["order_source"] == "web"

    def test_event_class_is_version_2(self):
        assert OrderCreated.__version__ == 2
