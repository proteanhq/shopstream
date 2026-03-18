"""Inbound cross-domain subscriber — Notifications reacts to Inventory events.

Listens for LowStockDetected to send internal alerts via Slack.

Uses the subscriber (ACL) pattern: receives raw dict payloads from the global
broker, filters by event type, and translates into domain-local side effects.
No dependency on shared event classes or register_external_event.
"""

import structlog

from notifications.domain import notifications
from notifications.notification.helpers import create_internal_notification
from notifications.notification.notification import NotificationType

logger = structlog.get_logger(__name__)


@notifications.subscriber(broker="global", stream="inventory::inventory_item")
class InventoryEventsSubscriber:
    """Reacts to Inventory domain events to send internal alerts.

    ACL pattern: receives raw broker message dict, extracts event type from
    metadata.headers.type, and creates notifications. Ignores all event
    types not relevant to the Notifications domain.
    """

    def __call__(self, payload: dict) -> None:
        event_type = payload.get("metadata", {}).get("headers", {}).get("type", "")
        data = payload.get("data", {})

        if "LowStockDetected" in event_type:
            self._on_low_stock_detected(data)

    def _on_low_stock_detected(self, data: dict) -> None:
        """Send internal Slack alert when stock drops below reorder point."""
        create_internal_notification(
            notification_type=NotificationType.LOW_STOCK_ALERT.value,
            context={
                "sku": data.get("sku", ""),
                "product_id": str(data.get("product_id", "")),
                "warehouse_id": str(data.get("variant_id", "")),  # Use variant_id as warehouse proxy
                "current_available": data.get("current_available"),
                "reorder_point": data.get("reorder_point"),
            },
            source_event_type="Inventory.LowStockDetected.v1",
        )
