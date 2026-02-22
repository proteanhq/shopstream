"""Shipping update template — sent when order is handed off to carrier."""

from notifications.notification.notification import (
    NotificationChannel,
    NotificationType,
)


class ShippingUpdateTemplate:
    notification_type = NotificationType.SHIPPING_UPDATE.value
    default_channels = [
        NotificationChannel.EMAIL.value,
        NotificationChannel.SMS.value,
        NotificationChannel.PUSH.value,
    ]

    @staticmethod
    def render(context: dict) -> dict:
        order_id = context.get("order_id", "N/A")
        carrier = context.get("carrier", "the carrier")
        tracking_number = context.get("tracking_number", "N/A")
        estimated_delivery = context.get("estimated_delivery", "soon")
        return {
            "subject": "Your Order Has Shipped!",
            "body": (
                f"Great news! Your order #{order_id} has shipped.\n\n"
                f"Carrier: {carrier}\n"
                f"Tracking Number: {tracking_number}\n"
                f"Estimated Delivery: {estimated_delivery}\n\n"
                "You can track your package using the tracking number above."
            ),
        }
