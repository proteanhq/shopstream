"""Order confirmation template — sent when an order is created."""

from notifications.notification.notification import (
    NotificationChannel,
    NotificationType,
)


class OrderConfirmationTemplate:
    notification_type = NotificationType.ORDER_CONFIRMATION.value
    default_channels = [NotificationChannel.EMAIL.value]

    @staticmethod
    def render(context: dict) -> dict:
        order_id = context.get("order_id", "N/A")
        grand_total = context.get("grand_total", "0.00")
        currency = context.get("currency", "USD")
        return {
            "subject": f"Order #{order_id} Confirmed",
            "body": (
                f"Your order #{order_id} has been confirmed.\n\n"
                f"Order Total: {currency} {grand_total}\n\n"
                "We'll notify you once your order ships.\n\n"
                "Thank you for shopping with ShopStream!"
            ),
        }
