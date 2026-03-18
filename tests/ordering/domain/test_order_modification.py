"""Tests for order modification — add/remove items, update quantities, apply coupons."""

import pytest
from protean.exceptions import ValidationError
from protean.testing import given

from ordering.order.confirmation import ConfirmOrder
from ordering.order.creation import CreateOrder
from ordering.order.events import CouponApplied, ItemAdded, ItemQuantityUpdated, ItemRemoved
from ordering.order.modification import AddItem, ApplyCoupon, RemoveItem, UpdateItemQuantity
from ordering.order.order import Order

CREATE_ORDER_ARGS = {
    "customer_id": "cust-001",
    "items": [
        {
            "product_id": "prod-001",
            "variant_id": "var-001",
            "sku": "SKU-001",
            "title": "Product 1",
            "quantity": 1,
            "unit_price": 25.0,
        }
    ],
    "shipping_address": {"street": "1 St", "city": "C", "postal_code": "00000", "country": "US"},
    "billing_address": {"street": "1 St", "city": "C", "postal_code": "00000", "country": "US"},
    "subtotal": 25.0,
    "shipping_cost": 0.0,
    "tax_total": 0.0,
    "discount_total": 0.0,
    "grand_total": 25.0,
    "currency": "USD",
}


def _created_result():
    result = given(Order).process(CreateOrder(**CREATE_ORDER_ARGS))
    return result, str(result.aggregate.id)


class TestAddItem:
    def test_add_item_increases_count(self):
        result, order_id = _created_result()
        result = result.process(
            AddItem(
                order_id=order_id,
                product_id="prod-002",
                variant_id="var-002",
                sku="SKU-002",
                title="Product 2",
                quantity=1,
                unit_price=30.0,
            )
        )
        assert len(result.aggregate.items) == 2

    def test_add_item_raises_event(self):
        result, order_id = _created_result()
        result = result.process(
            AddItem(
                order_id=order_id,
                product_id="prod-002",
                variant_id="var-002",
                sku="SKU-002",
                title="Product 2",
                quantity=1,
                unit_price=30.0,
            )
        )
        assert len(result.events) == 1
        assert ItemAdded in result.events

    def test_add_item_recalculates_pricing(self):
        result, order_id = _created_result()
        result = result.process(
            AddItem(
                order_id=order_id,
                product_id="prod-002",
                variant_id="var-002",
                sku="SKU-002",
                title="Product 2",
                quantity=2,
                unit_price=10.0,
            )
        )
        assert result.aggregate.pricing.subtotal == 45.0  # 25 + 20

    def test_cannot_add_item_to_confirmed_order(self):
        result, order_id = _created_result()
        result = result.process(ConfirmOrder(order_id=order_id))
        result = result.process(
            AddItem(
                order_id=order_id,
                product_id="prod-002",
                variant_id="var-002",
                sku="SKU-002",
                title="Product 2",
                quantity=1,
                unit_price=10.0,
            )
        )
        assert result.rejected


class TestRemoveItem:
    def test_remove_item_decreases_count(self):
        result, order_id = _created_result()
        item_id = str(result.aggregate.items[0].id)
        result = result.process(RemoveItem(order_id=order_id, item_id=item_id))
        assert len(result.aggregate.items) == 0

    def test_remove_item_raises_event(self):
        result, order_id = _created_result()
        item_id = str(result.aggregate.items[0].id)
        result = result.process(RemoveItem(order_id=order_id, item_id=item_id))
        assert len(result.events) == 1
        assert ItemRemoved in result.events

    def test_remove_nonexistent_item_raises_error(self):
        result, order_id = _created_result()
        result = result.process(RemoveItem(order_id=order_id, item_id="nonexistent-id"))
        assert result.rejected

    def test_cannot_remove_item_from_confirmed_order(self):
        result, order_id = _created_result()
        item_id = str(result.aggregate.items[0].id)
        result = result.process(ConfirmOrder(order_id=order_id))
        result = result.process(RemoveItem(order_id=order_id, item_id=item_id))
        assert result.rejected


class TestUpdateItemQuantity:
    def test_update_quantity(self):
        result, order_id = _created_result()
        item_id = str(result.aggregate.items[0].id)
        result = result.process(UpdateItemQuantity(order_id=order_id, item_id=item_id, new_quantity=5))
        assert result.aggregate.items[0].quantity == 5

    def test_update_quantity_raises_event(self):
        result, order_id = _created_result()
        item_id = str(result.aggregate.items[0].id)
        result = result.process(UpdateItemQuantity(order_id=order_id, item_id=item_id, new_quantity=3))
        assert len(result.events) == 1
        assert ItemQuantityUpdated in result.events
        event = result.events[ItemQuantityUpdated]
        assert event.previous_quantity == "1"
        assert event.new_quantity == "3"

    def test_update_quantity_recalculates_pricing(self):
        result, order_id = _created_result()
        item_id = str(result.aggregate.items[0].id)
        result = result.process(UpdateItemQuantity(order_id=order_id, item_id=item_id, new_quantity=4))
        assert result.aggregate.pricing.subtotal == 100.0  # 4 * 25.0

    def test_invalid_quantity_raises_error(self):
        result, order_id = _created_result()
        item_id = str(result.aggregate.items[0].id)
        with pytest.raises(ValidationError):
            UpdateItemQuantity(order_id=order_id, item_id=item_id, new_quantity=0)

    def test_nonexistent_item_raises_error(self):
        result, order_id = _created_result()
        result = result.process(UpdateItemQuantity(order_id=order_id, item_id="nonexistent-id", new_quantity=5))
        assert result.rejected


class TestApplyCoupon:
    def test_apply_coupon(self):
        result, order_id = _created_result()
        result = result.process(ApplyCoupon(order_id=order_id, coupon_code="SAVE10"))
        assert result.aggregate.coupon_code == "SAVE10"

    def test_apply_coupon_raises_event(self):
        result, order_id = _created_result()
        result = result.process(ApplyCoupon(order_id=order_id, coupon_code="SAVE10"))
        assert len(result.events) == 1
        assert CouponApplied in result.events
        event = result.events[CouponApplied]
        assert event.coupon_code == "SAVE10"

    def test_cannot_apply_coupon_to_confirmed_order(self):
        result, order_id = _created_result()
        result = result.process(ConfirmOrder(order_id=order_id))
        result = result.process(ApplyCoupon(order_id=order_id, coupon_code="SAVE10"))
        assert result.rejected
