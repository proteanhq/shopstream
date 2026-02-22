"""Refund notification template — sent when a refund is processed."""

from notifications.notification.notification import (
    NotificationChannel,
    NotificationType,
)


class RefundNotificationTemplate:
    notification_type = NotificationType.REFUND_NOTIFICATION.value
    default_channels = [NotificationChannel.EMAIL.value]

    @staticmethod
    def render(context: dict) -> dict:
        order_id = context.get("order_id", "N/A")
        amount = context.get("amount", "0.00")
        currency = context.get("currency", "USD")
        reason = context.get("reason", "as requested")
        return {
            "subject": f"Refund Processed - {currency} {amount}",
            "body": (
                f"A refund of {currency} {amount} has been processed "
                f"for order #{order_id}.\n\n"
                f"Reason: {reason}\n\n"
                "The refund should appear in your account within 5-10 "
                "business days, depending on your payment provider.\n\n"
                "Thank you for your patience."
            ),
        }
