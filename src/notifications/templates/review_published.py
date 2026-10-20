"""Review published template — sent when a review is approved."""

from typing import Any

from notifications.notification.notification import (
    NotificationChannel,
    NotificationType,
)


class ReviewPublishedTemplate:
    notification_type = NotificationType.REVIEW_PUBLISHED.value
    default_channels = [NotificationChannel.EMAIL.value]

    @staticmethod
    def render(_context: dict[str, Any]) -> dict[str, str]:
        return {
            "subject": "Your review has been published",
            "body": (
                "Great news! Your review has been approved and is now "
                "visible to other shoppers.\n\n"
                "Thank you for sharing your experience! Your feedback "
                "helps others make better purchasing decisions.\n\n"
                "The ShopStream Team"
            ),
        }
