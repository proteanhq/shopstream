"""Inbound cross-domain event handler — Notifications reacts to Inventory events.

Listens for LowStockDetected to send internal alerts via Slack.
"""

import structlog
from notifications.domain import notifications
from notifications.notification.helpers import create_internal_notification
from notifications.notification.notification import Notification, NotificationType
from protean.utils.mixins import handle
from shared.events.inventory import LowStockDetected

logger = structlog.get_logger(__name__)

notifications.register_external_event(LowStockDetected, "Inventory.LowStockDetected.v1")


@notifications.event_handler(part_of=Notification, stream_category="inventory::inventory_item")
class InventoryEventsHandler:
    """Reacts to Inventory domain events to send internal alerts."""

    @handle(LowStockDetected)
    def on_low_stock_detected(self, event: LowStockDetected) -> None:
        """Send internal Slack alert when stock drops below reorder point."""
        create_internal_notification(
            notification_type=NotificationType.LOW_STOCK_ALERT.value,
            context={
                "sku": event.sku,
                "product_id": str(event.product_id),
                "warehouse_id": str(event.variant_id),  # Use variant_id as warehouse proxy
                "current_available": event.current_available,
                "reorder_point": event.reorder_point,
            },
            source_event_type="Inventory.LowStockDetected.v1",
        )
