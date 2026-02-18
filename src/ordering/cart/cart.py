"""Shopping Cart aggregate (CQRS) — ephemeral cart that converts to an Order at checkout.

The cart is a standard CQRS aggregate (not event sourced). It tracks items
selected by a customer or guest, supports coupon application, guest cart
merging, and converts to an Order at checkout.
"""

import json
from datetime import UTC, datetime
from enum import Enum

from protean import invariant
from protean.exceptions import ValidationError
from protean.fields import DateTime, HasMany, Identifier, Integer, String, Text

from ordering.cart.events import (
    CartAbandoned,
    CartConverted,
    CartCouponApplied,
    CartItemAdded,
    CartItemRemoved,
    CartQuantityUpdated,
    CartsMerged,
)
from ordering.domain import ordering


class CartStatus(Enum):
    ACTIVE = "Active"
    CONVERTED = "Converted"
    ABANDONED = "Abandoned"


@ordering.entity(part_of="ShoppingCart")
class CartItem:
    product_id = Identifier(required=True)
    variant_id = Identifier(required=True)
    quantity = Integer(required=True, min_value=1)
    added_at = DateTime()


@ordering.aggregate
class ShoppingCart:
    customer_id = Identifier()  # Nullable for guest carts
    session_id = String(max_length=255)  # For guest cart identification
    items = HasMany(CartItem)
    applied_coupons = Text()  # JSON array of coupon codes
    status = String(choices=CartStatus, default=CartStatus.ACTIVE.value)
    created_at = DateTime()
    updated_at = DateTime()

    @invariant.post
    def cart_must_have_items_to_convert(self):
        if self.status == CartStatus.CONVERTED.value and not self.items:
            raise ValidationError({"cart": ["Cannot convert an empty cart to an order"]})

    # -------------------------------------------------------------------
    # Factory
    # -------------------------------------------------------------------
    @classmethod
    def create(cls, customer_id=None, session_id=None):
        now = datetime.now(UTC)
        return cls(
            customer_id=customer_id,
            session_id=session_id,
            status=CartStatus.ACTIVE.value,
            applied_coupons=json.dumps([]),
            created_at=now,
            updated_at=now,
        )

    # -------------------------------------------------------------------
    # Item management
    # -------------------------------------------------------------------
    def add_item(self, product_id, variant_id, quantity):
        """Add an item to the cart (or increase quantity if already present)."""
        if CartStatus(self.status) != CartStatus.ACTIVE:
            raise ValidationError({"status": ["Items can only be added to an active cart"]})

        # Check if item already exists (same product + variant)
        existing = next(
            (i for i in self.items if str(i.product_id) == str(product_id) and str(i.variant_id) == str(variant_id)),
            None,
        )

        now = datetime.now(UTC)

        if existing:
            existing.quantity += quantity
            item_id = str(existing.id)
        else:
            item = CartItem(
                product_id=product_id,
                variant_id=variant_id,
                quantity=quantity,
                added_at=now,
            )
            self.add_items(item)
            item_id = str(item.id)

        self.updated_at = now

        self.raise_(
            CartItemAdded(
                cart_id=str(self.id),
                item_id=item_id,
                product_id=str(product_id),
                variant_id=str(variant_id),
                quantity=quantity,
            )
        )

    def update_item_quantity(self, item_id, new_quantity):
        """Update the quantity of an existing cart item."""
        if CartStatus(self.status) != CartStatus.ACTIVE:
            raise ValidationError({"status": ["Item quantities can only be updated in an active cart"]})

        item = next((i for i in self.items if str(i.id) == str(item_id)), None)
        if item is None:
            raise ValidationError({"item_id": ["Item not found in cart"]})

        previous_quantity = item.quantity
        item.quantity = new_quantity
        now = datetime.now(UTC)
        self.updated_at = now

        self.raise_(
            CartQuantityUpdated(
                cart_id=str(self.id),
                item_id=str(item_id),
                previous_quantity=previous_quantity,
                new_quantity=new_quantity,
            )
        )

    def remove_item(self, item_id):
        """Remove an item from the cart."""
        if CartStatus(self.status) != CartStatus.ACTIVE:
            raise ValidationError({"status": ["Items can only be removed from an active cart"]})

        item = next((i for i in self.items if str(i.id) == str(item_id)), None)
        if item is None:
            raise ValidationError({"item_id": ["Item not found in cart"]})

        self.remove_items(item)
        now = datetime.now(UTC)
        self.updated_at = now

        self.raise_(
            CartItemRemoved(
                cart_id=str(self.id),
                item_id=str(item_id),
            )
        )

    # -------------------------------------------------------------------
    # Coupon management
    # -------------------------------------------------------------------
    def apply_coupon(self, coupon_code):
        """Apply a coupon code to the cart."""
        if CartStatus(self.status) != CartStatus.ACTIVE:
            raise ValidationError({"status": ["Coupons can only be applied to an active cart"]})

        coupons = json.loads(self.applied_coupons) if self.applied_coupons else []
        if coupon_code in coupons:
            raise ValidationError({"coupon_code": ["Coupon already applied"]})

        coupons.append(coupon_code)
        self.applied_coupons = json.dumps(coupons)
        now = datetime.now(UTC)
        self.updated_at = now

        self.raise_(
            CartCouponApplied(
                cart_id=str(self.id),
                coupon_code=coupon_code,
            )
        )

    # -------------------------------------------------------------------
    # Cart merging (guest → authenticated)
    # -------------------------------------------------------------------
    def merge_guest_cart(self, guest_cart_items):
        """Merge items from a guest cart into this authenticated cart.

        Args:
            guest_cart_items: List of dicts with product_id, variant_id, quantity.
        """
        if CartStatus(self.status) != CartStatus.ACTIVE:
            raise ValidationError({"status": ["Can only merge into an active cart"]})

        items_merged = 0
        now = datetime.now(UTC)

        for guest_item in guest_cart_items:
            existing = next(
                (
                    i
                    for i in self.items
                    if str(i.product_id) == str(guest_item["product_id"])
                    and str(i.variant_id) == str(guest_item["variant_id"])
                ),
                None,
            )
            if existing:
                existing.quantity += guest_item["quantity"]
            else:
                self.add_items(
                    CartItem(
                        product_id=guest_item["product_id"],
                        variant_id=guest_item["variant_id"],
                        quantity=guest_item["quantity"],
                        added_at=now,
                    )
                )
            items_merged += 1

        self.updated_at = now

        self.raise_(
            CartsMerged(
                cart_id=str(self.id),
                source_session_id=guest_item.get("session_id", "") if guest_cart_items else "",
                items_merged_count=items_merged,
            )
        )

    # -------------------------------------------------------------------
    # Cart lifecycle
    # -------------------------------------------------------------------
    def convert_to_order(self):
        """Mark cart as converted to an order."""
        if CartStatus(self.status) != CartStatus.ACTIVE:
            raise ValidationError({"status": ["Only active carts can be converted"]})
        if not self.items:
            raise ValidationError({"cart": ["Cannot convert an empty cart"]})

        # Capture items before marking as converted
        items_snapshot = [
            {
                "product_id": str(item.product_id),
                "variant_id": str(item.variant_id),
                "quantity": item.quantity,
            }
            for item in self.items
        ]

        self.status = CartStatus.CONVERTED.value
        now = datetime.now(UTC)
        self.updated_at = now

        self.raise_(
            CartConverted(
                cart_id=str(self.id),
                customer_id=str(self.customer_id) if self.customer_id else None,
                items=json.dumps(items_snapshot),
            )
        )

    def abandon(self):
        """Mark cart as abandoned."""
        if CartStatus(self.status) != CartStatus.ACTIVE:
            raise ValidationError({"status": ["Only active carts can be abandoned"]})

        self.status = CartStatus.ABANDONED.value
        now = datetime.now(UTC)
        self.updated_at = now

        self.raise_(
            CartAbandoned(
                cart_id=str(self.id),
                abandoned_at=now,
            )
        )
