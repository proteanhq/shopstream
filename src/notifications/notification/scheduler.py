"""ProcessScheduledNotifications command + handler — release due notifications.

This handler is invoked by a background job or cron. It selects the PENDING
notifications whose scheduled_for time has passed and requests their dispatch.
It never calls a channel itself: each request raises
``NotificationDispatchRequested``, and ``NotificationDispatcher`` sends it
after this transaction commits, outside any transaction.
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


@notifications.command(part_of="Notification")
class ProcessScheduledNotifications:
    """Request to process all due scheduled notifications."""

    as_of: datetime | None = DateTime()  # Optional: process as of this time (defaults to the domain clock)


@notifications.command_handler(part_of=Notification)
class ProcessScheduledNotificationsHandler:
    @handle(ProcessScheduledNotifications)
    def process_scheduled(self, command: ProcessScheduledNotifications) -> None:
        with processing_priority(Priority.LOW):
            as_of = command.as_of or current_domain.clock.now()
            # Stored times are UTC, and the memory provider compares datetimes as
            # strings (proteanhq/protean#1900), so the cutoff must be in UTC too.
            # A naive as_of is taken to be UTC.
            as_of = (as_of if as_of.tzinfo else as_of.replace(tzinfo=UTC)).astimezone(UTC)
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
