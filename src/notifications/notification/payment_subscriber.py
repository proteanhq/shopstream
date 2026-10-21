"""Inbound cross-domain subscriber — Notifications reacts to Payment events.

Listens for PaymentSucceeded (receipt) and RefundCompleted (refund notice).

Uses the subscriber (ACL) pattern: receives raw dict payloads from the global
broker, filters by event type, and translates into domain-local side effects.
No dependency on shared event classes or register_external_event.
"""

from typing import Any

import structlog

from notifications.domain import notifications
from notifications.notification.helpers import create_notifications_for_customer, two_places
from notifications.notification.notification import NotificationType

logger = structlog.get_logger(__name__)


@notifications.subscriber(broker="global", stream="payments::payment")
class PaymentEventsSubscriber:
    """Reacts to Payment domain events to send customer notifications.

    ACL pattern: receives raw broker message dict, extracts event type from
    metadata.headers.type, and creates notifications. Ignores all event
    types not relevant to the Notifications domain.
    """

    def __call__(self, payload: dict[str, Any]) -> None:
        event_type = payload.get("metadata", {}).get("headers", {}).get("type", "")
        data = payload.get("data", {})

        if "PaymentSucceeded" in event_type:
            self._on_payment_succeeded(data, event_type)
        elif "RefundCompleted" in event_type:
            self._on_refund_completed(data, event_type)

    def _on_payment_succeeded(self, data: dict[str, Any], event_type: str) -> None:
        """Send payment receipt when payment is captured."""
        amount = two_places(data.get("amount"))
        if not amount:
            logger.info(
                "PaymentSucceeded missing amount, skipping notification",
                payment_id=str(data.get("payment_id", "")),
            )
            return

        create_notifications_for_customer(
            customer_id=str(data["customer_id"]),
            notification_type=NotificationType.PAYMENT_RECEIPT.value,
            context={
                "order_id": str(data["order_id"]),
                "amount": amount,
                "currency": data.get("currency", "USD"),
            },
            source_event_type=event_type,
        )

    def _on_refund_completed(self, data: dict[str, Any], event_type: str) -> None:
        """Send refund notification when a refund is processed."""
        customer_id = data.get("customer_id")
        if not customer_id:
            logger.info(
                "RefundCompleted missing customer_id, skipping notification",
                payment_id=str(data.get("payment_id", "")),
            )
            return
        amount = two_places(data.get("amount"))
        if not amount:
            logger.info(
                "RefundCompleted missing amount, skipping notification",
                payment_id=str(data.get("payment_id", "")),
            )
            return

        create_notifications_for_customer(
            customer_id=str(customer_id),
            notification_type=NotificationType.REFUND_NOTIFICATION.value,
            context={
                "order_id": str(data["order_id"]),
                "amount": amount,
                "currency": data.get("currency") or "USD",
                "reason": data.get("reason") or "as requested",
            },
            source_event_type=event_type,
        )
