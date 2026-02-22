"""Payment receipt template — sent when payment is captured."""

from notifications.notification.notification import (
    NotificationChannel,
    NotificationType,
)


class PaymentReceiptTemplate:
    notification_type = NotificationType.PAYMENT_RECEIPT.value
    default_channels = [NotificationChannel.EMAIL.value]

    @staticmethod
    def render(context: dict) -> dict:
        order_id = context.get("order_id", "N/A")
        amount = context.get("amount", "0.00")
        currency = context.get("currency", "USD")
        return {
            "subject": f"Payment Receipt - {currency} {amount}",
            "body": (
                f"Payment of {currency} {amount} has been received "
                f"for order #{order_id}.\n\n"
                "This is your official payment receipt.\n\n"
                "Thank you for your purchase!"
            ),
        }
