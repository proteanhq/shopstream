"""ProcessScheduledNotifications command + handler — release due notifications.

This handler is invoked by a background job or cron. It selects the PENDING
notifications whose scheduled_for time has passed and requests their dispatch.
It never calls a channel itself: each request raises
``NotificationDispatchRequested``, and after this transaction commits
``NotificationDispatcher`` claims the notification and sends it, outside any
transaction. A notification already claimed by another request is skipped.
"""

from datetime import UTC, datetime

import structlog
from protean.fields import DateTime
from protean.utils.globals import current_domain
from protean.utils.mixins import handle
from protean.utils.processing import Priority, processing_priority

from notifications.domain import notifications
from notifications.notification.notification import Notification, NotificationStatus

logger = structlog.get_logger(__name__)


def as_utc(value: datetime) -> datetime:
    """Return ``value`` in UTC, taking a naive datetime to be UTC already.

    Stored times are UTC, and the memory provider compares datetimes as
    strings (proteanhq/protean#1900), so a query cutoff must be in UTC too.
    """
    return (value if value.tzinfo else value.replace(tzinfo=UTC)).astimezone(UTC)


def clock_now() -> datetime:
    """Return the domain clock's time in UTC."""
    return as_utc(current_domain.clock.now())


@notifications.command(part_of="Notification")
class ProcessScheduledNotifications:
    """Request to process all due scheduled notifications."""

    as_of: datetime | None = DateTime()  # Optional: process as of this time (defaults to the domain clock)


@notifications.command_handler(part_of=Notification)
class ProcessScheduledNotificationsHandler:
    @handle(ProcessScheduledNotifications)
    def process_scheduled(self, command: ProcessScheduledNotifications) -> None:
        with processing_priority(Priority.LOW):
            as_of = as_utc(command.as_of) if command.as_of else clock_now()
            repo = current_domain.repository_for(Notification)

            # Load only the due notifications, with no row limit: the query
            # default of 100 rows would leave due notifications behind.
            try:
                pending = (
                    repo.query.filter(status=NotificationStatus.PENDING.value, scheduled_for__lte=as_of)
                    .limit(None)
                    .all()
                    .items
                )
            except Exception:
                logger.info("No pending notifications found")
                return

            requested_count = 0
            for notification in pending:
                notification.request_dispatch()
                repo.add(notification)
                requested_count += 1

            logger.info(
                "Scheduled notifications released for dispatch",
                requested=requested_count,
                as_of=str(as_of),
            )
