"""Delivery confirmation template — sent when order is delivered."""

from notifications.notification.notification import (
    NotificationChannel,
    NotificationType,
)


class DeliveryConfirmationTemplate:
    notification_type = NotificationType.DELIVERY_CONFIRMATION.value
    default_channels = [
        NotificationChannel.EMAIL.value,
        NotificationChannel.PUSH.value,
    ]

    @staticmethod
    def render(context: dict) -> dict:
        order_id = context.get("order_id", "N/A")
        return {
            "subject": "Your Order Has Been Delivered",
            "body": (
                f"Your order #{order_id} has been delivered.\n\n"
                "We hope you enjoy your purchase! If you have any issues, "
                "please don't hesitate to reach out to our support team.\n\n"
                "Thank you for shopping with ShopStream!"
            ),
        }
