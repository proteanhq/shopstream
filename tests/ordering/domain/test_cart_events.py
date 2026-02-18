"""Tests for all 7 ShoppingCart events — construction and field completeness."""

from datetime import UTC, datetime

from ordering.cart.events import (
    CartAbandoned,
    CartConverted,
    CartCouponApplied,
    CartItemAdded,
    CartItemRemoved,
    CartQuantityUpdated,
    CartsMerged,
)


class TestCartItemAddedEvent:
    def test_version(self):
        assert CartItemAdded.__version__ == "v1"

    def test_construction(self):
        event = CartItemAdded(
            cart_id="cart-001",
            item_id="item-001",
            product_id="prod-001",
            variant_id="var-001",
            quantity=2,
        )
        assert event.cart_id == "cart-001"
        assert event.item_id == "item-001"
        assert event.quantity == 2


class TestCartQuantityUpdatedEvent:
    def test_construction(self):
        event = CartQuantityUpdated(
            cart_id="cart-001",
            item_id="item-001",
            previous_quantity=1,
            new_quantity=5,
        )
        assert event.previous_quantity == 1
        assert event.new_quantity == 5


class TestCartItemRemovedEvent:
    def test_construction(self):
        event = CartItemRemoved(cart_id="cart-001", item_id="item-001")
        assert event.item_id == "item-001"


class TestCartCouponAppliedEvent:
    def test_construction(self):
        event = CartCouponApplied(cart_id="cart-001", coupon_code="SAVE10")
        assert event.coupon_code == "SAVE10"


class TestCartsMergedEvent:
    def test_construction(self):
        event = CartsMerged(
            cart_id="cart-001",
            source_session_id="sess-guest-001",
            items_merged_count=3,
        )
        assert event.items_merged_count == 3


class TestCartConvertedEvent:
    def test_construction(self):
        event = CartConverted(
            cart_id="cart-001",
            customer_id="cust-001",
            items='[{"product_id": "p1", "variant_id": "v1", "quantity": 2}]',
        )
        assert event.customer_id == "cust-001"
        assert "p1" in event.items


class TestCartAbandonedEvent:
    def test_construction(self):
        now = datetime.now(UTC)
        event = CartAbandoned(cart_id="cart-001", abandoned_at=now)
        assert event.abandoned_at == now
