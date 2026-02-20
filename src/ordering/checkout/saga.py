"""Order Checkout Saga — coordinates the Order → Inventory → Payment flow.

This ProcessManager orchestrates the checkout process across three bounded
contexts: Ordering, Inventory, and Payments. It lives in the Ordering domain
because it primarily coordinates order lifecycle state changes.

Flow:
    1. OrderConfirmed → set status awaiting_reservation
    2. StockReserved → issue RecordPaymentPending command → awaiting_payment
    3a. PaymentSucceeded → issue RecordPaymentSuccess command → completed (end)
    3b. PaymentFailed (can_retry) → retrying (wait for external retry)
    3b. PaymentFailed (no retry) → issue CancelOrder → failed (end)
    4. ReservationReleased → issue CancelOrder → failed (end)

Cross-domain events are imported from shared.events module and registered
as external events via ordering.register_external_event().
"""

from protean.fields import DateTime, Float, Identifier, Integer, String
from protean.utils.globals import current_domain
from protean.utils.mixins import handle
from shared.events.inventory import ReservationReleased, StockReserved
from shared.events.payments import PaymentFailed, PaymentSucceeded

from ordering.domain import ordering
from ordering.order.events import OrderConfirmed

# Register external events from other domains so Protean can deserialize them
ordering.register_external_event(StockReserved, "Inventory.StockReserved.v1")
ordering.register_external_event(ReservationReleased, "Inventory.ReservationReleased.v1")
ordering.register_external_event(PaymentSucceeded, "Payments.PaymentSucceeded.v1")
ordering.register_external_event(PaymentFailed, "Payments.PaymentFailed.v1")

MAX_PAYMENT_RETRIES = 3


@ordering.process_manager(
    stream_categories=[
        "ordering::order",
        "inventory::inventory_item",
        "payments::payment",
    ]
)
class OrderCheckoutSaga:
    """Coordinates the checkout process across ordering, inventory, and payments."""

    order_id = Identifier()
    status = String(default="new")
    reservation_id = Identifier()
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

    @handle(StockReserved, correlate="order_id")
    def on_stock_reserved(self, event: StockReserved) -> None:
        """Step 2: Stock reserved — initiate payment."""
        self.reservation_id = event.reservation_id
        self.status = "awaiting_payment"

        # Dispatch command to ordering domain to record payment pending
        from ordering.order.payment import RecordPaymentPending

        current_domain.process(
            RecordPaymentPending(
                order_id=self.order_id,
                payment_id=f"saga-pay-{self.order_id}",
                payment_method="credit_card",
            ),
            asynchronous=False,
        )

    @handle(PaymentSucceeded, correlate="order_id")
    def on_payment_succeeded(self, event: PaymentSucceeded) -> None:
        """Step 3a: Payment succeeded — record success and complete saga."""
        self.payment_id = event.payment_id
        self.amount = event.amount
        self.status = "completed"

        from ordering.order.payment import RecordPaymentSuccess

        current_domain.process(
            RecordPaymentSuccess(
                order_id=self.order_id,
                payment_id=event.payment_id,
                amount=event.amount,
                payment_method="credit_card",
            ),
            asynchronous=False,
        )
        self.mark_as_complete()

    @handle(PaymentFailed, correlate="order_id")
    def on_payment_failed(self, event: PaymentFailed) -> None:
        """Step 3b: Payment failed — retry or cancel order."""
        self.retry_count = event.attempt_number
        self.failure_reason = event.reason

        if event.can_retry and self.retry_count < MAX_PAYMENT_RETRIES:
            self.status = "retrying"
            # The payments domain handles retries; we just track state
        else:
            self.status = "failed"
            from ordering.order.cancellation import CancelOrder

            current_domain.process(
                CancelOrder(
                    order_id=self.order_id,
                    reason=f"Payment failed: {event.reason}",
                    cancelled_by="System",
                ),
                asynchronous=False,
            )
            self.mark_as_complete()

    @handle(ReservationReleased, correlate="order_id", end=True)
    def on_reservation_released(self, event: ReservationReleased) -> None:
        """Step 4: Reservation released (timeout or cancellation) — cancel order."""
        self.status = "failed"
        self.failure_reason = f"Reservation released: {event.reason}"

        from ordering.order.cancellation import CancelOrder

        current_domain.process(
            CancelOrder(
                order_id=self.order_id,
                reason=f"Inventory reservation released: {event.reason}",
                cancelled_by="System",
            ),
            asynchronous=False,
        )
