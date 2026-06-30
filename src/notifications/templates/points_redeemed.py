"""Points redeemed template — sent when a customer redeems loyalty points."""

from notifications.notification.notification import (
    NotificationChannel,
    NotificationType,
)


class PointsRedeemedTemplate:
    notification_type = NotificationType.POINTS_REDEEMED.value
    default_channels = [NotificationChannel.EMAIL.value]

    @staticmethod
    def render(context: dict) -> dict:
        amount = context.get("amount", "0")
        balance_after = context.get("balance_after", "0")
        reason = context.get("reason") or "your redemption"
        return {
            "subject": f"You redeemed {amount} points",
            "body": (
                f"{amount} loyalty points have been redeemed for {reason}.\n\n"
                f"Your remaining points balance is {balance_after}.\n\n"
                "Thank you for being a member!"
            ),
        }
