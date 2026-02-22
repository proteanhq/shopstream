"""Application tests for Cart cross-domain event handlers."""

from datetime import UTC, datetime

from notifications.notification.cart_events import CartEventsHandler
from notifications.notification.notification import (
    Notification,
    NotificationType,
)
from protean import current_domain
from shared.events.ordering import CartAbandoned


class TestCartRecoveryHandler:
    def test_creates_cart_recovery_notification(self):
        event = CartAbandoned(
            cart_id="cart-001",
            customer_id="cust-cart-1",
            abandoned_at=datetime.now(UTC),
        )
        handler = CartEventsHandler()
        handler.on_cart_abandoned(event)

        repo = current_domain.repository_for(Notification)
        notifications = (
            repo._dao.query.filter(
                recipient_id="cust-cart-1",
                notification_type=NotificationType.CART_RECOVERY.value,
            )
            .all()
            .items
        )
        assert len(notifications) >= 1

    def test_cart_recovery_is_scheduled(self):
        event = CartAbandoned(
            cart_id="cart-002",
            customer_id="cust-cart-2",
            abandoned_at=datetime.now(UTC),
        )
        handler = CartEventsHandler()
        handler.on_cart_abandoned(event)

        repo = current_domain.repository_for(Notification)
        notifications = (
            repo._dao.query.filter(
                recipient_id="cust-cart-2",
            )
            .all()
            .items
        )
        assert notifications[0].scheduled_for is not None

    def test_skips_guest_cart(self):
        event = CartAbandoned(
            cart_id="cart-003",
            customer_id=None,
            abandoned_at=datetime.now(UTC),
        )
        handler = CartEventsHandler()
        handler.on_cart_abandoned(event)
        # Should not raise — just logs and skips
