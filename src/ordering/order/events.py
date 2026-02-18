"""Domain events for the Order aggregate.

All events are versioned, immutable facts representing state changes.
Events are persisted to the event store and used for:
- Rebuilding aggregate state via @apply (event sourcing)
- Updating projections via projectors
- Cross-domain communication via Redis Streams
"""

from protean.fields import DateTime, Float, Identifier, String, Text

from ordering.domain import ordering


@ordering.event(part_of="Order")
class OrderCreated:
    """A new order was created from a shopping cart at checkout."""

    __version__ = "v1"

    order_id = Identifier(required=True)
    customer_id = Identifier(required=True)
    items = Text(required=True)  # JSON: list of item dicts
    shipping_address = Text(required=True)  # JSON: address dict
    billing_address = Text(required=True)  # JSON: address dict
    subtotal = Float(required=True)
    shipping_cost = Float()
    tax_total = Float()
    discount_total = Float()
    grand_total = Float(required=True)
    currency = String(default="USD")
    created_at = DateTime(required=True)


@ordering.event(part_of="Order")
class ItemAdded:
    """A new line item was added to an order (only in Created state)."""

    __version__ = "v1"

    order_id = Identifier(required=True)
    item_id = Identifier(required=True)
    product_id = Identifier(required=True)
    variant_id = Identifier(required=True)
    sku = String(required=True)
    title = String(required=True)
    quantity = String(required=True)  # serialized int
    unit_price = String(required=True)  # serialized float
    new_subtotal = Float(required=True)
    new_grand_total = Float(required=True)


@ordering.event(part_of="Order")
class ItemRemoved:
    """A line item was removed from an order (only in Created state)."""

    __version__ = "v1"

    order_id = Identifier(required=True)
    item_id = Identifier(required=True)
    new_subtotal = Float(required=True)
    new_grand_total = Float(required=True)


@ordering.event(part_of="Order")
class ItemQuantityUpdated:
    """The quantity of an order line item was changed."""

    __version__ = "v1"

    order_id = Identifier(required=True)
    item_id = Identifier(required=True)
    previous_quantity = String(required=True)
    new_quantity = String(required=True)
    new_subtotal = Float(required=True)
    new_grand_total = Float(required=True)


@ordering.event(part_of="Order")
class CouponApplied:
    """A coupon code was applied to an order."""

    __version__ = "v1"

    order_id = Identifier(required=True)
    coupon_code = String(required=True)


@ordering.event(part_of="Order")
class OrderConfirmed:
    """The customer confirmed the order, committing to the purchase."""

    __version__ = "v1"

    order_id = Identifier(required=True)
    confirmed_at = DateTime(required=True)


@ordering.event(part_of="Order")
class PaymentPending:
    """Payment processing was initiated for the order."""

    __version__ = "v1"

    order_id = Identifier(required=True)
    payment_id = String(required=True)
    payment_method = String(required=True)


@ordering.event(part_of="Order")
class PaymentSucceeded:
    """Payment was successfully captured for the order."""

    __version__ = "v1"

    order_id = Identifier(required=True)
    payment_id = String(required=True)
    amount = Float(required=True)
    payment_method = String(required=True)


@ordering.event(part_of="Order")
class PaymentFailed:
    """Payment processing failed; the order returns to Confirmed for retry."""

    __version__ = "v1"

    order_id = Identifier(required=True)
    payment_id = String(required=True)
    reason = String(required=True)


@ordering.event(part_of="Order")
class OrderProcessing:
    """The warehouse began picking and packing the order."""

    __version__ = "v1"

    order_id = Identifier(required=True)
    started_at = DateTime(required=True)


@ordering.event(part_of="Order")
class OrderShipped:
    """All order items were shipped with a carrier."""

    __version__ = "v1"

    order_id = Identifier(required=True)
    shipment_id = String(required=True)
    carrier = String(required=True)
    tracking_number = String(required=True)
    shipped_item_ids = Text()  # JSON: list of item IDs
    estimated_delivery = String()  # ISO date string
    shipped_at = DateTime(required=True)


@ordering.event(part_of="Order")
class OrderPartiallyShipped:
    """Some (but not all) order items were shipped."""

    __version__ = "v1"

    order_id = Identifier(required=True)
    shipment_id = String(required=True)
    carrier = String(required=True)
    tracking_number = String(required=True)
    shipped_item_ids = Text()  # JSON: list of item IDs
    shipped_at = DateTime(required=True)


@ordering.event(part_of="Order")
class OrderDelivered:
    """The carrier confirmed delivery of the order to the customer."""

    __version__ = "v1"

    order_id = Identifier(required=True)
    delivered_at = DateTime(required=True)


@ordering.event(part_of="Order")
class OrderCompleted:
    """The order was finalized after delivery and return window expiry."""

    __version__ = "v1"

    order_id = Identifier(required=True)
    completed_at = DateTime(required=True)


@ordering.event(part_of="Order")
class ReturnRequested:
    """The customer requested a return of a delivered order."""

    __version__ = "v1"

    order_id = Identifier(required=True)
    reason = String(required=True)
    requested_at = DateTime(required=True)


@ordering.event(part_of="Order")
class ReturnApproved:
    """A return request was approved by the system or an admin."""

    __version__ = "v1"

    order_id = Identifier(required=True)
    approved_at = DateTime(required=True)


@ordering.event(part_of="Order")
class OrderReturned:
    """Returned items were received back from the customer."""

    __version__ = "v1"

    order_id = Identifier(required=True)
    returned_item_ids = Text()  # JSON: list of item IDs
    returned_at = DateTime(required=True)


@ordering.event(part_of="Order")
class OrderCancelled:
    """The order was cancelled before fulfillment began."""

    __version__ = "v1"

    order_id = Identifier(required=True)
    reason = String(required=True)
    cancelled_by = String(required=True)
    cancelled_at = DateTime(required=True)


@ordering.event(part_of="Order")
class OrderRefunded:
    """A refund was issued for a cancelled or returned order."""

    __version__ = "v1"

    order_id = Identifier(required=True)
    refund_amount = Float(required=True)
    refunded_at = DateTime(required=True)
