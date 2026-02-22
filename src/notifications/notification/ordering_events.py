"""Inbound cross-domain event handler — Notifications reacts to Order events.

Listens for OrderCreated (confirmation), OrderCancelled (cancellation notice),
and OrderDelivered (review prompt scheduled 7 days later).
"""

from datetime import UTC, datetime, timedelta

import structlog
from notifications.domain import notifications
from notifications.notification.helpers import create_notifications_for_customer
from notifications.notification.notification import Notification, NotificationType
from protean.utils.mixins import handle
from shared.events.ordering import OrderCancelled, OrderCreated, OrderDelivered

logger = structlog.get_logger(__name__)

notifications.register_external_event(OrderCreated, "Ordering.OrderCreated.v1")
notifications.register_external_event(OrderCancelled, "Ordering.OrderCancelled.v1")
notifications.register_external_event(OrderDelivered, "Ordering.OrderDelivered.v1")


@notifications.event_handler(part_of=Notification, stream_category="ordering::order")
class OrderingEventsHandler:
    """Reacts to Ordering domain events to send customer notifications."""

    @handle(OrderCreated)
    def on_order_created(self, event: OrderCreated) -> None:
        """Send order confirmation when an order is placed."""
        create_notifications_for_customer(
            customer_id=str(event.customer_id),
            notification_type=NotificationType.ORDER_CONFIRMATION.value,
            context={
                "order_id": str(event.order_id),
                "grand_total": str(event.grand_total),
                "currency": event.currency or "USD",
            },
            source_event_type="Ordering.OrderCreated.v1",
        )

    @handle(OrderCancelled)
    def on_order_cancelled(self, event: OrderCancelled) -> None:
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
            order_id=str(event.order_id),
            reason=event.reason,
            cancelled_by=event.cancelled_by,
        )

    @handle(OrderDelivered)
    def on_order_delivered(self, event: OrderDelivered) -> None:
        """Schedule a review prompt 7 days after delivery."""
        if not event.customer_id:
            logger.info(
                "OrderDelivered missing customer_id, skipping review prompt",
                order_id=str(event.order_id),
            )
            return

        scheduled_for = datetime.now(UTC) + timedelta(days=7)

        create_notifications_for_customer(
            customer_id=str(event.customer_id),
            notification_type=NotificationType.REVIEW_PROMPT.value,
            context={
                "order_id": str(event.order_id),
            },
            source_event_type="Ordering.OrderDelivered.v1",
            scheduled_for=scheduled_for,
        )
