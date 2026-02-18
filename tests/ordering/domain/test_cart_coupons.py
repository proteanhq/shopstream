"""Tests for cart coupon management."""

import json

import pytest
from ordering.cart.cart import ShoppingCart
from ordering.cart.events import CartCouponApplied
from protean.exceptions import ValidationError


def _make_cart():
    return ShoppingCart.create(customer_id="cust-001")


class TestApplyCoupon:
    def test_apply_coupon(self):
        cart = _make_cart()
        cart.apply_coupon("SAVE10")
        coupons = json.loads(cart.applied_coupons)
        assert "SAVE10" in coupons

    def test_apply_coupon_raises_event(self):
        cart = _make_cart()
        cart.apply_coupon("SAVE10")
        coupon_events = [e for e in cart._events if isinstance(e, CartCouponApplied)]
        assert len(coupon_events) == 1
        assert coupon_events[0].coupon_code == "SAVE10"

    def test_apply_multiple_coupons(self):
        cart = _make_cart()
        cart.apply_coupon("SAVE10")
        cart.apply_coupon("FREESHIP")
        coupons = json.loads(cart.applied_coupons)
        assert len(coupons) == 2

    def test_cannot_apply_duplicate_coupon(self):
        cart = _make_cart()
        cart.apply_coupon("SAVE10")
        with pytest.raises(ValidationError):
            cart.apply_coupon("SAVE10")

    def test_cannot_apply_to_converted_cart(self):
        cart = _make_cart()
        cart.add_item("prod-001", "var-001", 1)
        cart.convert_to_order()
        with pytest.raises(ValidationError):
            cart.apply_coupon("SAVE10")
