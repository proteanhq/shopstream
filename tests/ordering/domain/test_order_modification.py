"""Tests for order modification — add/remove items, update quantities, apply coupons."""

import pytest
from ordering.order.events import CouponApplied, ItemAdded, ItemQuantityUpdated, ItemRemoved
from ordering.order.order import Order
from protean.exceptions import ValidationError


def _make_order():
    return Order.create(
        customer_id="cust-001",
        items_data=[
            {
                "product_id": "prod-001",
                "variant_id": "var-001",
                "sku": "SKU-001",
                "title": "Product 1",
                "quantity": 1,
                "unit_price": 25.0,
            }
        ],
        shipping_address={"street": "1 St", "city": "C", "postal_code": "00000", "country": "US"},
        billing_address={"street": "1 St", "city": "C", "postal_code": "00000", "country": "US"},
        pricing={"subtotal": 25.0, "grand_total": 25.0},
    )


class TestAddItem:
    def test_add_item_increases_count(self):
        order = _make_order()
        order._events.clear()
        order.add_item("prod-002", "var-002", "SKU-002", "Product 2", 1, 30.0)
        assert len(order.items) == 2

    def test_add_item_raises_event(self):
        order = _make_order()
        order._events.clear()
        order.add_item("prod-002", "var-002", "SKU-002", "Product 2", 1, 30.0)
        assert len(order._events) == 1
        assert isinstance(order._events[0], ItemAdded)

    def test_add_item_recalculates_pricing(self):
        order = _make_order()
        order._events.clear()
        order.add_item("prod-002", "var-002", "SKU-002", "Product 2", 2, 10.0)
        assert order.pricing.subtotal == 45.0  # 25 + 20

    def test_cannot_add_item_to_confirmed_order(self):
        order = _make_order()
        order.confirm()
        with pytest.raises(ValidationError):
            order.add_item("prod-002", "var-002", "SKU-002", "Product 2", 1, 10.0)


class TestRemoveItem:
    def test_remove_item_decreases_count(self):
        order = _make_order()
        item_id = order.items[0].id
        order._events.clear()
        order.remove_item(item_id)
        assert len(order.items) == 0

    def test_remove_item_raises_event(self):
        order = _make_order()
        item_id = order.items[0].id
        order._events.clear()
        order.remove_item(item_id)
        assert len(order._events) == 1
        assert isinstance(order._events[0], ItemRemoved)

    def test_remove_nonexistent_item_raises_error(self):
        order = _make_order()
        with pytest.raises(ValidationError):
            order.remove_item("nonexistent-id")

    def test_cannot_remove_item_from_confirmed_order(self):
        order = _make_order()
        item_id = order.items[0].id
        order.confirm()
        with pytest.raises(ValidationError):
            order.remove_item(item_id)


class TestUpdateItemQuantity:
    def test_update_quantity(self):
        order = _make_order()
        item_id = order.items[0].id
        order._events.clear()
        order.update_item_quantity(item_id, 5)
        assert order.items[0].quantity == 5

    def test_update_quantity_raises_event(self):
        order = _make_order()
        item_id = order.items[0].id
        order._events.clear()
        order.update_item_quantity(item_id, 3)
        assert len(order._events) == 1
        event = order._events[0]
        assert isinstance(event, ItemQuantityUpdated)
        assert event.previous_quantity == "1"
        assert event.new_quantity == "3"

    def test_update_quantity_recalculates_pricing(self):
        order = _make_order()
        item_id = order.items[0].id
        order._events.clear()
        order.update_item_quantity(item_id, 4)
        assert order.pricing.subtotal == 100.0  # 4 * 25.0

    def test_invalid_quantity_raises_error(self):
        order = _make_order()
        item_id = order.items[0].id
        with pytest.raises(ValidationError):
            order.update_item_quantity(item_id, 0)

    def test_nonexistent_item_raises_error(self):
        order = _make_order()
        with pytest.raises(ValidationError):
            order.update_item_quantity("nonexistent-id", 5)


class TestApplyCoupon:
    def test_apply_coupon(self):
        order = _make_order()
        order._events.clear()
        order.apply_coupon("SAVE10")
        assert order.coupon_code == "SAVE10"

    def test_apply_coupon_raises_event(self):
        order = _make_order()
        order._events.clear()
        order.apply_coupon("SAVE10")
        assert len(order._events) == 1
        event = order._events[0]
        assert isinstance(event, CouponApplied)
        assert event.coupon_code == "SAVE10"

    def test_cannot_apply_coupon_to_confirmed_order(self):
        order = _make_order()
        order.confirm()
        with pytest.raises(ValidationError):
            order.apply_coupon("SAVE10")
