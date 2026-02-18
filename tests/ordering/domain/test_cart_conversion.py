"""Tests for cart-to-order conversion."""

import pytest
from ordering.cart.cart import CartStatus, ShoppingCart
from ordering.cart.events import CartConverted
from protean.exceptions import ValidationError


def _make_cart_with_items():
    cart = ShoppingCart.create(customer_id="cust-001")
    cart.add_item("prod-001", "var-001", 2)
    cart.add_item("prod-002", "var-002", 1)
    cart._events.clear()
    return cart


class TestConvertToOrder:
    def test_converts_to_converted_status(self):
        cart = _make_cart_with_items()
        cart.convert_to_order()
        assert cart.status == CartStatus.CONVERTED.value

    def test_raises_cart_converted_event(self):
        cart = _make_cart_with_items()
        cart.convert_to_order()
        assert len(cart._events) == 1
        event = cart._events[0]
        assert isinstance(event, CartConverted)
        assert event.customer_id == "cust-001"

    def test_event_contains_items_snapshot(self):
        cart = _make_cart_with_items()
        cart.convert_to_order()
        event = cart._events[0]
        assert event.items is not None
        assert "prod-001" in event.items

    def test_cannot_convert_empty_cart(self):
        cart = ShoppingCart.create(customer_id="cust-001")
        with pytest.raises(ValidationError):
            cart.convert_to_order()

    def test_cannot_convert_already_converted_cart(self):
        cart = _make_cart_with_items()
        cart.convert_to_order()
        with pytest.raises(ValidationError):
            cart.convert_to_order()

    def test_cannot_convert_abandoned_cart(self):
        cart = _make_cart_with_items()
        cart.abandon()
        with pytest.raises(ValidationError):
            cart.convert_to_order()
