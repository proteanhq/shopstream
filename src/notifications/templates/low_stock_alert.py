"""Low stock alert template — internal notification to operations."""

from notifications.notification.notification import (
    NotificationChannel,
    NotificationType,
    RecipientType,
)


class LowStockAlertTemplate:
    notification_type = NotificationType.LOW_STOCK_ALERT.value
    default_channels = [NotificationChannel.SLACK.value]
    recipient_type = RecipientType.INTERNAL.value

    @staticmethod
    def render(context: dict) -> dict:
        sku = context.get("sku", "N/A")
        product_id = context.get("product_id", "N/A")
        warehouse_id = context.get("warehouse_id", "N/A")
        current_available = context.get("current_available", 0)
        reorder_point = context.get("reorder_point", 0)
        return {
            "subject": f"[Low Stock] {sku}",
            "body": (
                f"Low stock alert for SKU: {sku}\n\n"
                f"Product ID: {product_id}\n"
                f"Warehouse: {warehouse_id}\n"
                f"Current Available: {current_available}\n"
                f"Reorder Point: {reorder_point}\n\n"
                "Please review and reorder as needed."
            ),
        }
