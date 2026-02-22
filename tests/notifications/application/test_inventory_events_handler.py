"""Application tests for Inventory cross-domain event handlers."""

from datetime import UTC, datetime

from notifications.notification.inventory_events import InventoryEventsHandler
from notifications.notification.notification import (
    Notification,
    NotificationChannel,
    NotificationType,
    RecipientType,
)
from protean import current_domain
from shared.events.inventory import LowStockDetected


def _make_low_stock_event(**overrides):
    defaults = {
        "inventory_item_id": "inv-001",
        "product_id": "prod-001",
        "variant_id": "var-001",
        "sku": "SKU-001",
        "current_available": 5,
        "reorder_point": 10,
        "detected_at": datetime.now(UTC),
    }
    defaults.update(overrides)
    return LowStockDetected(**defaults)


class TestLowStockAlertHandler:
    def test_creates_internal_slack_notification(self):
        event = _make_low_stock_event()
        handler = InventoryEventsHandler()
        handler.on_low_stock_detected(event)

        repo = current_domain.repository_for(Notification)
        notifications = (
            repo._dao.query.filter(
                notification_type=NotificationType.LOW_STOCK_ALERT.value,
            )
            .all()
            .items
        )
        assert len(notifications) >= 1

    def test_low_stock_uses_slack_channel(self):
        event = _make_low_stock_event(
            inventory_item_id="inv-002",
            product_id="prod-002",
            variant_id="var-002",
            sku="SKU-002",
            current_available=3,
        )
        handler = InventoryEventsHandler()
        handler.on_low_stock_detected(event)

        repo = current_domain.repository_for(Notification)
        notifications = (
            repo._dao.query.filter(
                notification_type=NotificationType.LOW_STOCK_ALERT.value,
                channel=NotificationChannel.SLACK.value,
            )
            .all()
            .items
        )
        assert len(notifications) >= 1

    def test_low_stock_is_internal_type(self):
        event = _make_low_stock_event(
            inventory_item_id="inv-003",
            product_id="prod-003",
            variant_id="var-003",
            sku="SKU-003",
            current_available=2,
            reorder_point=5,
        )
        handler = InventoryEventsHandler()
        handler.on_low_stock_detected(event)

        repo = current_domain.repository_for(Notification)
        notifications = (
            repo._dao.query.filter(
                notification_type=NotificationType.LOW_STOCK_ALERT.value,
            )
            .all()
            .items
        )
        found = [n for n in notifications if str(n.recipient_id) == "operations"]
        assert len(found) >= 1
        assert found[-1].recipient_type == RecipientType.INTERNAL.value
