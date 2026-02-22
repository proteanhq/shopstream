"""Review prompt template — sent 7 days after delivery."""

from notifications.notification.notification import (
    NotificationChannel,
    NotificationType,
)


class ReviewPromptTemplate:
    notification_type = NotificationType.REVIEW_PROMPT.value
    default_channels = [
        NotificationChannel.EMAIL.value,
        NotificationChannel.PUSH.value,
    ]

    @staticmethod
    def render(context: dict) -> dict:
        order_id = context.get("order_id", "N/A")
        return {
            "subject": "How was your purchase?",
            "body": (
                f"You received your order #{order_id} recently.\n\n"
                "We'd love to hear your thoughts! Leave a review to help "
                "other shoppers make great choices.\n\n"
                "Your feedback makes a real difference.\n\n"
                "Thank you!\nThe ShopStream Team"
            ),
        }
