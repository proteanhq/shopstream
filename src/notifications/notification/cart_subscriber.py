"""Inbound cross-domain subscriber — Notifications reacts to Cart events.

Listens for CartAbandoned to schedule a cart recovery email 24 hours later.

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


@notifications.subscriber(broker="global", stream="ordering::cart")
class CartEventsSubscriber:
    """Reacts to Cart events to send recovery notifications.

    ACL pattern: receives raw broker message dict, extracts event type from
    metadata.headers.type, and creates notifications. Ignores all event
    types not relevant to the Notifications domain.
    """

    def __call__(self, payload: dict) -> None:
        event_type = payload.get("metadata", {}).get("headers", {}).get("type", "")
        data = payload.get("data", {})

        if "CartAbandoned" in event_type:
            self._on_cart_abandoned(data)

    def _on_cart_abandoned(self, data: dict) -> None:
        """Schedule a cart recovery email 24 hours after abandonment."""
        customer_id = data.get("customer_id")
        if not customer_id:
            logger.info(
                "CartAbandoned missing customer_id (guest cart), skipping recovery",
                cart_id=str(data.get("cart_id", "")),
            )
            return

        scheduled_for = datetime.now(UTC) + timedelta(hours=24)

        create_notifications_for_customer(
            customer_id=str(customer_id),
            notification_type=NotificationType.CART_RECOVERY.value,
            context={
                "cart_id": str(data["cart_id"]),
            },
            source_event_type="Ordering.CartAbandoned.v1",
            scheduled_for=scheduled_for,
        )
