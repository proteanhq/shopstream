"""Review rejected template — sent when a review is rejected by moderation."""

from notifications.notification.notification import (
    NotificationChannel,
    NotificationType,
)


class ReviewRejectedTemplate:
    notification_type = NotificationType.REVIEW_REJECTED.value
    default_channels = [NotificationChannel.EMAIL.value]

    @staticmethod
    def render(context: dict) -> dict:
        reason = context.get("reason", "It did not meet our community guidelines")
        return {
            "subject": "Update on your review",
            "body": (
                "We were unable to publish your review at this time.\n\n"
                f"Reason: {reason}\n\n"
                "You can edit and resubmit your review. Please ensure it "
                "meets our community guidelines.\n\n"
                "If you have questions, please contact our support team.\n\n"
                "The ShopStream Team"
            ),
        }
