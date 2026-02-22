"""NotificationPreference aggregate (CQRS) — customer channel preferences.

Manages per-customer notification preferences: which channels are enabled,
quiet hours (DND), and per-type unsubscribe. Default preferences are created
automatically when a customer registers.
"""

import json
from datetime import UTC, datetime

from notifications.domain import notifications
from notifications.preference.events import (
    ChannelsUpdated,
    PreferencesCreated,
    QuietHoursCleared,
    QuietHoursSet,
    TypeResubscribed,
    TypeUnsubscribed,
)
from protean.exceptions import ValidationError
from protean.fields import Boolean, DateTime, Identifier, String, Text


# ---------------------------------------------------------------------------
# Aggregate Root
# ---------------------------------------------------------------------------
@notifications.aggregate
class NotificationPreference:
    """A customer's notification channel preferences.

    Controls which channels (email, SMS, push) the customer receives
    notifications on, quiet hours, and per-type unsubscribe.
    """

    # Customer link
    customer_id: Identifier(required=True, unique=True)

    # Channel preferences
    email_enabled: Boolean(default=True)
    sms_enabled: Boolean(default=False)
    push_enabled: Boolean(default=False)

    # Quiet hours (DND)
    quiet_hours_start: String(max_length=5)  # "22:00" format
    quiet_hours_end: String(max_length=5)  # "08:00" format

    # Per-type unsubscribe
    unsubscribed_types: Text()  # JSON list of NotificationType values

    # Timestamps
    created_at: DateTime()
    updated_at: DateTime()

    # -------------------------------------------------------------------
    # Factory
    # -------------------------------------------------------------------
    @classmethod
    def create_default(cls, customer_id):
        """Create default preferences for a new customer.

        Default: email enabled, SMS and push disabled, no quiet hours.
        """
        now = datetime.now(UTC)

        preference = cls(
            customer_id=customer_id,
            email_enabled=True,
            sms_enabled=False,
            push_enabled=False,
            unsubscribed_types=json.dumps([]),
            created_at=now,
            updated_at=now,
        )

        preference.raise_(
            PreferencesCreated(
                preference_id=str(preference.id),
                customer_id=str(customer_id),
                email_enabled=True,
                sms_enabled=False,
                push_enabled=False,
                created_at=now,
            )
        )

        return preference

    # -------------------------------------------------------------------
    # Channel management
    # -------------------------------------------------------------------
    def update_channels(self, email=None, sms=None, push=None):
        """Update channel preferences. Pass None to keep unchanged."""
        if email is None and sms is None and push is None:
            raise ValidationError({"channels": ["At least one channel preference must be provided"]})

        now = datetime.now(UTC)

        if email is not None:
            self.email_enabled = email
        if sms is not None:
            self.sms_enabled = sms
        if push is not None:
            self.push_enabled = push
        self.updated_at = now

        self.raise_(
            ChannelsUpdated(
                preference_id=str(self.id),
                customer_id=str(self.customer_id),
                email_enabled=self.email_enabled,
                sms_enabled=self.sms_enabled,
                push_enabled=self.push_enabled,
                updated_at=now,
            )
        )

    # -------------------------------------------------------------------
    # Quiet hours
    # -------------------------------------------------------------------
    def set_quiet_hours(self, start, end):
        """Set do-not-disturb window. Both start and end required."""
        if not start or not end:
            raise ValidationError({"quiet_hours": ["Both start and end times are required"]})

        # Basic format validation (HH:MM)
        for label, value in [("start", start), ("end", end)]:
            parts = value.split(":")
            if len(parts) != 2:
                raise ValidationError({f"quiet_hours_{label}": [f"Invalid time format: {value}. Use HH:MM"]})
            try:
                hour, minute = int(parts[0]), int(parts[1])
                if not (0 <= hour <= 23 and 0 <= minute <= 59):
                    raise ValueError
            except ValueError:
                raise ValidationError({f"quiet_hours_{label}": [f"Invalid time format: {value}. Use HH:MM"]}) from None

        now = datetime.now(UTC)
        self.quiet_hours_start = start
        self.quiet_hours_end = end
        self.updated_at = now

        self.raise_(
            QuietHoursSet(
                preference_id=str(self.id),
                customer_id=str(self.customer_id),
                start=start,
                end=end,
                updated_at=now,
            )
        )

    def clear_quiet_hours(self):
        """Remove the quiet hours window."""
        now = datetime.now(UTC)
        self.quiet_hours_start = None
        self.quiet_hours_end = None
        self.updated_at = now

        self.raise_(
            QuietHoursCleared(
                preference_id=str(self.id),
                customer_id=str(self.customer_id),
                cleared_at=now,
            )
        )

    # -------------------------------------------------------------------
    # Per-type unsubscribe
    # -------------------------------------------------------------------
    def unsubscribe_from(self, notification_type):
        """Unsubscribe from a specific notification type."""
        types = json.loads(self.unsubscribed_types) if self.unsubscribed_types else []

        if notification_type in types:
            raise ValidationError({"unsubscribed_types": [f"Already unsubscribed from {notification_type}"]})

        types.append(notification_type)
        now = datetime.now(UTC)
        self.unsubscribed_types = json.dumps(types)
        self.updated_at = now

        self.raise_(
            TypeUnsubscribed(
                preference_id=str(self.id),
                customer_id=str(self.customer_id),
                notification_type=notification_type,
                unsubscribed_at=now,
            )
        )

    def resubscribe_to(self, notification_type):
        """Resubscribe to a previously unsubscribed notification type."""
        types = json.loads(self.unsubscribed_types) if self.unsubscribed_types else []

        if notification_type not in types:
            raise ValidationError({"unsubscribed_types": [f"Not currently unsubscribed from {notification_type}"]})

        types.remove(notification_type)
        now = datetime.now(UTC)
        self.unsubscribed_types = json.dumps(types)
        self.updated_at = now

        self.raise_(
            TypeResubscribed(
                preference_id=str(self.id),
                customer_id=str(self.customer_id),
                notification_type=notification_type,
                resubscribed_at=now,
            )
        )

    # -------------------------------------------------------------------
    # Query helpers
    # -------------------------------------------------------------------
    def is_subscribed_to(self, notification_type):
        """Check if the customer is subscribed to a notification type."""
        types = json.loads(self.unsubscribed_types) if self.unsubscribed_types else []
        return notification_type not in types

    def get_enabled_channels(self):
        """Return list of enabled channel strings."""
        channels = []
        if self.email_enabled:
            channels.append("Email")
        if self.sms_enabled:
            channels.append("SMS")
        if self.push_enabled:
            channels.append("Push")
        return channels
