"""Domain events for the ShoppingCart aggregate."""

from protean.fields import DateTime, Identifier, Integer, String, Text

from ordering.domain import ordering


@ordering.event(part_of="ShoppingCart")
class CartItemAdded:
    __version__ = "v1"

    cart_id = Identifier(required=True)
    item_id = Identifier(required=True)
    product_id = Identifier(required=True)
    variant_id = Identifier(required=True)
    quantity = Integer(required=True)


@ordering.event(part_of="ShoppingCart")
class CartQuantityUpdated:
    __version__ = "v1"

    cart_id = Identifier(required=True)
    item_id = Identifier(required=True)
    previous_quantity = Integer(required=True)
    new_quantity = Integer(required=True)


@ordering.event(part_of="ShoppingCart")
class CartItemRemoved:
    __version__ = "v1"

    cart_id = Identifier(required=True)
    item_id = Identifier(required=True)


@ordering.event(part_of="ShoppingCart")
class CartCouponApplied:
    __version__ = "v1"

    cart_id = Identifier(required=True)
    coupon_code = String(required=True)


@ordering.event(part_of="ShoppingCart")
class CartsMerged:
    __version__ = "v1"

    cart_id = Identifier(required=True)
    source_session_id = String()
    items_merged_count = Integer(required=True)


@ordering.event(part_of="ShoppingCart")
class CartConverted:
    __version__ = "v1"

    cart_id = Identifier(required=True)
    customer_id = Identifier()
    items = Text(required=True)  # JSON: list of {product_id, variant_id, quantity}


@ordering.event(part_of="ShoppingCart")
class CartAbandoned:
    __version__ = "v1"

    cart_id = Identifier(required=True)
    abandoned_at = DateTime(required=True)
