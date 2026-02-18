"""Orders by status — admin dashboard view for filtering orders by status."""

from protean.core.projector import on
from protean.fields import DateTime, Float, Identifier, String
from protean.utils.globals import current_domain

from ordering.domain import ordering
from ordering.order.events import (
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
class OrdersByStatus:
    order_id = Identifier(identifier=True, required=True)
    customer_id = Identifier(required=True)
    status = String(required=True)
    grand_total = Float()
    created_at = DateTime()
    updated_at = DateTime()


@ordering.projector(projector_for=OrdersByStatus, aggregates=[Order])
class OrdersByStatusProjector:
    @on(OrderCreated)
    def on_order_created(self, event):
        current_domain.repository_for(OrdersByStatus).add(
            OrdersByStatus(
                order_id=event.order_id,
                customer_id=event.customer_id,
                status="Created",
                grand_total=event.grand_total,
                created_at=event.created_at,
                updated_at=event.created_at,
            )
        )

    def _update_status(self, order_id, status, updated_at=None):
        repo = current_domain.repository_for(OrdersByStatus)
        record = repo.get(order_id)
        record.status = status
        if updated_at:
            record.updated_at = updated_at
        repo.add(record)

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
