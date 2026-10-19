"""Domain events for the Order aggregate.

All events are versioned, immutable facts representing state changes.
Events are persisted to the event store and used for:
- Rebuilding aggregate state via @apply (event sourcing)
- Updating projections via projectors
- Cross-domain communication via Redis Streams
"""

from datetime import datetime
from typing import Any

from protean.fields import DateTime, Dict, Float, Identifier, List, String

from ordering.domain import ordering


@ordering.event(part_of="Order", published=True)
class OrderCreated:
    """A new order was created from a shopping cart at checkout.

    v2: Added order_source to track originating channel (web, mobile, api).
    """

    __version__ = 2

    order_id: str = Identifier(required=True)
    customer_id: str = Identifier(required=True)
    items: list[dict[str, Any]] = List(Dict(), required=True)
    shipping_address: dict[str, Any] = Dict(required=True)
    billing_address: dict[str, Any] = Dict(required=True)
    subtotal: float = Float(required=True)
    shipping_cost: float | None = Float()
    tax_total: float | None = Float()
    discount_total: float | None = Float()
    grand_total: float = Float(required=True)
    currency: str = String(default="USD")
    order_source: str = String(default="web")
    created_at: datetime = DateTime(required=True)


@ordering.event(part_of="Order")
class ItemAdded:
    """A new line item was added to an order (only in Created state)."""

    order_id: str = Identifier(required=True)
    item_id: str = Identifier(required=True)
    product_id: str = Identifier(required=True)
    variant_id: str = Identifier(required=True)
    sku: str = String(required=True)
    title: str = String(required=True)
    quantity: str = String(required=True)  # serialized int
    unit_price: str = String(required=True)  # serialized float
    new_subtotal: float = Float(required=True)
    new_grand_total: float = Float(required=True)
    added_at: datetime = DateTime(required=True)


@ordering.event(part_of="Order")
class ItemRemoved:
    """A line item was removed from an order (only in Created state)."""

    order_id: str = Identifier(required=True)
    item_id: str = Identifier(required=True)
    new_subtotal: float = Float(required=True)
    new_grand_total: float = Float(required=True)
    removed_at: datetime = DateTime(required=True)


@ordering.event(part_of="Order")
class ItemQuantityUpdated:
    """The quantity of an order line item was changed."""

    order_id: str = Identifier(required=True)
    item_id: str = Identifier(required=True)
    previous_quantity: str = String(required=True)
    new_quantity: str = String(required=True)
    new_subtotal: float = Float(required=True)
    new_grand_total: float = Float(required=True)
    updated_at: datetime = DateTime(required=True)


@ordering.event(part_of="Order")
class CouponApplied:
    """A coupon code was applied to an order."""

    order_id: str = Identifier(required=True)
    coupon_code: str = String(required=True)
    applied_at: datetime = DateTime(required=True)


@ordering.event(part_of="Order", published=True)
class OrderConfirmed:
    """The customer confirmed the order, committing to the purchase."""

    order_id: str = Identifier(required=True)
    confirmed_at: datetime = DateTime(required=True)


@ordering.event(part_of="Order")
class PaymentPending:
    """Payment processing was initiated for the order."""

    order_id: str = Identifier(required=True)
    payment_id: str = String(required=True)
    payment_method: str = String(required=True)
    initiated_at: datetime = DateTime(required=True)


@ordering.event(part_of="Order")
class PaymentSucceeded:
    """Payment was successfully captured for the order."""

    order_id: str = Identifier(required=True)
    payment_id: str = String(required=True)
    amount: float = Float(required=True)
    payment_method: str = String(required=True)
    paid_at: datetime = DateTime(required=True)


@ordering.event(part_of="Order")
class PaymentFailed:
    """Payment processing failed; the order returns to Confirmed for retry."""

    order_id: str = Identifier(required=True)
    payment_id: str = String(required=True)
    reason: str = String(required=True)
    failed_at: datetime = DateTime(required=True)


@ordering.event(part_of="Order")
class OrderProcessing:
    """The warehouse began picking and packing the order."""

    order_id: str = Identifier(required=True)
    started_at: datetime = DateTime(required=True)


@ordering.event(part_of="Order")
class OrderShipped:
    """All order items were shipped with a carrier."""

    order_id: str = Identifier(required=True)
    shipment_id: str = String(required=True)
    carrier: str = String(required=True)
    tracking_number: str = String(required=True)
    shipped_item_ids: list[str] = List(String())
    estimated_delivery: str | None = String()  # ISO date string
    shipped_at: datetime = DateTime(required=True)


@ordering.event(part_of="Order")
class OrderPartiallyShipped:
    """Some (but not all) order items were shipped."""

    order_id: str = Identifier(required=True)
    shipment_id: str = String(required=True)
    carrier: str = String(required=True)
    tracking_number: str = String(required=True)
    shipped_item_ids: list[str] = List(String())
    shipped_at: datetime = DateTime(required=True)


@ordering.event(part_of="Order", published=True)
class OrderDelivered:
    """The carrier confirmed delivery of the order to the customer."""

    order_id: str = Identifier(required=True)
    customer_id: str = Identifier(required=True)
    delivered_at: datetime = DateTime(required=True)


@ordering.event(part_of="Order")
class OrderCompleted:
    """The order was finalized after delivery and return window expiry."""

    order_id: str = Identifier(required=True)
    completed_at: datetime = DateTime(required=True)


@ordering.event(part_of="Order")
class ReturnRequested:
    """The customer requested a return of a delivered order."""

    order_id: str = Identifier(required=True)
    reason: str = String(required=True)
    requested_at: datetime = DateTime(required=True)


@ordering.event(part_of="Order")
class ReturnApproved:
    """A return request was approved by the system or an admin."""

    order_id: str = Identifier(required=True)
    approved_at: datetime = DateTime(required=True)


@ordering.event(part_of="Order", published=True)
class OrderReturned:
    """Returned items were received back from the customer."""

    order_id: str = Identifier(required=True)
    returned_item_ids: list[str] = List(String())
    returned_at: datetime = DateTime(required=True)


@ordering.event(part_of="Order", published=True)
class OrderCancelled:
    """The order was cancelled before fulfillment began."""

    order_id: str = Identifier(required=True)
    reason: str = String(required=True)
    cancelled_by: str = String(required=True)
    cancelled_at: datetime = DateTime(required=True)


@ordering.event(part_of="Order")
class OrderRefunded:
    """A refund was issued for a cancelled or returned order."""

    order_id: str = Identifier(required=True)
    refund_amount: float = Float(required=True)
    refunded_at: datetime = DateTime(required=True)
