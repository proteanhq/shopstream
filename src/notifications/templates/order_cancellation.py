"""Order cancellation template — sent when an order is cancelled."""

from notifications.notification.notification import (
    NotificationChannel,
    NotificationType,
)


class OrderCancellationTemplate:
    notification_type = NotificationType.ORDER_CANCELLATION.value
    default_channels = [NotificationChannel.EMAIL.value]

    @staticmethod
    def render(context: dict) -> dict:
        order_id = context.get("order_id", "N/A")
        reason = context.get("reason", "as requested")
        cancelled_by = context.get("cancelled_by", "system")
        return {
            "subject": f"Order #{order_id} Cancelled",
            "body": (
                f"Your order #{order_id} has been cancelled.\n\n"
                f"Reason: {reason}\n"
                f"Cancelled by: {cancelled_by}\n\n"
                "If payment was captured, a refund will be processed "
                "automatically.\n\n"
                "If you have questions, please contact our support team."
            ),
        }
