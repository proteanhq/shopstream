"""Cart recovery template — sent 24 hours after cart abandonment."""

from notifications.notification.notification import (
    NotificationChannel,
    NotificationType,
)


class CartRecoveryTemplate:
    notification_type = NotificationType.CART_RECOVERY.value
    default_channels = [NotificationChannel.EMAIL.value]

    @staticmethod
    def render(_context: dict) -> dict:
        return {
            "subject": "You left items in your cart",
            "body": (
                "It looks like you left some items in your shopping cart.\n\n"
                "Don't miss out! Come back and complete your purchase "
                "before they sell out.\n\n"
                "Happy shopping!\nThe ShopStream Team"
            ),
        }
