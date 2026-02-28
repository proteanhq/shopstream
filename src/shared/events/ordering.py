"""Cross-domain event contracts for Ordering domain events.

These classes define the event shape for consumption by other domains
(e.g., the Fulfillment domain to cancel in-progress fulfillments when
an order is cancelled, or the Notifications domain to send confirmations).
They are registered as external events via domain.register_external_event()
with matching __type__ strings so Protean's stream deserialization works
correctly.

The source-of-truth events are in src/ordering/order/events.py and
src/ordering/cart/events.py.
"""

from protean.core.event import BaseEvent
from protean.fields import DateTime, Dict, Float, Identifier, List, String


class OrderCreated(BaseEvent):
    """A new order was created from a shopping cart at checkout.

    Consumed by the Notifications domain to send order confirmation emails.
    """

    __version__ = "v1"

    order_id = Identifier(required=True)
    customer_id = Identifier(required=True)
    items = List(Dict(), required=True)
    grand_total = Float(required=True)
    currency = String(default="USD")
    created_at = DateTime(required=True)


class OrderPaid(BaseEvent):
    """Payment was recorded successfully on the order."""

    __version__ = "v1"

    order_id = Identifier(required=True)
    customer_id = Identifier(required=True)
    items = List(Dict(), required=True)
    shipping_address = Dict()
    grand_total = Float(required=True)
    currency = String(default="USD")
    paid_at = DateTime(required=True)


class OrderCancelled(BaseEvent):
    """An order was cancelled."""

    __version__ = "v1"

    order_id = Identifier(required=True)
    reason = String(required=True)
    cancelled_by = String(required=True)
    cancelled_at = DateTime(required=True)


class OrderDelivered(BaseEvent):
    """An order was delivered to the customer.

    Consumed by the Reviews domain to track verified purchases.
    Note: The source event (Ordering.OrderDelivered.v1) only carries
    order_id and delivered_at. This shared contract adds customer_id
    and items for downstream consumers that need them.
    """

    __version__ = "v1"

    order_id = Identifier(required=True)
    customer_id = Identifier()
    items = List(Dict())
    delivered_at = DateTime(required=True)


class OrderReturned(BaseEvent):
    """Returned items were received back from the customer.

    Consumed by the Inventory domain to restock items and the Payments
    domain to initiate a refund.
    """

    __version__ = "v1"

    order_id = Identifier(required=True)
    customer_id = Identifier()
    returned_item_ids = List(String())
    items = List(Dict())
    grand_total = Float()
    returned_at = DateTime(required=True)


class ItemAdded(BaseEvent):
    """A new line item was added to an order."""

    __version__ = "v1"

    order_id = Identifier(required=True)
    item_id = Identifier(required=True)
    product_id = Identifier(required=True)
    variant_id = Identifier(required=True)
    sku = String(required=True)
    title = String(required=True)
    quantity = String(required=True)
    unit_price = String(required=True)
    new_subtotal = Float(required=True)
    new_grand_total = Float(required=True)
    added_at = DateTime(required=True)


class ItemRemoved(BaseEvent):
    """A line item was removed from an order."""

    __version__ = "v1"

    order_id = Identifier(required=True)
    item_id = Identifier(required=True)
    new_subtotal = Float(required=True)
    new_grand_total = Float(required=True)
    removed_at = DateTime(required=True)


class ItemQuantityUpdated(BaseEvent):
    """The quantity of an order line item was changed."""

    __version__ = "v1"

    order_id = Identifier(required=True)
    item_id = Identifier(required=True)
    previous_quantity = String(required=True)
    new_quantity = String(required=True)
    new_subtotal = Float(required=True)
    new_grand_total = Float(required=True)
    updated_at = DateTime(required=True)


class CouponApplied(BaseEvent):
    """A coupon code was applied to an order."""

    __version__ = "v1"

    order_id = Identifier(required=True)
    coupon_code = String(required=True)
    applied_at = DateTime(required=True)


class OrderConfirmed(BaseEvent):
    """The customer confirmed the order."""

    __version__ = "v1"

    order_id = Identifier(required=True)
    confirmed_at = DateTime(required=True)


class PaymentPending(BaseEvent):
    """Payment processing was initiated for the order."""

    __version__ = "v1"

    order_id = Identifier(required=True)
    payment_id = String(required=True)
    payment_method = String(required=True)
    initiated_at = DateTime(required=True)


