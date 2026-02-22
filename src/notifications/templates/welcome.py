"""Welcome notification template — sent when a customer registers."""

from notifications.notification.notification import (
    NotificationChannel,
    NotificationType,
)


class WelcomeTemplate:
    notification_type = NotificationType.WELCOME.value
    default_channels = [NotificationChannel.EMAIL.value]

    @staticmethod
    def render(context: dict) -> dict:
        first_name = context.get("first_name", "there")
        return {
            "subject": f"Welcome to ShopStream, {first_name}!",
            "body": (
                f"Hi {first_name},\n\n"
                "Thank you for joining ShopStream! We're excited to have you.\n\n"
                "Start exploring our catalogue and find great deals.\n\n"
                "Happy shopping!\n"
                "The ShopStream Team"
            ),
        }
