"""Cart view — current cart state for UI rendering."""

import json

from protean.core.projector import on
from protean.fields import DateTime, Identifier, Integer, String, Text
from protean.utils.globals import current_domain

from ordering.cart.cart import ShoppingCart
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


@ordering.projection
class CartView:
    cart_id = Identifier(identifier=True, required=True)
    customer_id = Identifier()
    session_id = String()
    items = Text()  # JSON: list of {product_id, variant_id, quantity}
    applied_coupons = Text()  # JSON: list of coupon codes
    status = String(required=True)
    item_count = Integer(default=0)
    created_at = DateTime()
    updated_at = DateTime()


@ordering.projector(projector_for=CartView, aggregates=[ShoppingCart])
class CartViewProjector:
    @on(CartItemAdded)
    def on_item_added(self, event):
        repo = current_domain.repository_for(CartView)
        try:
            view = repo.get(event.cart_id)
        except Exception:
            # Cart view doesn't exist yet — create it
            view = CartView(
                cart_id=event.cart_id,
                status="Active",
                items="[]",
                applied_coupons="[]",
                item_count=0,
            )

        items = json.loads(view.items) if view.items else []

        # Check if item already exists
        existing = next(
            (
                i
                for i in items
                if i.get("product_id") == str(event.product_id) and i.get("variant_id") == str(event.variant_id)
            ),
            None,
        )
        if existing:
            existing["quantity"] = existing.get("quantity", 0) + event.quantity
        else:
            items.append(
                {
                    "item_id": str(event.item_id),
                    "product_id": str(event.product_id),
                    "variant_id": str(event.variant_id),
                    "quantity": event.quantity,
                }
            )

        view.items = json.dumps(items)
        view.item_count = len(items)
        repo.add(view)

    @on(CartQuantityUpdated)
    def on_quantity_updated(self, event):
        repo = current_domain.repository_for(CartView)
        view = repo.get(event.cart_id)
        items = json.loads(view.items) if view.items else []
        for item in items:
            if item.get("item_id") == str(event.item_id):
                item["quantity"] = event.new_quantity
                break
        view.items = json.dumps(items)
        repo.add(view)

    @on(CartItemRemoved)
    def on_item_removed(self, event):
        repo = current_domain.repository_for(CartView)
        view = repo.get(event.cart_id)
        items = json.loads(view.items) if view.items else []
        items = [i for i in items if i.get("item_id") != str(event.item_id)]
        view.items = json.dumps(items)
        view.item_count = len(items)
        repo.add(view)

    @on(CartCouponApplied)
    def on_coupon_applied(self, event):
        repo = current_domain.repository_for(CartView)
        view = self._get_or_create_view(repo, event.cart_id)
        coupons = json.loads(view.applied_coupons) if view.applied_coupons else []
        coupons.append(event.coupon_code)
        view.applied_coupons = json.dumps(coupons)
        repo.add(view)

    @on(CartsMerged)
    def on_carts_merged(self, event):
        repo = current_domain.repository_for(CartView)
        view = self._get_or_create_view(repo, event.cart_id)
        view.item_count = (view.item_count or 0) + event.items_merged_count
        repo.add(view)

    @on(CartConverted)
    def on_cart_converted(self, event):
        repo = current_domain.repository_for(CartView)
        view = self._get_or_create_view(repo, event.cart_id)
        view.status = "Converted"
        repo.add(view)

    @on(CartAbandoned)
    def on_cart_abandoned(self, event):
        repo = current_domain.repository_for(CartView)
        view = self._get_or_create_view(repo, event.cart_id)
        view.status = "Abandoned"
        view.updated_at = event.abandoned_at
        repo.add(view)

    @staticmethod
    def _get_or_create_view(repo, cart_id):
        try:
            return repo.get(cart_id)
        except Exception:
            return CartView(
                cart_id=cart_id,
                status="Active",
                items="[]",
                applied_coupons="[]",
                item_count=0,
            )
