"""Domain events for the NotificationPreference aggregate."""

from datetime import datetime

from protean.fields import Boolean, DateTime, Identifier, String

from notifications.domain import notifications


@notifications.event(part_of="NotificationPreference")
class PreferencesCreated:
    """Default notification preferences were created for a customer."""

    preference_id: str = Identifier(required=True)
    customer_id: str = Identifier(required=True)
    email_enabled: bool = Boolean(required=True)
    sms_enabled: bool = Boolean(required=True)
    push_enabled: bool = Boolean(required=True)
    created_at: datetime = DateTime(required=True)


@notifications.event(part_of="NotificationPreference")
class ChannelsUpdated:
    """A customer's notification channel preferences were changed."""

    preference_id: str = Identifier(required=True)
    customer_id: str = Identifier(required=True)
    email_enabled: bool = Boolean(required=True)
    sms_enabled: bool = Boolean(required=True)
    push_enabled: bool = Boolean(required=True)
    updated_at: datetime = DateTime(required=True)


@notifications.event(part_of="NotificationPreference")
class QuietHoursSet:
    """A customer set their do-not-disturb window."""

    preference_id: str = Identifier(required=True)
    customer_id: str = Identifier(required=True)
    start: str = String(required=True)
    end: str = String(required=True)
    updated_at: datetime = DateTime(required=True)


@notifications.event(part_of="NotificationPreference")
class QuietHoursCleared:
    """A customer cleared their do-not-disturb window."""

    preference_id: str = Identifier(required=True)
    customer_id: str = Identifier(required=True)
    cleared_at: datetime = DateTime(required=True)


@notifications.event(part_of="NotificationPreference")
class TypeUnsubscribed:
    """A customer unsubscribed from a specific notification type."""

    preference_id: str = Identifier(required=True)
    customer_id: str = Identifier(required=True)
    notification_type: str = String(required=True)
    unsubscribed_at: datetime = DateTime(required=True)


@notifications.event(part_of="NotificationPreference")
class TypeResubscribed:
    """A customer resubscribed to a previously unsubscribed notification type."""

    preference_id: str = Identifier(required=True)
    customer_id: str = Identifier(required=True)
    notification_type: str = String(required=True)
    resubscribed_at: datetime = DateTime(required=True)
