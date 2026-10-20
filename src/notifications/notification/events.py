"""Domain events for the Notification aggregate."""

from datetime import datetime

from protean.fields import DateTime, Identifier, Integer, String

from notifications.domain import notifications


@notifications.event(part_of="Notification")
class NotificationCreated:
    """A notification was created and queued for dispatch."""

    notification_id: str = Identifier(required=True)
    recipient_id: str = Identifier(required=True)
    recipient_type: str = String(required=True)
    notification_type: str = String(required=True)
    channel: str = String(required=True)
    subject: str | None = String()
    template_name: str | None = String()
    source_event_type: str | None = String()
    scheduled_for: datetime | None = DateTime()
    created_at: datetime = DateTime(required=True)


@notifications.event(part_of="Notification")
class NotificationSent:
    """A notification was sent to the channel adapter."""

    notification_id: str = Identifier(required=True)
    recipient_id: str = Identifier(required=True)
    channel: str = String(required=True)
    sent_at: datetime = DateTime(required=True)


@notifications.event(part_of="Notification")
class NotificationDelivered:
    """A notification was confirmed delivered to the recipient."""

    notification_id: str = Identifier(required=True)
    recipient_id: str = Identifier(required=True)
    channel: str = String(required=True)
    delivered_at: datetime = DateTime(required=True)


@notifications.event(part_of="Notification")
class NotificationFailed:
    """A notification failed to send or deliver."""

    notification_id: str = Identifier(required=True)
    recipient_id: str = Identifier(required=True)
    channel: str = String(required=True)
    reason: str = String(required=True)
    retry_count: int = Integer(required=True)
    max_retries: int = Integer(required=True)
    failed_at: datetime = DateTime(required=True)


@notifications.event(part_of="Notification")
class NotificationBounced:
    """A notification bounced (permanent delivery failure)."""

    notification_id: str = Identifier(required=True)
    recipient_id: str = Identifier(required=True)
    channel: str = String(required=True)
    reason: str = String(required=True)
    bounced_at: datetime = DateTime(required=True)


@notifications.event(part_of="Notification")
class NotificationCancelled:
    """A pending notification was cancelled."""

    notification_id: str = Identifier(required=True)
    recipient_id: str = Identifier(required=True)
    channel: str = String(required=True)
    reason: str = String(required=True)
    cancelled_at: datetime = DateTime(required=True)


@notifications.event(part_of="Notification")
class NotificationRetried:
    """A failed notification was retried."""

    notification_id: str = Identifier(required=True)
    recipient_id: str = Identifier(required=True)
    channel: str = String(required=True)
    retry_count: int = Integer(required=True)
    retried_at: datetime = DateTime(required=True)
