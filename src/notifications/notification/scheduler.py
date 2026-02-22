"""ProcessScheduledNotifications command + handler — dispatch due notifications.

This handler is invoked by a background job or cron to dispatch
notifications whose scheduled_for time has passed.
"""

from datetime import UTC, datetime

import structlog
from notifications.channel import get_channel
from notifications.domain import notifications
from notifications.notification.dispatch import _dispatch_via_channel
from notifications.notification.notification import Notification, NotificationStatus
from protean.fields import DateTime
from protean.utils.globals import current_domain
from protean.utils.mixins import handle

logger = structlog.get_logger(__name__)


@notifications.command(part_of="Notification")
class ProcessScheduledNotifications:
    """Request to process all due scheduled notifications."""

    as_of: DateTime()  # Optional: process as of this time (defaults to now)


@notifications.command_handler(part_of=Notification)
class ProcessScheduledNotificationsHandler:
    @handle(ProcessScheduledNotifications)
    def process_scheduled(self, command: ProcessScheduledNotifications):
        as_of = command.as_of or datetime.now(UTC)
        repo = current_domain.repository_for(Notification)

        # Find pending notifications with scheduled_for <= now
        try:
            pending = repo._dao.query.filter(status=NotificationStatus.PENDING.value).all().items
        except Exception:
            logger.info("No pending notifications found")
            return

        dispatched_count = 0
        for notification in pending:
            # Skip notifications that aren't due yet
            if notification.scheduled_for is None:
                continue

            # Normalize timezone awareness for comparison
            sched = notification.scheduled_for
            if sched.tzinfo is not None and as_of.tzinfo is None:
                sched = sched.replace(tzinfo=None)
            elif sched.tzinfo is None and as_of.tzinfo is not None:
                sched = sched.replace(tzinfo=as_of.tzinfo)

            if sched > as_of:
                continue

            try:
                adapter = get_channel(notification.channel)
                result = _dispatch_via_channel(adapter, notification)

                if result.get("status") == "sent":
                    notification.mark_sent()
                else:
                    notification.mark_failed(result.get("error", "Unknown dispatch error"))
                dispatched_count += 1
            except Exception as e:
                notification.mark_failed(str(e))
                logger.error(
                    "Scheduled notification dispatch failed",
                    notification_id=str(notification.id),
                    error=str(e),
                )

            repo.add(notification)

        logger.info(
            "Scheduled notifications processed",
            dispatched=dispatched_count,
            as_of=str(as_of),
        )
