"""ExpireStaleDispatches command + handler — fail notifications stuck in DISPATCHING.

A notification stays DISPATCHING when its send never records a result, for
example when ``NotificationDispatchStarted`` is dead-lettered. This handler,
run by the same background job as ``ProcessScheduledNotifications``, marks
each one FAILED. It never sends: the send may already have reached the
recipient, so a retry decides whether to send again.
"""

from datetime import datetime, timedelta

import structlog
from protean.fields import DateTime
from protean.utils.globals import current_domain
from protean.utils.mixins import handle
from protean.utils.processing import Priority, processing_priority

from notifications.domain import notifications
from notifications.notification.notification import Notification, NotificationStatus
from notifications.notification.scheduler import as_utc

logger = structlog.get_logger(__name__)

# Much longer than any send takes. A result recorded at the moment the sweep
# expires the same notification makes one of the two commits fail. If the
# record step loses, Protean retries the whole send (proteanhq/protean#1915),
# or on Postgres drops the result (proteanhq/protean#1914).
STALE_DISPATCH_AFTER = timedelta(minutes=15)


@notifications.command(part_of="Notification")
class ExpireStaleDispatches:
    """Request to fail notifications that have been DISPATCHING for too long."""

    as_of: datetime | None = DateTime()  # Optional: expire as of this time (defaults to the domain clock)


@notifications.command_handler(part_of=Notification)
class ExpireStaleDispatchesHandler:
    @handle(ExpireStaleDispatches)
    def expire_stale_dispatches(self, command: ExpireStaleDispatches) -> None:
        with processing_priority(Priority.LOW):
            cutoff = as_utc(command.as_of or current_domain.clock.now()) - STALE_DISPATCH_AFTER
            repo = current_domain.repository_for(Notification)

            # The claim sets updated_at, and nothing else writes a DISPATCHING
            # notification before its result, so updated_at is the claim time.
            stale = (
                repo.query.filter(status=NotificationStatus.DISPATCHING.value, updated_at__lte=cutoff)
                .limit(None)
                .all()
                .items
            )

            for notification in stale:
                notification.expire_dispatch()
                repo.add(notification)

            logger.info(
                "Stale dispatches expired",
                expired=len(stale),
                cutoff=str(cutoff),
            )
