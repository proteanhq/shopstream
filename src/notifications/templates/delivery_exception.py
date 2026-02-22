"""Delivery exception template — sent when there's a delivery issue."""

from notifications.notification.notification import (
    NotificationChannel,
    NotificationType,
)


class DeliveryExceptionTemplate:
    notification_type = NotificationType.DELIVERY_EXCEPTION.value
    default_channels = [
        NotificationChannel.EMAIL.value,
        NotificationChannel.SMS.value,
    ]

    @staticmethod
    def render(context: dict) -> dict:
        order_id = context.get("order_id", "N/A")
        reason = context.get("reason", "an issue during delivery")
        return {
            "subject": "Delivery Issue with Your Order",
            "body": (
                f"We encountered an issue delivering your order #{order_id}.\n\n"
                f"Issue: {reason}\n\n"
                "Our team is working to resolve this. We'll keep you updated "
                "on any changes.\n\n"
                "If you have questions, please contact our support team."
            ),
        }
