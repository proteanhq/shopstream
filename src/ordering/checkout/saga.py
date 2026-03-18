"""Order Checkout Saga — coordinates the Order → Inventory → Payment flow.

This ProcessManager tracks the checkout process state as it progresses
through the ordering lifecycle. It lives in the Ordering domain and
reacts ONLY to internal ordering events.

External events (from Inventory and Payments) are translated into internal
ordering commands by subscribers (inventory_subscriber.py, payment_subscriber.py),
which in turn cause the Order aggregate to raise internal events that this
saga reacts to.

Flow:
    1. OrderConfirmed → set status awaiting_reservation
    2. PaymentPending → set status awaiting_payment (stock was reserved externally)
    3a. PaymentSucceeded → completed (end)
    3b. PaymentFailed → retrying (if under max retries) or CancelOrder → failed (end)
    4. OrderCancelled → failed (end) (reservation released or other cancellation)
"""

import logging

from protean.exceptions import ValidationError
from protean.fields import DateTime, Float, Identifier, Integer, String
from protean.utils.globals import current_domain
from protean.utils.mixins import handle
from protean.utils.processing import Priority

from ordering.domain import ordering
from ordering.order.events import (
    OrderCancelled,
    OrderConfirmed,
    PaymentFailed,
    PaymentPending,
    PaymentSucceeded,
)

logger = logging.getLogger(__name__)

MAX_PAYMENT_RETRIES = 3


@ordering.process_manager(
    stream_categories=[
        "ordering::order",
    ]
)
class OrderCheckoutSaga:
    """Coordinates the checkout process, reacting only to internal ordering events."""

    order_id = Identifier()
    status = String(default="new")
    payment_id = Identifier()
    retry_count = Integer(default=0)
    failure_reason = String()
    started_at = DateTime()
    completed_at = DateTime()
    amount = Float()

    @handle(OrderConfirmed, start=True, correlate="order_id")
    def on_order_confirmed(self, event: OrderConfirmed) -> None:
        """Step 1: Order confirmed — wait for inventory reservation."""
        self.order_id = event.order_id
        self.status = "awaiting_reservation"
        self.started_at = event.confirmed_at

    @handle(PaymentPending, correlate="order_id")
    def on_payment_pending(self, event: PaymentPending) -> None:
        """Step 2: Payment pending — stock was reserved, payment initiated.

        The InventoryEventsSubscriber received StockReserved from the external
        bus and dispatched RecordPaymentPending, which caused this event.
        """
        self.payment_id = event.payment_id
        self.status = "awaiting_payment"

    @handle(PaymentSucceeded, correlate="order_id")
    def on_payment_succeeded(self, event: PaymentSucceeded) -> None:
        """Step 3a: Payment succeeded — saga complete.

        The PaymentEventsSubscriber received PaymentSucceeded from the external
        bus and dispatched RecordPaymentSuccess, which caused this event.
        """
        if self.status in ("completed", "failed"):
            return  # Already reached terminal state; skip duplicate

        self.payment_id = event.payment_id
        self.amount = event.amount
        self.status = "completed"
        self.mark_as_complete()

    @handle(PaymentFailed, correlate="order_id")
    def on_payment_failed(self, event: PaymentFailed) -> None:
        """Step 3b: Payment failed — retry or cancel order.

        The PaymentEventsSubscriber received PaymentFailed from the external
        bus and dispatched RecordPaymentFailure, which caused this event.
        The saga owns the retry count and decides when to give up.
        """
        if self.status in ("completed", "failed"):
            return  # Already reached terminal state; skip duplicate

        self.retry_count += 1
        self.failure_reason = event.reason

        if self.retry_count < MAX_PAYMENT_RETRIES:
            self.status = "retrying"
            # The payments domain handles retries; we just track state
        else:
            self.status = "failed"
            from ordering.order.cancellation import CancelOrder

            try:
                current_domain.process(
                    CancelOrder(
                        order_id=self.order_id,
                        reason=f"Payment failed: {event.reason}",
                        cancelled_by="System",
                    ),
                    asynchronous=False,
                    priority=Priority.HIGH,
                )
            except ValidationError:
                logger.info("Order %s already cancelled; skipping CancelOrder", self.order_id)

            self.mark_as_complete()

    @handle(OrderCancelled, correlate="order_id", end=True)
    def on_order_cancelled(self, event: OrderCancelled) -> None:
        """Step 4: Order cancelled — saga ends in failed state.

        This can be triggered by:
        - The InventoryEventsSubscriber dispatching CancelOrder after ReservationReleased
        - The payment retry exhaustion above
        - A manual cancellation
        """
        if self.status in ("completed", "failed"):
            return  # Already reached terminal state; skip duplicate

        self.status = "failed"
        self.failure_reason = f"Order cancelled: {event.reason}"
