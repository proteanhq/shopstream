"""Tests for cart management — merge and abandon."""

import pytest
from ordering.cart.cart import CartStatus, ShoppingCart
from ordering.cart.events import CartAbandoned, CartsMerged
from protean.exceptions import ValidationError


def _make_cart():
    return ShoppingCart.create(customer_id="cust-001")


class TestMergeGuestCart:
    def test_merge_adds_items(self):
        cart = _make_cart()
        guest_items = [
            {"product_id": "prod-001", "variant_id": "var-001", "quantity": 2},
            {"product_id": "prod-002", "variant_id": "var-002", "quantity": 1},
        ]
        cart.merge_guest_cart(guest_items)
        assert len(cart.items) == 2

    def test_merge_increases_existing_quantity(self):
        cart = _make_cart()
        cart.add_item("prod-001", "var-001", 1)
        cart._events.clear()
        guest_items = [
            {"product_id": "prod-001", "variant_id": "var-001", "quantity": 3},
        ]
        cart.merge_guest_cart(guest_items)
        assert cart.items[0].quantity == 4  # 1 + 3

    def test_merge_raises_event(self):
        cart = _make_cart()
        guest_items = [
            {"product_id": "prod-001", "variant_id": "var-001", "quantity": 1},
        ]
        cart.merge_guest_cart(guest_items)
        merge_events = [e for e in cart._events if isinstance(e, CartsMerged)]
        assert len(merge_events) == 1
        assert merge_events[0].items_merged_count == 1

    def test_cannot_merge_into_converted_cart(self):
        cart = _make_cart()
        cart.add_item("prod-001", "var-001", 1)
        cart.convert_to_order()
        with pytest.raises(ValidationError):
            cart.merge_guest_cart([{"product_id": "p", "variant_id": "v", "quantity": 1}])


class TestAbandonCart:
    def test_abandon_sets_status(self):
        cart = _make_cart()
        cart.abandon()
        assert cart.status == CartStatus.ABANDONED.value

    def test_abandon_raises_event(self):
        cart = _make_cart()
        cart.abandon()
        abandon_events = [e for e in cart._events if isinstance(e, CartAbandoned)]
        assert len(abandon_events) == 1
        assert abandon_events[0].abandoned_at is not None

    def test_cannot_abandon_converted_cart(self):
        cart = _make_cart()
        cart.add_item("prod-001", "var-001", 1)
        cart.convert_to_order()
        with pytest.raises(ValidationError):
            cart.abandon()

    def test_cannot_abandon_already_abandoned_cart(self):
        cart = _make_cart()
        cart.abandon()
        with pytest.raises(ValidationError):
            cart.abandon()