class PaymentSucceeded(BaseEvent):
    """Payment was successfully captured for the order."""

    __version__ = "v1"

    order_id = Identifier(required=True)
    payment_id = String(required=True)
    amount = Float(required=True)
    payment_method = String(required=True)
    paid_at = DateTime(required=True)


class PaymentFailed(BaseEvent):
    """Payment processing failed."""

    __version__ = "v1"

    order_id = Identifier(required=True)
    payment_id = String(required=True)
    reason = String(required=True)
    failed_at = DateTime(required=True)


class OrderProcessing(BaseEvent):
    """The warehouse began picking and packing the order."""

    __version__ = "v1"

    order_id = Identifier(required=True)
    started_at = DateTime(required=True)


class OrderShipped(BaseEvent):
    """All order items were shipped with a carrier."""

    __version__ = "v1"

    order_id = Identifier(required=True)
    shipment_id = String(required=True)
    carrier = String(required=True)
    tracking_number = String(required=True)
    shipped_item_ids = List(String())
    estimated_delivery = String()
    shipped_at = DateTime(required=True)


class OrderPartiallyShipped(BaseEvent):
    """Some (but not all) order items were shipped."""

    __version__ = "v1"

    order_id = Identifier(required=True)
    shipment_id = String(required=True)
    carrier = String(required=True)
    tracking_number = String(required=True)
    shipped_item_ids = List(String())
    shipped_at = DateTime(required=True)


class OrderCompleted(BaseEvent):
    """The order was finalized after delivery and return window expiry."""

    __version__ = "v1"

    order_id = Identifier(required=True)
    completed_at = DateTime(required=True)


class ReturnRequested(BaseEvent):
    """The customer requested a return of a delivered order."""

    __version__ = "v1"

    order_id = Identifier(required=True)
    reason = String(required=True)
    requested_at = DateTime(required=True)


class ReturnApproved(BaseEvent):
    """A return request was approved."""

    __version__ = "v1"

    order_id = Identifier(required=True)
    approved_at = DateTime(required=True)


class OrderRefunded(BaseEvent):
    """A refund was issued for a cancelled or returned order."""

    __version__ = "v1"

    order_id = Identifier(required=True)
    refund_amount = Float(required=True)
    refunded_at = DateTime(required=True)


class CartAbandoned(BaseEvent):
    """A shopping cart was marked as abandoned due to inactivity.

    Consumed by the Notifications domain to send cart recovery emails
    (scheduled 24 hours after abandonment).
    """

    __version__ = "v1"

    cart_id = Identifier(required=True)
    customer_id = Identifier()
    items = List(Dict())
    abandoned_at = DateTime(required=True)


class CartItemAdded(BaseEvent):
    """An item was added to a shopping cart."""

    __version__ = "v1"

    cart_id = Identifier(required=True)
    item_id = Identifier(required=True)
    product_id = Identifier(required=True)
    variant_id = Identifier(required=True)
    quantity = String(required=True)
    added_at = DateTime(required=True)


class CartQuantityUpdated(BaseEvent):
    """The quantity of a cart item was changed."""

    __version__ = "v1"

    cart_id = Identifier(required=True)
    item_id = Identifier(required=True)
    previous_quantity = String(required=True)
    new_quantity = String(required=True)
    updated_at = DateTime(required=True)


class CartItemRemoved(BaseEvent):
    """An item was removed from a shopping cart."""

    __version__ = "v1"

    cart_id = Identifier(required=True)
    item_id = Identifier(required=True)
    removed_at = DateTime(required=True)


class CartCouponApplied(BaseEvent):
    """A coupon was applied to a shopping cart."""

    __version__ = "v1"

    cart_id = Identifier(required=True)
    coupon_code = String(required=True)
    applied_at = DateTime(required=True)


class CartsMerged(BaseEvent):
    """Two shopping carts were merged."""

    __version__ = "v1"

    cart_id = Identifier(required=True)
    source_cart_id = Identifier(required=True)
    merged_at = DateTime(required=True)


class CartConverted(BaseEvent):
    """A shopping cart was converted to an order."""

    __version__ = "v1"

    cart_id = Identifier(required=True)
    order_id = Identifier(required=True)
    converted_at = DateTime(required=True)
