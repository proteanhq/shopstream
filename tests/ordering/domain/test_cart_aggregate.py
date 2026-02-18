"""Tests for ShoppingCart aggregate creation and structure."""

import json

from ordering.cart.cart import CartStatus, ShoppingCart


class TestCartCreation:
    def test_create_with_customer_id(self):
        cart = ShoppingCart.create(customer_id="cust-001")
        assert str(cart.customer_id) == "cust-001"
        assert cart.session_id is None

    def test_create_with_session_id(self):
        cart = ShoppingCart.create(session_id="sess-guest-001")
        assert cart.customer_id is None
        assert cart.session_id == "sess-guest-001"

    def test_create_sets_active_status(self):
        cart = ShoppingCart.create(customer_id="cust-001")
        assert cart.status == CartStatus.ACTIVE.value

    def test_create_starts_with_empty_items(self):
        cart = ShoppingCart.create(customer_id="cust-001")
        assert len(cart.items) == 0

    def test_create_sets_empty_coupons(self):
        cart = ShoppingCart.create(customer_id="cust-001")
        coupons = json.loads(cart.applied_coupons) if cart.applied_coupons else []
        assert coupons == []

    def test_create_sets_timestamps(self):
        cart = ShoppingCart.create(customer_id="cust-001")
        assert cart.created_at is not None
        assert cart.updated_at is not None

    def test_create_generates_id(self):
        cart = ShoppingCart.create(customer_id="cust-001")
        assert cart.id is not None
