"""Application tests for Cart cross-domain subscriber."""

from datetime import UTC, datetime

from protean import current_domain

from notifications.notification.cart_subscriber import CartEventsSubscriber
from notifications.notification.notification import (
    Notification,
    NotificationType,
)


def _build_message(event_type: str, data: dict) -> dict:
    """Build a broker message payload with metadata and data."""
    return {
        "data": data,
        "metadata": {"headers": {"type": event_type}},
    }


class TestCartRecoveryHandler:
    def test_creates_cart_recovery_notification(self):
        subscriber = CartEventsSubscriber()
        subscriber(
            _build_message(
                "Ordering.CartAbandoned.v1",
                {
                    "cart_id": "cart-001",
                    "customer_id": "cust-cart-1",
                    "abandoned_at": datetime.now(UTC).isoformat(),
                },
            )
        )

        repo = current_domain.repository_for(Notification)
        notifications = (
            repo.query.filter(
                recipient_id="cust-cart-1",
                notification_type=NotificationType.CART_RECOVERY.value,
            )
            .all()
            .items
        )
        assert len(notifications) >= 1

    def test_cart_recovery_is_scheduled(self):
        subscriber = CartEventsSubscriber()
        subscriber(
            _build_message(
                "Ordering.CartAbandoned.v1",
                {
                    "cart_id": "cart-002",
                    "customer_id": "cust-cart-2",
                    "abandoned_at": datetime.now(UTC).isoformat(),
                },
            )
        )

        repo = current_domain.repository_for(Notification)
        notifications = (
            repo.query.filter(
                recipient_id="cust-cart-2",
            )
            .all()
            .items
        )
        assert notifications[0].scheduled_for is not None

    def test_skips_guest_cart(self):
        subscriber = CartEventsSubscriber()
        subscriber(
            _build_message(
                "Ordering.CartAbandoned.v1",
                {
                    "cart_id": "cart-003",
                    "customer_id": None,
                    "abandoned_at": datetime.now(UTC).isoformat(),
                },
            )
        )
        # Should not raise — just logs and skips


class TestIgnoresUnrelatedEvents:
    def test_ignores_non_matching_events(self):
        """Non-cart-abandoned events on the stream should be ignored."""
        subscriber = CartEventsSubscriber()
        subscriber(_build_message("Ordering.CartItemAdded.v1", {"cart_id": "cart-ignore"}))
