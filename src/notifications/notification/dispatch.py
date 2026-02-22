"""Internal dispatch handler — sends notifications via channel adapters.

Reacts to NotificationCreated events and dispatches via the appropriate
channel adapter (email, SMS, push, Slack). Updates the notification
status to SENT or FAILED based on the result.
"""

import structlog
from notifications.channel import get_channel
from notifications.domain import notifications
from notifications.notification.events import NotificationCreated
from notifications.notification.notification import (
    Notification,
    NotificationChannel,
    NotificationStatus,
)
from protean.utils.globals import current_domain
from protean.utils.mixins import handle

logger = structlog.get_logger(__name__)


@notifications.event_handler(part_of=Notification)
class NotificationDispatcher:
    """Dispatches notifications via channel adapters when they are created."""

    @handle(NotificationCreated)
    def on_notification_created(self, event: NotificationCreated) -> None:
        """Dispatch the notification via its channel adapter."""
        # Skip scheduled notifications — they'll be dispatched by the scheduler
        if event.scheduled_for is not None:
            logger.info(
                "Notification is scheduled, skipping immediate dispatch",
                notification_id=str(event.notification_id),
                scheduled_for=str(event.scheduled_for),
            )
            return

        repo = current_domain.repository_for(Notification)

        try:
            notification = repo.get(event.notification_id)
        except Exception:
            logger.error(
                "Failed to load notification for dispatch",
                notification_id=str(event.notification_id),
            )
            return

        # Only dispatch PENDING notifications
        if NotificationStatus(notification.status) != NotificationStatus.PENDING:
            logger.info(
                "Notification not in PENDING status, skipping dispatch",
                notification_id=str(event.notification_id),
                status=notification.status,
            )
            return

        try:
            adapter = get_channel(notification.channel)
            result = _dispatch_via_channel(adapter, notification)

            if result.get("status") == "sent":
                notification.mark_sent()
            else:
                notification.mark_failed(result.get("error", "Unknown dispatch error"))
        except Exception as e:
            notification.mark_failed(str(e))
            logger.error(
                "Notification dispatch failed",
                notification_id=str(notification.id),
                error=str(e),
            )

        repo.add(notification)


def _dispatch_via_channel(adapter, notification: Notification) -> dict:
    """Route dispatch to the correct adapter method based on channel."""
    channel = notification.channel

    if channel == NotificationChannel.EMAIL.value:
        return adapter.send(
            to=str(notification.recipient_id),
            subject=notification.subject or "",
            body=notification.body,
        )
    elif channel == NotificationChannel.SMS.value:
        return adapter.send(
            to=str(notification.recipient_id),
            body=notification.body,
        )
    elif channel == NotificationChannel.PUSH.value:
        return adapter.send(
            device_token=str(notification.recipient_id),
            title=notification.subject or "",
            body=notification.body,
        )
    elif channel == NotificationChannel.SLACK.value:
        return adapter.send(
            channel="#operations",
            message=notification.body,
        )
    else:
        return {"status": "failed", "error": f"Unknown channel: {channel}"}
