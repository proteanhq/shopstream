"""Inbound cross-domain event handler — Notifications reacts to Payment events.

Listens for PaymentSucceeded (receipt) and RefundCompleted (refund notice).
"""

import structlog
from notifications.domain import notifications
from notifications.notification.helpers import create_notifications_for_customer
from notifications.notification.notification import Notification, NotificationType
from protean.utils.mixins import handle
from shared.events.payments import PaymentSucceeded, RefundCompleted

logger = structlog.get_logger(__name__)

notifications.register_external_event(PaymentSucceeded, "Payments.PaymentSucceeded.v1")
notifications.register_external_event(RefundCompleted, "Payments.RefundCompleted.v1")


@notifications.event_handler(part_of=Notification, stream_category="payments::payment")
class PaymentEventsHandler:
    """Reacts to Payment domain events to send customer notifications."""

    @handle(PaymentSucceeded)
    def on_payment_succeeded(self, event: PaymentSucceeded) -> None:
        """Send payment receipt when payment is captured."""
        create_notifications_for_customer(
            customer_id=str(event.customer_id),
            notification_type=NotificationType.PAYMENT_RECEIPT.value,
            context={
                "order_id": str(event.order_id),
                "amount": str(event.amount),
                "currency": event.currency,
            },
            source_event_type="Payments.PaymentSucceeded.v1",
        )

    @handle(RefundCompleted)
    def on_refund_completed(self, event: RefundCompleted) -> None:
        """Send refund notification when a refund is processed."""
        if not event.customer_id:
            logger.info(
                "RefundCompleted missing customer_id, skipping notification",
                payment_id=str(event.payment_id),
            )
            return

        create_notifications_for_customer(
            customer_id=str(event.customer_id),
            notification_type=NotificationType.REFUND_NOTIFICATION.value,
            context={
                "order_id": str(event.order_id),
                "amount": str(event.amount),
                "currency": event.currency or "USD",
                "reason": event.reason or "as requested",
            },
            source_event_type="Payments.RefundCompleted.v1",
        )
