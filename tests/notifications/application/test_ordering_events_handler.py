"""Application tests for Ordering cross-domain subscriber."""

from datetime import UTC, datetime

from protean import current_domain

from notifications.notification.notification import (
    Notification,
    NotificationType,
)
from notifications.notification.ordering_subscriber import OrderingEventsSubscriber


def _build_message(event_type: str, data: dict) -> dict:
    """Build a broker message payload with metadata and data."""
    return {
        "data": data,
        "metadata": {"headers": {"type": event_type}},
    }


class TestOrderConfirmationHandler:
    def test_creates_order_confirmation_notification(self):
        payload = _build_message(
            "Ordering.OrderCreated.v1",
            {
                "order_id": "ord-001",
                "customer_id": "cust-ord-1",
                "items": [{"product_id": "prod-1", "quantity": 1}],
                "shipping_address": {
                    "street": "1 Main St",
                    "city": "NYC",
                    "state": "NY",
                    "postal_code": "10001",
                    "country": "US",
                },
                "billing_address": {
                    "street": "1 Main St",
                    "city": "NYC",
                    "state": "NY",
                    "postal_code": "10001",
                    "country": "US",
                },
                "subtotal": 99.99,
                "grand_total": 99.99,
                "currency": "USD",
                "created_at": datetime.now(UTC).isoformat(),
            },
        )
        subscriber = OrderingEventsSubscriber()
        subscriber(payload)

        repo = current_domain.repository_for(Notification)
        notifications = (
            repo.query.filter(
                recipient_id="cust-ord-1",
                notification_type=NotificationType.ORDER_CONFIRMATION.value,
            )
            .all()
            .items
        )
        assert len(notifications) >= 1

    def test_order_confirmation_includes_order_id(self):
        payload = _build_message(
            "Ordering.OrderCreated.v1",
            {
                "order_id": "ORD-123",
                "customer_id": "cust-ord-2",
                "items": [{"product_id": "prod-1", "quantity": 1}],
                "shipping_address": {
                    "street": "1 Main St",
                    "city": "NYC",
                    "state": "NY",
                    "postal_code": "10001",
                    "country": "US",
                },
                "billing_address": {
                    "street": "1 Main St",
                    "city": "NYC",
                    "state": "NY",
                    "postal_code": "10001",
                    "country": "US",
                },
                "subtotal": 99.99,
                "grand_total": 99.99,
                "currency": "USD",
                "created_at": datetime.now(UTC).isoformat(),
            },
        )
        subscriber = OrderingEventsSubscriber()
        subscriber(payload)

        repo = current_domain.repository_for(Notification)
        notifications = (
            repo.query.filter(
                recipient_id="cust-ord-2",
            )
            .all()
            .items
        )
        assert "ORD-123" in notifications[0].body


class TestOrderDeliveredMissingCustomerId:
    def test_skips_when_no_customer_id(self):
        """OrderDelivered without customer_id should be skipped without error."""
        payload = _build_message(
            "Ordering.OrderDelivered.v1",
            {
                "order_id": "ord-no-cust",
                "delivered_at": datetime.now(UTC).isoformat(),
            },
        )
        subscriber = OrderingEventsSubscriber()
        subscriber(payload)

        # No notification should have been created
        repo = current_domain.repository_for(Notification)
        notifications = repo.query.filter(notification_type=NotificationType.REVIEW_PROMPT.value).all().items
        matching = [n for n in notifications if "ord-no-cust" in n.body]
        assert len(matching) == 0


class TestReviewPromptHandler:
    def test_creates_scheduled_review_prompt(self):
        payload = _build_message(
            "Ordering.OrderDelivered.v1",
            {
                "order_id": "ord-001",
                "customer_id": "cust-del-1",
                "delivered_at": datetime.now(UTC).isoformat(),
            },
        )
        subscriber = OrderingEventsSubscriber()
        subscriber(payload)

        repo = current_domain.repository_for(Notification)
        notifications = (
            repo.query.filter(
                recipient_id="cust-del-1",
                notification_type=NotificationType.REVIEW_PROMPT.value,
            )
            .all()
            .items
        )
        assert len(notifications) >= 1
        assert notifications[0].scheduled_for is not None


class TestOrderCancelledHandler:
    def test_handles_order_cancelled_without_error(self):
        """OrderCancelled logs a warning (no customer_id on shared event)."""
        payload = _build_message(
            "Ordering.OrderCancelled.v1",
            {
                "order_id": "ord-cancel-1",
                "reason": "Customer requested",
                "cancelled_by": "customer",
                "cancelled_at": datetime.now(UTC).isoformat(),
            },
        )
        subscriber = OrderingEventsSubscriber()
        subscriber(payload)
        # No notification created — just logs

    def test_handles_system_cancellation(self):
        payload = _build_message(
            "Ordering.OrderCancelled.v1",
            {
                "order_id": "ord-cancel-2",
                "reason": "Payment expired",
                "cancelled_by": "system",
                "cancelled_at": datetime.now(UTC).isoformat(),
            },
        )
        subscriber = OrderingEventsSubscriber()
        subscriber(payload)


class TestIgnoresUnrelatedOrderingEvents:
    def test_ignores_non_matching_events(self):
        """Events on the ordering stream that aren't handled should be ignored."""
        subscriber = OrderingEventsSubscriber()
        subscriber(_build_message("Ordering.OrderConfirmed.v1", {"order_id": "ord-ignore"}))
