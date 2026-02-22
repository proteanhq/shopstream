"""Domain events for the Notification aggregate."""

from notifications.domain import notifications
from protean.fields import DateTime, Identifier, Integer, String


@notifications.event(part_of="Notification")
class NotificationCreated:
    """A notification was created and queued for dispatch."""

    __version__ = "v1"

    notification_id: Identifier(required=True)
    recipient_id: Identifier(required=True)
    recipient_type: String(required=True)
    notification_type: String(required=True)
    channel: String(required=True)
    subject: String()
    template_name: String()
    source_event_type: String()
    scheduled_for: DateTime()
    created_at: DateTime(required=True)


@notifications.event(part_of="Notification")
class NotificationSent:
    """A notification was sent to the channel adapter."""

    __version__ = "v1"

    notification_id: Identifier(required=True)
    recipient_id: Identifier(required=True)
    channel: String(required=True)
    sent_at: DateTime(required=True)


@notifications.event(part_of="Notification")
class NotificationDelivered:
    """A notification was confirmed delivered to the recipient."""

    __version__ = "v1"

    notification_id: Identifier(required=True)
    recipient_id: Identifier(required=True)
    channel: String(required=True)
    delivered_at: DateTime(required=True)


@notifications.event(part_of="Notification")
class NotificationFailed:
    """A notification failed to send or deliver."""

    __version__ = "v1"

    notification_id: Identifier(required=True)
    recipient_id: Identifier(required=True)
    channel: String(required=True)
    reason: String(required=True)
    retry_count: Integer(required=True)
    max_retries: Integer(required=True)
    failed_at: DateTime(required=True)


@notifications.event(part_of="Notification")
class NotificationBounced:
    """A notification bounced (permanent delivery failure)."""

    __version__ = "v1"

    notification_id: Identifier(required=True)
    recipient_id: Identifier(required=True)
    channel: String(required=True)
    reason: String(required=True)
    bounced_at: DateTime(required=True)


@notifications.event(part_of="Notification")
class NotificationCancelled:
    """A pending notification was cancelled."""

    __version__ = "v1"

    notification_id: Identifier(required=True)
    recipient_id: Identifier(required=True)
    channel: String(required=True)
    reason: String(required=True)
    cancelled_at: DateTime(required=True)


@notifications.event(part_of="Notification")
class NotificationRetried:
    """A failed notification was retried."""

    __version__ = "v1"

    notification_id: Identifier(required=True)
    recipient_id: Identifier(required=True)
    channel: String(required=True)
    retry_count: Integer(required=True)
    retried_at: DateTime(required=True)
