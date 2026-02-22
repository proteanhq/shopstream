"""Application tests for Ordering cross-domain event handlers."""

import json
from datetime import UTC, datetime

from notifications.notification.notification import (
    Notification,
    NotificationType,
)
from notifications.notification.ordering_events import OrderingEventsHandler
from protean import current_domain
from shared.events.ordering import OrderCancelled, OrderCreated, OrderDelivered


def _fire_order_created(
    order_id="ord-001",
    customer_id="cust-001",
    grand_total=99.99,
    currency="USD",
):
    return OrderCreated(
        order_id=order_id,
        customer_id=customer_id,
        items=json.dumps([{"product_id": "prod-1", "quantity": 1}]),
        grand_total=grand_total,
        currency=currency,
        created_at=datetime.now(UTC),
    )


def _fire_order_delivered(
    order_id="ord-001",
    customer_id="cust-001",
):
    return OrderDelivered(
        order_id=order_id,
        customer_id=customer_id,
        delivered_at=datetime.now(UTC),
    )


class TestOrderConfirmationHandler:
    def test_creates_order_confirmation_notification(self):
        event = _fire_order_created(customer_id="cust-ord-1")
        handler = OrderingEventsHandler()
        handler.on_order_created(event)

        repo = current_domain.repository_for(Notification)
        notifications = (
            repo._dao.query.filter(
                recipient_id="cust-ord-1",
                notification_type=NotificationType.ORDER_CONFIRMATION.value,
            )
            .all()
            .items
        )
        assert len(notifications) >= 1

    def test_order_confirmation_includes_order_id(self):
        event = _fire_order_created(customer_id="cust-ord-2", order_id="ORD-123")
        handler = OrderingEventsHandler()
        handler.on_order_created(event)

        repo = current_domain.repository_for(Notification)
        notifications = (
            repo._dao.query.filter(
                recipient_id="cust-ord-2",
            )
            .all()
            .items
        )
        assert "ORD-123" in notifications[0].body


class TestReviewPromptHandler:
    def test_creates_scheduled_review_prompt(self):
        event = _fire_order_delivered(customer_id="cust-del-1")
        handler = OrderingEventsHandler()
        handler.on_order_delivered(event)

        repo = current_domain.repository_for(Notification)
        notifications = (
            repo._dao.query.filter(
                recipient_id="cust-del-1",
                notification_type=NotificationType.REVIEW_PROMPT.value,
            )
            .all()
            .items
        )
        assert len(notifications) >= 1
        assert notifications[0].scheduled_for is not None

    def test_skips_when_no_customer_id(self):
        event = OrderDelivered(
            order_id="ord-x",
            customer_id=None,
            delivered_at=datetime.now(UTC),
        )
        handler = OrderingEventsHandler()
        handler.on_order_delivered(event)
        # Should not create any notifications — just logs


class TestOrderCancelledHandler:
    def test_handles_order_cancelled_without_error(self):
        """OrderCancelled logs a warning (no customer_id on shared event)."""
        event = OrderCancelled(
            order_id="ord-cancel-1",
            reason="Customer requested",
            cancelled_by="customer",
            cancelled_at=datetime.now(UTC),
        )
        handler = OrderingEventsHandler()
        handler.on_order_cancelled(event)
        # No notification created — just logs

    def test_handles_system_cancellation(self):
        event = OrderCancelled(
            order_id="ord-cancel-2",
            reason="Payment expired",
            cancelled_by="system",
            cancelled_at=datetime.now(UTC),
        )
        handler = OrderingEventsHandler()
        handler.on_order_cancelled(event)
