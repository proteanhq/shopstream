"""Inbound cross-domain event handler — Notifications reacts to Cart events.

Listens for CartAbandoned to schedule a cart recovery email 24 hours later.
"""

from datetime import UTC, datetime, timedelta

import structlog
from notifications.domain import notifications
from notifications.notification.helpers import create_notifications_for_customer
from notifications.notification.notification import Notification, NotificationType
from protean.utils.mixins import handle
from shared.events.ordering import CartAbandoned

logger = structlog.get_logger(__name__)

notifications.register_external_event(CartAbandoned, "Ordering.CartAbandoned.v1")


@notifications.event_handler(part_of=Notification, stream_category="ordering::cart")
class CartEventsHandler:
    """Reacts to Cart events to send recovery notifications."""

    @handle(CartAbandoned)
    def on_cart_abandoned(self, event: CartAbandoned) -> None:
        """Schedule a cart recovery email 24 hours after abandonment."""
        if not event.customer_id:
            logger.info(
                "CartAbandoned missing customer_id (guest cart), skipping recovery",
                cart_id=str(event.cart_id),
            )
            return

        scheduled_for = datetime.now(UTC) + timedelta(hours=24)

        create_notifications_for_customer(
            customer_id=str(event.customer_id),
            notification_type=NotificationType.CART_RECOVERY.value,
            context={
                "cart_id": str(event.cart_id),
            },
            source_event_type="Ordering.CartAbandoned.v1",
            scheduled_for=scheduled_for,
        )
