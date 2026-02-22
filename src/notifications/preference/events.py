"""Domain events for the NotificationPreference aggregate."""

from notifications.domain import notifications
from protean.fields import Boolean, DateTime, Identifier, String


@notifications.event(part_of="NotificationPreference")
class PreferencesCreated:
    """Default notification preferences were created for a customer."""

    __version__ = "v1"

    preference_id: Identifier(required=True)
    customer_id: Identifier(required=True)
    email_enabled: Boolean(required=True)
    sms_enabled: Boolean(required=True)
    push_enabled: Boolean(required=True)
    created_at: DateTime(required=True)


@notifications.event(part_of="NotificationPreference")
class ChannelsUpdated:
    """A customer's notification channel preferences were changed."""

    __version__ = "v1"

    preference_id: Identifier(required=True)
    customer_id: Identifier(required=True)
    email_enabled: Boolean(required=True)
    sms_enabled: Boolean(required=True)
    push_enabled: Boolean(required=True)
    updated_at: DateTime(required=True)


@notifications.event(part_of="NotificationPreference")
class QuietHoursSet:
    """A customer set their do-not-disturb window."""

    __version__ = "v1"

    preference_id: Identifier(required=True)
    customer_id: Identifier(required=True)
    start: String(required=True)
    end: String(required=True)
    updated_at: DateTime(required=True)


@notifications.event(part_of="NotificationPreference")
class QuietHoursCleared:
    """A customer cleared their do-not-disturb window."""

    __version__ = "v1"

    preference_id: Identifier(required=True)
    customer_id: Identifier(required=True)
    cleared_at: DateTime(required=True)


@notifications.event(part_of="NotificationPreference")
class TypeUnsubscribed:
    """A customer unsubscribed from a specific notification type."""

    __version__ = "v1"

    preference_id: Identifier(required=True)
    customer_id: Identifier(required=True)
    notification_type: String(required=True)
    unsubscribed_at: DateTime(required=True)


@notifications.event(part_of="NotificationPreference")
class TypeResubscribed:
    """A customer resubscribed to a previously unsubscribed notification type."""

    __version__ = "v1"

    preference_id: Identifier(required=True)
    customer_id: Identifier(required=True)
    notification_type: String(required=True)
    resubscribed_at: DateTime(required=True)
