"""Inbound cross-domain subscriber — Notifications reacts to Payment events.

Listens for PaymentSucceeded (receipt) and RefundCompleted (refund notice).

Uses the subscriber (ACL) pattern: receives raw dict payloads from the global
broker, filters by event type, and translates into domain-local side effects.
No dependency on shared event classes or register_external_event.
"""

import structlog

from notifications.domain import notifications
from notifications.notification.helpers import create_notifications_for_customer
from notifications.notification.notification import NotificationType

logger = structlog.get_logger(__name__)


@notifications.subscriber(broker="global", stream="payments::payment")
class PaymentEventsSubscriber:
    """Reacts to Payment domain events to send customer notifications.

    ACL pattern: receives raw broker message dict, extracts event type from
    metadata.headers.type, and creates notifications. Ignores all event
    types not relevant to the Notifications domain.
    """

    def __call__(self, payload: dict) -> None:
        event_type = payload.get("metadata", {}).get("headers", {}).get("type", "")
        data = payload.get("data", {})

        if "PaymentSucceeded" in event_type:
            self._on_payment_succeeded(data)
        elif "RefundCompleted" in event_type:
            self._on_refund_completed(data)

    def _on_payment_succeeded(self, data: dict) -> None:
        """Send payment receipt when payment is captured."""
        create_notifications_for_customer(
            customer_id=str(data["customer_id"]),
            notification_type=NotificationType.PAYMENT_RECEIPT.value,
            context={
                "order_id": str(data["order_id"]),
                "amount": str(data["amount"]),
                "currency": data.get("currency", "USD"),
            },
            source_event_type="Payments.PaymentSucceeded.v1",
        )

    def _on_refund_completed(self, data: dict) -> None:
        """Send refund notification when a refund is processed."""
        customer_id = data.get("customer_id")
        if not customer_id:
            logger.info(
                "RefundCompleted missing customer_id, skipping notification",
                payment_id=str(data.get("payment_id", "")),
            )
            return

        create_notifications_for_customer(
            customer_id=str(customer_id),
            notification_type=NotificationType.REFUND_NOTIFICATION.value,
            context={
                "order_id": str(data["order_id"]),
                "amount": str(data["amount"]),
                "currency": data.get("currency") or "USD",
                "reason": data.get("reason") or "as requested",
            },
            source_event_type="Payments.RefundCompleted.v1",
        )
