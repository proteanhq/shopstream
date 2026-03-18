"""Application tests for Inventory cross-domain subscriber."""

from datetime import UTC, datetime

from protean import current_domain

from notifications.notification.inventory_subscriber import InventoryEventsSubscriber
from notifications.notification.notification import (
    Notification,
    NotificationChannel,
    NotificationType,
    RecipientType,
)


def _build_message(event_type: str, data: dict) -> dict:
    """Build a broker message payload with metadata and data."""
    return {
        "data": data,
        "metadata": {"headers": {"type": event_type}},
    }


def _low_stock_message(**overrides):
    defaults = {
        "inventory_item_id": "inv-001",
        "product_id": "prod-001",
        "variant_id": "var-001",
        "sku": "SKU-001",
        "current_available": 5,
        "reorder_point": 10,
        "detected_at": datetime.now(UTC).isoformat(),
    }
    defaults.update(overrides)
    return _build_message("Inventory.LowStockDetected.v1", defaults)


class TestLowStockAlertHandler:
    def test_creates_internal_slack_notification(self):
        subscriber = InventoryEventsSubscriber()
        subscriber(_low_stock_message())

        repo = current_domain.repository_for(Notification)
        notifications = (
            repo.query.filter(
                notification_type=NotificationType.LOW_STOCK_ALERT.value,
            )
            .all()
            .items
        )
        assert len(notifications) >= 1

    def test_low_stock_uses_slack_channel(self):
        subscriber = InventoryEventsSubscriber()
        subscriber(
            _low_stock_message(
                inventory_item_id="inv-002",
                product_id="prod-002",
                variant_id="var-002",
                sku="SKU-002",
                current_available=3,
            )
        )

        repo = current_domain.repository_for(Notification)
        notifications = (
            repo.query.filter(
                notification_type=NotificationType.LOW_STOCK_ALERT.value,
                channel=NotificationChannel.SLACK.value,
            )
            .all()
            .items
        )
        assert len(notifications) >= 1

    def test_low_stock_is_internal_type(self):
        subscriber = InventoryEventsSubscriber()
        subscriber(
            _low_stock_message(
                inventory_item_id="inv-003",
                product_id="prod-003",
                variant_id="var-003",
                sku="SKU-003",
                current_available=2,
                reorder_point=5,
            )
        )

        repo = current_domain.repository_for(Notification)
        notifications = (
            repo.query.filter(
                notification_type=NotificationType.LOW_STOCK_ALERT.value,
            )
            .all()
            .items
        )
        found = [n for n in notifications if str(n.recipient_id) == "operations"]
        assert len(found) >= 1
        assert found[-1].recipient_type == RecipientType.INTERNAL.value


class TestIgnoresUnrelatedEvents:
    def test_ignores_non_matching_events(self):
        """Non-low-stock events on the stream should be ignored."""
        subscriber = InventoryEventsSubscriber()
        subscriber(_build_message("Inventory.StockInitialized.v1", {"inventory_item_id": "inv-ignore"}))
