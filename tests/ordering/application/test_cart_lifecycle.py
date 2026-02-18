"""Application tests for cart lifecycle: create → add items → coupon → convert/abandon."""

import json

from ordering.cart.cart import CartStatus, ShoppingCart
from ordering.cart.conversion import ConvertToOrder
from ordering.cart.coupons import ApplyCouponToCart
from ordering.cart.items import AddToCart
from ordering.cart.management import AbandonCart, CreateCart, MergeGuestCart
from protean import current_domain


def _create_cart_with_item():
    cart_id = current_domain.process(
        CreateCart(customer_id="cust-001"),
        asynchronous=False,
    )
    current_domain.process(
        AddToCart(
            cart_id=cart_id,
            product_id="prod-001",
            variant_id="var-001",
            quantity=2,
        ),
        asynchronous=False,
    )
    return cart_id


class TestCartCreation:
    def test_create_cart_returns_id(self):
        cart_id = current_domain.process(
            CreateCart(customer_id="cust-001"),
            asynchronous=False,
        )
        assert cart_id is not None

    def test_create_cart_persists(self):
        cart_id = current_domain.process(
            CreateCart(customer_id="cust-001"),
            asynchronous=False,
        )
        cart = current_domain.repository_for(ShoppingCart).get(cart_id)
        assert str(cart.customer_id) == "cust-001"
        assert cart.status == CartStatus.ACTIVE.value


class TestCartCouponFlow:
    def test_apply_coupon_persists(self):
        cart_id = _create_cart_with_item()
        current_domain.process(
            ApplyCouponToCart(cart_id=cart_id, coupon_code="SAVE10"),
            asynchronous=False,
        )
        cart = current_domain.repository_for(ShoppingCart).get(cart_id)
        coupons = json.loads(cart.applied_coupons)
        assert "SAVE10" in coupons


class TestCartConversion:
    def test_convert_to_order_persists(self):
        cart_id = _create_cart_with_item()
        current_domain.process(
            ConvertToOrder(cart_id=cart_id),
            asynchronous=False,
        )
        cart = current_domain.repository_for(ShoppingCart).get(cart_id)
        assert cart.status == CartStatus.CONVERTED.value


class TestCartAbandonment:
    def test_abandon_cart_persists(self):
        cart_id = current_domain.process(
            CreateCart(customer_id="cust-001"),
            asynchronous=False,
        )
        current_domain.process(
            AbandonCart(cart_id=cart_id),
            asynchronous=False,
        )
        cart = current_domain.repository_for(ShoppingCart).get(cart_id)
        assert cart.status == CartStatus.ABANDONED.value


class TestGuestCartMerge:
    def test_merge_guest_cart_persists(self):
        cart_id = _create_cart_with_item()
        guest_items = json.dumps(
            [
                {"product_id": "prod-002", "variant_id": "var-002", "quantity": 3},
            ]
        )
        current_domain.process(
            MergeGuestCart(cart_id=cart_id, guest_cart_items=guest_items),
            asynchronous=False,
        )
        cart = current_domain.repository_for(ShoppingCart).get(cart_id)
        assert len(cart.items) == 2
