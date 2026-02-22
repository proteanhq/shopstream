"""FailedNotifications — queue of failed notifications for retry/investigation."""

from notifications.domain import notifications
from notifications.notification.events import (
    NotificationFailed,
    NotificationRetried,
    NotificationSent,
)
from notifications.notification.notification import Notification
from protean.core.projector import on
from protean.fields import DateTime, Identifier, Integer, String
from protean.utils.globals import current_domain


@notifications.projection
class FailedNotifications:
    notification_id: Identifier(identifier=True, required=True)
    recipient_id: Identifier(required=True)
    notification_type: String(required=True)
    channel: String(required=True)
    failure_reason: String(max_length=500)
    retry_count: Integer(default=0)
    max_retries: Integer(default=3)
    failed_at: DateTime()


@notifications.projector(projector_for=FailedNotifications, aggregates=[Notification])
class FailedNotificationsProjector:
    @on(NotificationFailed)
    def on_notification_failed(self, event):
        repo = current_domain.repository_for(FailedNotifications)

        # Look up the notification for type info
        try:
            notif = current_domain.repository_for(Notification).get(event.notification_id)
            notification_type = notif.notification_type
        except Exception:
            notification_type = "Unknown"

        try:
            failed = repo.get(event.notification_id)
            failed.failure_reason = event.reason
            failed.retry_count = event.retry_count
            failed.failed_at = event.failed_at
        except Exception:
            failed = FailedNotifications(
                notification_id=event.notification_id,
                recipient_id=event.recipient_id,
                notification_type=notification_type,
                channel=event.channel,
                failure_reason=event.reason,
                retry_count=event.retry_count,
                max_retries=event.max_retries,
                failed_at=event.failed_at,
            )

        repo.add(failed)

    @on(NotificationRetried)
    def on_notification_retried(self, event):
        """Remove from failed queue when retried (it goes back to pending)."""
        repo = current_domain.repository_for(FailedNotifications)
        try:
            failed = repo.get(event.notification_id)
            repo._dao.delete(failed)
        except Exception:
            pass

    @on(NotificationSent)
    def on_notification_sent(self, event):
        """Remove from failed queue when successfully sent."""
        repo = current_domain.repository_for(FailedNotifications)
        try:
            failed = repo.get(event.notification_id)
            repo._dao.delete(failed)
        except Exception:
            pass
