"""Domain events for the ShoppingCart aggregate."""

from datetime import datetime
from typing import Any

from protean.fields import DateTime, Dict, Identifier, Integer, List, String

from ordering.domain import ordering


@ordering.event(part_of="ShoppingCart")
class CartItemAdded:
    """A product was added to the shopping cart."""

    cart_id: str = Identifier(required=True)
    item_id: str = Identifier(required=True)
    product_id: str = Identifier(required=True)
    variant_id: str = Identifier(required=True)
    quantity: int = Integer(required=True)


@ordering.event(part_of="ShoppingCart")
class CartQuantityUpdated:
    """The quantity of a cart item was changed."""

    cart_id: str = Identifier(required=True)
    item_id: str = Identifier(required=True)
    previous_quantity: int = Integer(required=True)
    new_quantity: int = Integer(required=True)


@ordering.event(part_of="ShoppingCart")
class CartItemRemoved:
    """An item was removed from the shopping cart."""

    cart_id: str = Identifier(required=True)
    item_id: str = Identifier(required=True)


@ordering.event(part_of="ShoppingCart")
class CartCouponApplied:
    """A coupon code was applied to the shopping cart."""

    cart_id: str = Identifier(required=True)
    coupon_code: str = String(required=True)


@ordering.event(part_of="ShoppingCart")
class CartsMerged:
    """A guest cart's items were merged into a registered customer's cart."""

    cart_id: str = Identifier(required=True)
    source_session_id: str | None = String()
    items_merged_count: int = Integer(required=True)


@ordering.event(part_of="ShoppingCart")
class CartConverted:
    """A shopping cart was converted into an order at checkout."""

    cart_id: str = Identifier(required=True)
    customer_id: str | None = Identifier()
    items: list[dict[str, Any]] = List(Dict(), required=True)


@ordering.event(part_of="ShoppingCart", published=True)
class CartAbandoned:
    """A shopping cart was marked as abandoned due to inactivity."""

    cart_id: str = Identifier(required=True)
    abandoned_at: datetime = DateTime(required=True)
