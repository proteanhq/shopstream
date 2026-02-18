"""Tests for cart item management."""

import pytest
from ordering.cart.cart import ShoppingCart
from ordering.cart.events import CartItemAdded, CartItemRemoved, CartQuantityUpdated
from protean.exceptions import ValidationError


def _make_cart():
    return ShoppingCart.create(customer_id="cust-001")


class TestAddItem:
    def test_add_item(self):
        cart = _make_cart()
        cart.add_item("prod-001", "var-001", 2)
        assert len(cart.items) == 1
        assert cart.items[0].quantity == 2

    def test_add_item_raises_event(self):
        cart = _make_cart()
        cart.add_item("prod-001", "var-001", 1)
        # Filter for CartItemAdded events
        added_events = [e for e in cart._events if isinstance(e, CartItemAdded)]
        assert len(added_events) == 1
        event = added_events[0]
        assert event.product_id == "prod-001"
        assert event.quantity == 1

    def test_add_same_product_increases_quantity(self):
        cart = _make_cart()
        cart.add_item("prod-001", "var-001", 1)
        cart.add_item("prod-001", "var-001", 2)
        assert len(cart.items) == 1
        assert cart.items[0].quantity == 3

    def test_add_different_variant_creates_new_item(self):
        cart = _make_cart()
        cart.add_item("prod-001", "var-001", 1)
        cart.add_item("prod-001", "var-002", 1)
        assert len(cart.items) == 2

    def test_cannot_add_to_converted_cart(self):
        cart = _make_cart()
        cart.add_item("prod-001", "var-001", 1)
        cart.convert_to_order()
        with pytest.raises(ValidationError):
            cart.add_item("prod-002", "var-002", 1)


class TestUpdateQuantity:
    def test_update_quantity(self):
        cart = _make_cart()
        cart.add_item("prod-001", "var-001", 1)
        item_id = cart.items[0].id
        cart.update_item_quantity(item_id, 5)
        assert cart.items[0].quantity == 5

    def test_update_quantity_raises_event(self):
        cart = _make_cart()
        cart.add_item("prod-001", "var-001", 1)
        item_id = cart.items[0].id
        cart._events.clear()
        cart.update_item_quantity(item_id, 3)
        assert len(cart._events) == 1
        event = cart._events[0]
        assert isinstance(event, CartQuantityUpdated)
        assert event.previous_quantity == 1
        assert event.new_quantity == 3

    def test_update_nonexistent_item(self):
        cart = _make_cart()
        with pytest.raises(ValidationError):
            cart.update_item_quantity("nonexistent", 5)


class TestRemoveItem:
    def test_remove_item(self):
        cart = _make_cart()
        cart.add_item("prod-001", "var-001", 1)
        item_id = cart.items[0].id
        cart.remove_item(item_id)
        assert len(cart.items) == 0

    def test_remove_item_raises_event(self):
        cart = _make_cart()
        cart.add_item("prod-001", "var-001", 1)
        item_id = cart.items[0].id
        cart._events.clear()
        cart.remove_item(item_id)
        assert len(cart._events) == 1
        assert isinstance(cart._events[0], CartItemRemoved)

    def test_remove_nonexistent_item(self):
        cart = _make_cart()
        with pytest.raises(ValidationError):
            cart.remove_item("nonexistent")

    def test_cannot_remove_from_abandoned_cart(self):
        cart = _make_cart()
        cart.add_item("prod-001", "var-001", 1)
        item_id = cart.items[0].id
        cart.abandon()
        with pytest.raises(ValidationError):
            cart.remove_item(item_id)
