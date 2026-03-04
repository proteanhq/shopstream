"""Domain events for the ShoppingCart aggregate."""

from protean.fields import DateTime, Dict, Identifier, Integer, List, String

from ordering.domain import ordering


@ordering.event(part_of="ShoppingCart")
class CartItemAdded:
    """A product was added to the shopping cart."""

    __version__ = "v1"

    cart_id = Identifier(required=True)
    item_id = Identifier(required=True)
    product_id = Identifier(required=True)
    variant_id = Identifier(required=True)
    quantity = Integer(required=True)


@ordering.event(part_of="ShoppingCart")
class CartQuantityUpdated:
    """The quantity of a cart item was changed."""

    __version__ = "v1"

    cart_id = Identifier(required=True)
    item_id = Identifier(required=True)
    previous_quantity = Integer(required=True)
    new_quantity = Integer(required=True)


@ordering.event(part_of="ShoppingCart")
class CartItemRemoved:
    """An item was removed from the shopping cart."""

    __version__ = "v1"

    cart_id = Identifier(required=True)
    item_id = Identifier(required=True)


@ordering.event(part_of="ShoppingCart")
class CartCouponApplied:
    """A coupon code was applied to the shopping cart."""

    __version__ = "v1"

    cart_id = Identifier(required=True)
    coupon_code = String(required=True)


@ordering.event(part_of="ShoppingCart")
class CartsMerged:
    """A guest cart's items were merged into a registered customer's cart."""

    __version__ = "v1"

    cart_id = Identifier(required=True)
    source_session_id = String()
    items_merged_count = Integer(required=True)


@ordering.event(part_of="ShoppingCart")
class CartConverted:
    """A shopping cart was converted into an order at checkout."""

    __version__ = "v1"

    cart_id = Identifier(required=True)
    customer_id = Identifier()
    items = List(Dict(), required=True)


@ordering.event(part_of="ShoppingCart", published=True)
class CartAbandoned:
    """A shopping cart was marked as abandoned due to inactivity."""

    __version__ = "v1"

    cart_id = Identifier(required=True)
    abandoned_at = DateTime(required=True)
