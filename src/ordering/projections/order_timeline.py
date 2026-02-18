"""Order timeline — append-only audit trail of all order events."""

import uuid
from datetime import UTC, datetime

from protean.core.projector import on
from protean.fields import DateTime, Identifier, String, Text
from protean.utils.globals import current_domain

from ordering.domain import ordering
from ordering.order.events import (
    CouponApplied,
    ItemAdded,
    ItemQuantityUpdated,
    ItemRemoved,
    OrderCancelled,
    OrderCompleted,
    OrderConfirmed,
    OrderCreated,
    OrderDelivered,
    OrderPartiallyShipped,
    OrderProcessing,
    OrderRefunded,
    OrderReturned,
    OrderShipped,
    PaymentFailed,
    PaymentPending,
    PaymentSucceeded,
    ReturnApproved,
    ReturnRequested,
)
from ordering.order.order import Order


@ordering.projection
class OrderTimeline:
    entry_id = Identifier(identifier=True, required=True)
    order_id = Identifier(required=True)
    event_type = String(required=True)
    description = String(required=True)
    occurred_at = DateTime(required=True)
    event_metadata = Text()  # JSON: extra event data


def _add_entry(order_id, event_type, description, occurred_at, event_metadata=None):
    current_domain.repository_for(OrderTimeline).add(
        OrderTimeline(
            entry_id=str(uuid.uuid4()),
            order_id=order_id,
            event_type=event_type,
            description=description,
            occurred_at=occurred_at,
            event_metadata=event_metadata,
        )
    )


@ordering.projector(projector_for=OrderTimeline, aggregates=[Order])
class OrderTimelineProjector:
    @on(OrderCreated)
    def on_order_created(self, event):
        _add_entry(event.order_id, "OrderCreated", "Order was created", event.created_at)

    @on(ItemAdded)
    def on_item_added(self, event):
        _add_entry(event.order_id, "ItemAdded", f"Item {event.title} added (qty: {event.quantity})", datetime.now(UTC))

    @on(ItemRemoved)
    def on_item_removed(self, event):
        _add_entry(event.order_id, "ItemRemoved", f"Item {event.item_id} removed", datetime.now(UTC))

    @on(ItemQuantityUpdated)
    def on_item_quantity_updated(self, event):
        _add_entry(
            event.order_id,
            "ItemQuantityUpdated",
            f"Item quantity changed from {event.previous_quantity} to {event.new_quantity}",
            datetime.now(UTC),
        )

    @on(CouponApplied)
    def on_coupon_applied(self, event):
        _add_entry(event.order_id, "CouponApplied", f"Coupon '{event.coupon_code}' applied", datetime.now(UTC))

    @on(OrderConfirmed)
    def on_order_confirmed(self, event):
        _add_entry(event.order_id, "OrderConfirmed", "Order was confirmed", event.confirmed_at)

    @on(PaymentPending)
    def on_payment_pending(self, event):
        _add_entry(event.order_id, "PaymentPending", f"Payment initiated via {event.payment_method}", datetime.now(UTC))

    @on(PaymentSucceeded)
    def on_payment_succeeded(self, event):
        _add_entry(event.order_id, "PaymentSucceeded", f"Payment of {event.amount} succeeded", datetime.now(UTC))

    @on(PaymentFailed)
    def on_payment_failed(self, event):
        _add_entry(event.order_id, "PaymentFailed", f"Payment failed: {event.reason}", datetime.now(UTC))

    @on(OrderProcessing)
    def on_order_processing(self, event):
        _add_entry(event.order_id, "OrderProcessing", "Order processing started", event.started_at)

    @on(OrderShipped)
    def on_order_shipped(self, event):
        _add_entry(
            event.order_id,
            "OrderShipped",
            f"Shipped via {event.carrier} (tracking: {event.tracking_number})",
            event.shipped_at,
        )

    @on(OrderPartiallyShipped)
    def on_order_partially_shipped(self, event):
        _add_entry(event.order_id, "OrderPartiallyShipped", f"Partial shipment via {event.carrier}", event.shipped_at)

    @on(OrderDelivered)
    def on_order_delivered(self, event):
        _add_entry(event.order_id, "OrderDelivered", "Order was delivered", event.delivered_at)

    @on(OrderCompleted)
    def on_order_completed(self, event):
        _add_entry(event.order_id, "OrderCompleted", "Order completed", event.completed_at)

    @on(ReturnRequested)
    def on_return_requested(self, event):
        _add_entry(event.order_id, "ReturnRequested", f"Return requested: {event.reason}", event.requested_at)

    @on(ReturnApproved)
    def on_return_approved(self, event):
        _add_entry(event.order_id, "ReturnApproved", "Return approved", event.approved_at)

    @on(OrderReturned)
    def on_order_returned(self, event):
        _add_entry(event.order_id, "OrderReturned", "Items returned and received", event.returned_at)

    @on(OrderCancelled)
    def on_order_cancelled(self, event):
        _add_entry(
            event.order_id, "OrderCancelled", f"Cancelled by {event.cancelled_by}: {event.reason}", event.cancelled_at
        )

    @on(OrderRefunded)
    def on_order_refunded(self, event):
        _add_entry(event.order_id, "OrderRefunded", f"Refunded {event.refund_amount}", event.refunded_at)
