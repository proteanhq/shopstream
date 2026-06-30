"""Tier upgraded template — sent when a loyalty account reaches a new tier."""

from notifications.notification.notification import (
    NotificationChannel,
    NotificationType,
)


class TierUpgradedTemplate:
    notification_type = NotificationType.TIER_UPGRADED.value
    default_channels = [NotificationChannel.EMAIL.value, NotificationChannel.PUSH.value]

    @staticmethod
    def render(context: dict) -> dict:
        new_tier = str(context.get("new_tier", "a new")).title()
        old_tier = str(context.get("old_tier", "")).title()
        lifetime_points = context.get("lifetime_points", "")
        from_clause = f" from {old_tier}" if old_tier else ""
        return {
            "subject": f"You've reached {new_tier} status!",
            "body": (
                f"Congratulations — your loyalty tier has been upgraded{from_clause} to "
                f"{new_tier}.\n\n"
                f"Lifetime points: {lifetime_points}.\n\n"
                "Enjoy your new rewards and perks!"
            ),
        }
