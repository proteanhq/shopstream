"""Customer orders — per-customer order listing projection."""

from datetime import datetime
from decimal import Decimal as D

from protean import Index
from protean.core.projector import on
from protean.fields import DateTime, Decimal, Identifier, Integer, String
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


# Read path: list a customer's orders (filter by customer_id).
@ordering.projection(indexes=[Index("customer_id")])
class CustomerOrders:
    order_id: str = Identifier(identifier=True, required=True)
    customer_id: str = Identifier(required=True)
    status: str = String(required=True)
    grand_total: D | None = Decimal(precision=19, scale=4)
    currency: str = String(default="USD")
    item_count: int = Integer(default=0)
    created_at: datetime | None = DateTime()
    updated_at: datetime | None = DateTime()


@ordering.projector(projector_for=CustomerOrders, aggregates=[Order])
class CustomerOrdersProjector:
    @on(OrderCreated)
    def on_order_created(self, event: OrderCreated) -> None:
        items = event.items or []
        current_domain.repository_for(CustomerOrders).add(
            CustomerOrders(
                order_id=event.order_id,
                customer_id=event.customer_id,
                status="Created",
                grand_total=event.grand_total,
                currency=event.currency or "USD",
                item_count=len(items),
                created_at=event.created_at,
                updated_at=event.created_at,
            )
        )

    def _update_status(self, order_id: str, status: str, updated_at: datetime | None = None) -> None:
        repo = current_domain.repository_for(CustomerOrders)
        record = repo.get(order_id)
        record.status = status
        if updated_at:
            record.updated_at = updated_at
        repo.add(record)

    @on(OrderConfirmed)
    def on_order_confirmed(self, event: OrderConfirmed) -> None:
        self._update_status(event.order_id, "Confirmed", event.confirmed_at)

    @on(PaymentPending)
    def on_payment_pending(self, event: PaymentPending) -> None:
        self._update_status(event.order_id, "Payment_Pending")

    @on(PaymentSucceeded)
    def on_payment_succeeded(self, event: PaymentSucceeded) -> None:
        self._update_status(event.order_id, "Paid")

    @on(PaymentFailed)
    def on_payment_failed(self, event: PaymentFailed) -> None:
        self._update_status(event.order_id, "Confirmed")

    @on(OrderProcessing)
    def on_order_processing(self, event: OrderProcessing) -> None:
        self._update_status(event.order_id, "Processing", event.started_at)

    @on(OrderShipped)
    def on_order_shipped(self, event: OrderShipped) -> None:
        self._update_status(event.order_id, "Shipped", event.shipped_at)

    @on(OrderPartiallyShipped)
    def on_order_partially_shipped(self, event: OrderPartiallyShipped) -> None:
        self._update_status(event.order_id, "Partially_Shipped", event.shipped_at)

    @on(OrderDelivered)
    def on_order_delivered(self, event: OrderDelivered) -> None:
        self._update_status(event.order_id, "Delivered", event.delivered_at)

    @on(OrderCompleted)
    def on_order_completed(self, event: OrderCompleted) -> None:
        self._update_status(event.order_id, "Completed", event.completed_at)

    @on(ReturnRequested)
    def on_return_requested(self, event: ReturnRequested) -> None:
        self._update_status(event.order_id, "Return_Requested", event.requested_at)

    @on(ReturnApproved)
    def on_return_approved(self, event: ReturnApproved) -> None:
        self._update_status(event.order_id, "Return_Approved", event.approved_at)

    @on(OrderReturned)
    def on_order_returned(self, event: OrderReturned) -> None:
        self._update_status(event.order_id, "Returned", event.returned_at)

    @on(OrderCancelled)
    def on_order_cancelled(self, event: OrderCancelled) -> None:
        self._update_status(event.order_id, "Cancelled", event.cancelled_at)

    @on(OrderRefunded)
    def on_order_refunded(self, event: OrderRefunded) -> None:
        self._update_status(event.order_id, "Refunded", event.refunded_at)
