"""Order summary — lightweight listing/history view."""

import json

from protean.core.projector import on
from protean.fields import DateTime, Float, Identifier, Integer, String
from protean.utils.globals import current_domain

from ordering.domain import ordering
from ordering.order.events import (
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
class OrderSummary:
    order_id = Identifier(identifier=True, required=True)
    customer_id = Identifier(required=True)
    status = String(required=True)
    item_count = Integer(default=0)
    grand_total = Float()
    currency = String(default="USD")
    created_at = DateTime()
    updated_at = DateTime()


@ordering.projector(projector_for=OrderSummary, aggregates=[Order])
class OrderSummaryProjector:
    @on(OrderCreated)
    def on_order_created(self, event):
        items = json.loads(event.items) if isinstance(event.items, str) else []
        current_domain.repository_for(OrderSummary).add(
            OrderSummary(
                order_id=event.order_id,
                customer_id=event.customer_id,
                status="Created",
                item_count=len(items),
                grand_total=event.grand_total,
                currency=event.currency or "USD",
                created_at=event.created_at,
                updated_at=event.created_at,
            )
        )

    @on(ItemAdded)
    def on_item_added(self, event):
        repo = current_domain.repository_for(OrderSummary)
        summary = repo.get(event.order_id)
        summary.item_count = (summary.item_count or 0) + 1
        summary.grand_total = event.new_grand_total
        repo.add(summary)

    @on(ItemRemoved)
    def on_item_removed(self, event):
        repo = current_domain.repository_for(OrderSummary)
        summary = repo.get(event.order_id)
        summary.item_count = max((summary.item_count or 1) - 1, 0)
        summary.grand_total = event.new_grand_total
        repo.add(summary)

    @on(ItemQuantityUpdated)
    def on_item_quantity_updated(self, event):
        repo = current_domain.repository_for(OrderSummary)
        summary = repo.get(event.order_id)
        summary.grand_total = event.new_grand_total
        repo.add(summary)

    def _update_status(self, order_id, status, updated_at=None):
        repo = current_domain.repository_for(OrderSummary)
        summary = repo.get(order_id)
        summary.status = status
        if updated_at:
            summary.updated_at = updated_at
        repo.add(summary)

    @on(OrderConfirmed)
    def on_order_confirmed(self, event):
        self._update_status(event.order_id, "Confirmed", event.confirmed_at)

    @on(PaymentPending)
    def on_payment_pending(self, event):
        self._update_status(event.order_id, "Payment_Pending")

    @on(PaymentSucceeded)
    def on_payment_succeeded(self, event):
        self._update_status(event.order_id, "Paid")

    @on(PaymentFailed)
    def on_payment_failed(self, event):
        self._update_status(event.order_id, "Confirmed")

    @on(OrderProcessing)
    def on_order_processing(self, event):
        self._update_status(event.order_id, "Processing", event.started_at)

    @on(OrderShipped)
    def on_order_shipped(self, event):
        self._update_status(event.order_id, "Shipped", event.shipped_at)

    @on(OrderPartiallyShipped)
    def on_order_partially_shipped(self, event):
        self._update_status(event.order_id, "Partially_Shipped", event.shipped_at)

    @on(OrderDelivered)
    def on_order_delivered(self, event):
        self._update_status(event.order_id, "Delivered", event.delivered_at)

    @on(OrderCompleted)
    def on_order_completed(self, event):
        self._update_status(event.order_id, "Completed", event.completed_at)

    @on(ReturnRequested)
    def on_return_requested(self, event):
        self._update_status(event.order_id, "Return_Requested", event.requested_at)

    @on(ReturnApproved)
    def on_return_approved(self, event):
        self._update_status(event.order_id, "Return_Approved", event.approved_at)

    @on(OrderReturned)
    def on_order_returned(self, event):
        self._update_status(event.order_id, "Returned", event.returned_at)

    @on(OrderCancelled)
    def on_order_cancelled(self, event):
        self._update_status(event.order_id, "Cancelled", event.cancelled_at)

    @on(OrderRefunded)
    def on_order_refunded(self, event):
        self._update_status(event.order_id, "Refunded", event.refunded_at)
