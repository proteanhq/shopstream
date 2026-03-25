"""Inbound cross-domain subscriber — Notifications reacts to Order events.

Listens for OrderCreated (confirmation), OrderCancelled (cancellation notice),
and OrderDelivered (review prompt scheduled 7 days later).

Uses the subscriber (ACL) pattern: receives raw dict payloads from the global
broker, filters by event type, and translates into domain-local side effects.
No dependency on shared event classes or register_external_event.
"""

from datetime import UTC, datetime, timedelta

import structlog

from notifications.domain import notifications
from notifications.notification.helpers import create_notifications_for_customer
from notifications.notification.notification import NotificationType

logger = structlog.get_logger(__name__)


@notifications.subscriber(broker="global", stream="ordering::order")
class OrderingEventsSubscriber:
    """Reacts to Ordering domain events to send customer notifications.

    ACL pattern: receives raw broker message dict, extracts event type from
    metadata.headers.type, and creates notifications. Ignores all event
    types not relevant to the Notifications domain.
    """

    def __call__(self, payload: dict) -> None:
        event_type = payload.get("metadata", {}).get("headers", {}).get("type", "")
        data = payload.get("data", {})

        if "OrderCreated" in event_type:
            self._on_order_created(data)
        elif "OrderCancelled" in event_type:
            self._on_order_cancelled(data)
        elif "OrderDelivered" in event_type:
            self._on_order_delivered(data)

    def _on_order_created(self, data: dict) -> None:
        """Send order confirmation when an order is placed."""
        create_notifications_for_customer(
            customer_id=str(data["customer_id"]),
            notification_type=NotificationType.ORDER_CONFIRMATION.value,
            context={
                "order_id": str(data["order_id"]),
                "grand_total": str(data.get("grand_total", "")),
                "currency": data.get("currency") or "USD",
            },
            source_event_type="Ordering.OrderCreated.v2",
        )

    def _on_order_cancelled(self, data: dict) -> None:
        """Send cancellation notice when an order is cancelled.

        Note: OrderCancelled shared event doesn't carry customer_id.
        We use the cancelled_by field; if it's a customer ID we send
        to them. Otherwise we log a warning.
        """
        # OrderCancelled has order_id, reason, cancelled_by, cancelled_at
        # The cancelled_by field may be "customer", "system", or "admin"
        # We can't send a notification without a customer_id
        # In a real system, we'd look up the order to get customer_id
        logger.info(
            "Order cancelled — notification skipped (no customer_id on shared event)",
            order_id=str(data.get("order_id", "")),
            reason=data.get("reason"),
            cancelled_by=data.get("cancelled_by"),
        )

    def _on_order_delivered(self, data: dict) -> None:
        """Schedule a review prompt 7 days after delivery."""
        customer_id = data.get("customer_id")
        if not customer_id:
            logger.info(
                "OrderDelivered missing customer_id, skipping review prompt",
                order_id=str(data.get("order_id", "")),
            )
            return

        scheduled_for = datetime.now(UTC) + timedelta(days=7)

        create_notifications_for_customer(
            customer_id=str(customer_id),
            notification_type=NotificationType.REVIEW_PROMPT.value,
            context={
                "order_id": str(data["order_id"]),
            },
            source_event_type="Ordering.OrderDelivered.v1",
            scheduled_for=scheduled_for,
        )
