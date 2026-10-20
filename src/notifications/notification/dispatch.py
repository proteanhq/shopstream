"""Notification dispatch: claim, send through the channel, then record the result.

A send and its database write never share a transaction. On Postgres a unit
of work is one real transaction that opens at the first repository access and
holds a pooled connection until it ends, so a channel call made after a read
or write would hold that connection and any row locks for the length of the
call.

``NotificationDispatcher`` handles the two steps in separate methods, and each
method runs in its own unit of work:

1. ``NotificationDispatchRequested`` → claim. Loads the notification and, while
   it is still PENDING, moves it to DISPATCHING, which raises
   ``NotificationDispatchStarted``. A cancelled notification, or one already
   claimed by an earlier request, is skipped. The claim commits before the send.
2. ``NotificationDispatchStarted`` → send. The event carries everything the
   send needs, so this method reaches no repository before the send and its
   unit of work has no session while the channel is called. It then processes
   ``RecordDispatchResult``, whose handler marks the notification SENT or FAILED
   while it is still DISPATCHING.

The record step joins the send method's unit of work, because Protean has no
way to commit one step of a handler on its own (proteanhq/protean#1915). A
version conflict found at commit makes Protean retry the whole send method, so
the channel is called again. On Postgres the conflict is found at save time,
inside the record step, and its own retry then loses the result without an
error (proteanhq/protean#1914). Only the send method and the stale-dispatch
sweep (``ExpireStaleDispatches``) write to a DISPATCHING notification, so such
a conflict means two workers handled the same event, or a result arrived just
as the sweep expired the notification.

Each result names the claim it belongs to by the claim's ``retry_count``. A
late result from a claim that expired and was retried is not recorded on the
newer claim.

The send step cannot read the notification without opening a transaction, so
it cannot see that a claim has expired. Instead it refuses to send a claim
older than ``SEND_DEADLINE``, which is shorter than the sweep's
``STALE_DISPATCH_AFTER``. A claim the sweep can expire, and so one that can
have been retried, is never sent. This holds only because the claim time, the
send deadline and the sweep all read the domain clock, and the sweep never
looks past it.

A redelivered ``NotificationDispatchStarted``, after a crash between the send
and the record, also sends again within that deadline. Closing that gap needs
an idempotency key that the channel provider honours.

When the adapter raises ``ChannelUnavailableError`` (the provider cannot be
reached), the send step records nothing and lets the error propagate. The
notification stays DISPATCHING. Under the engine, the subscription tries the
``NotificationDispatchStarted`` message up to ``max_retries`` (3) times in all,
and repeated failures open its circuit breaker
(``[server.subscriptions.NotificationDispatcher]`` in ``domain.toml``). A
message that fails every attempt goes to the dead-letter queue. A retried
message can also be lost before that: an engine restart leaves it pending under
the old consumer name, and a stream trim can delete it. Either way the sweep
marks the notification FAILED once its claim is stale, and a retry sends it
again. A retry that lands after the send deadline sends nothing. Under sync
processing (the test and memory overlays) the error reaches whoever created
the notification, and nothing retries it until the sweep.
"""

from datetime import timedelta
from typing import Any

import structlog
from protean.fields import Identifier, Integer, Text
from protean.utils.globals import current_domain
from protean.utils.mixins import handle

from notifications.channel import ChannelAdapter, get_channel
from notifications.channel.email_port import EmailPort
from notifications.channel.errors import ChannelUnavailableError
from notifications.channel.push_port import PushPort
from notifications.channel.slack_port import SlackPort
from notifications.channel.sms_port import SMSPort
from notifications.channel.transaction_guard import SendInsideTransactionError
from notifications.domain import notifications
from notifications.notification.events import NotificationDispatchRequested, NotificationDispatchStarted
from notifications.notification.notification import (
    Notification,
    NotificationChannel,
    NotificationStatus,
)
from notifications.notification.scheduler import as_utc, clock_now

logger = structlog.get_logger(__name__)

# Shorter than STALE_DISPATCH_AFTER by more than a send takes, so a send that
# starts inside the deadline records its result before the sweep can expire it.
SEND_DEADLINE = timedelta(minutes=10)


@notifications.command(part_of="Notification")
class RecordDispatchResult:
    """Record the outcome of one channel send."""

    notification_id: str = Identifier(required=True)
    retry_count: int = Integer(required=True)  # The claim's retry_count, naming the attempt this result is for
    failure_reason: str | None = Text()  # None means the send succeeded


@notifications.command_handler(part_of=Notification)
class RecordDispatchResultHandler:
    @handle(RecordDispatchResult)
    def record_dispatch_result(self, command: RecordDispatchResult) -> None:
        repo = current_domain.repository_for(Notification)
        notification = repo.get_or_none(command.notification_id)
        if notification is None:
            logger.error(
                "Notification not found when recording dispatch result",
                notification_id=str(command.notification_id),
            )
            return

        # The send ran without reading the notification. A redelivered send has
        # already been recorded, and an expired dispatch was marked FAILED.
        if NotificationStatus(notification.status) != NotificationStatus.DISPATCHING:
            logger.info(
                "Notification not in DISPATCHING status, dispatch result not recorded",
                notification_id=str(command.notification_id),
                status=notification.status,
            )
            return

        # A claim that expired and was retried leaves the notification
        # DISPATCHING again under a higher retry_count. This result belongs to
        # the earlier claim, so it must not settle the newer one.
        if notification.retry_count != command.retry_count:
            logger.info(
                "Dispatch result belongs to an earlier claim, not recorded",
                notification_id=str(command.notification_id),
                result_retry_count=command.retry_count,
                claim_retry_count=notification.retry_count,
            )
            return

        if command.failure_reason is None:
            notification.mark_sent()
        else:
            notification.mark_failed(command.failure_reason)
        repo.add(notification)


@notifications.event_handler(part_of=Notification)
class NotificationDispatcher:
    """Claims a notification when its dispatch is requested, then sends it."""

    @handle(NotificationDispatchRequested)
    def on_dispatch_requested(self, event: NotificationDispatchRequested) -> None:
        """Claim the notification for one send, if it is still PENDING."""
        repo = current_domain.repository_for(Notification)
        notification = repo.get_or_none(event.notification_id)
        if notification is None:
            logger.error(
                "Notification not found when claiming it for dispatch",
                notification_id=str(event.notification_id),
            )
            return

        if NotificationStatus(notification.status) != NotificationStatus.PENDING:
            logger.info(
                "Notification not in PENDING status, dispatch not claimed",
                notification_id=str(event.notification_id),
                status=notification.status,
            )
            return

        notification.claim_dispatch(clock_now())
        repo.add(notification)

    @handle(NotificationDispatchStarted)
    def on_dispatch_started(self, event: NotificationDispatchStarted) -> None:
        """Send through the channel adapter, then record the result.

        The send runs before any repository access, so no transaction is open
        during it. ``RecordDispatchResult`` opens the session afterwards. A
        claim older than ``SEND_DEADLINE`` is not sent and records nothing; the
        sweep marks it FAILED.

        A failed send or any other adapter exception is recorded as FAILED.
        ``ChannelUnavailableError`` and ``SendInsideTransactionError`` propagate
        and record nothing.
        """
        if clock_now() - as_utc(event.started_at) >= SEND_DEADLINE:
            logger.warning(
                "Dispatch claim is past its send deadline, not sent",
                notification_id=str(event.notification_id),
                started_at=str(event.started_at),
            )
            return

        try:
            adapter = get_channel(event.channel)
            result = _dispatch_via_channel(adapter, event)
            # None tells RecordDispatchResult the send succeeded, so a failure
            # must always carry a non-empty reason.
            failure_reason = (
                None if result.get("status") == "sent" else (str(result.get("error") or "") or "Unknown dispatch error")
            )
        except SendInsideTransactionError:
            # A wiring bug in this code, not a channel failure: surface it
            # instead of recording the notification as FAILED.
            raise
        except ChannelUnavailableError:
            # An outage is transient: leave the notification DISPATCHING and fail
            # the handler, so the engine retries the message and the failure
            # counts towards the circuit breaker's threshold.
            logger.warning(
                "Notification channel unavailable, dispatch will be retried",
                notification_id=str(event.notification_id),
                channel=event.channel,
            )
            raise
        except Exception as e:
            failure_reason = str(e) or type(e).__name__
            logger.error(
                "Notification dispatch failed",
                notification_id=str(event.notification_id),
                error=failure_reason,
            )

        current_domain.process(
            RecordDispatchResult(
                notification_id=event.notification_id,
                retry_count=event.retry_count,
                failure_reason=failure_reason,
            ),
            asynchronous=False,
        )


def _dispatch_via_channel(adapter: ChannelAdapter, request: NotificationDispatchStarted) -> dict[str, Any]:
    """Route dispatch to the correct adapter method based on channel.

    ``get_channel`` builds the adapter for the same channel string, so each
    branch's adapter is always that channel's port.
    """
    channel = request.channel

    if channel == NotificationChannel.EMAIL.value:
        assert isinstance(adapter, EmailPort)
        return adapter.send(
            to=str(request.recipient_id),
            subject=request.subject or "",
            body=request.body,
        )
    elif channel == NotificationChannel.SMS.value:
        assert isinstance(adapter, SMSPort)
        return adapter.send(
            to=str(request.recipient_id),
            body=request.body,
        )
    elif channel == NotificationChannel.PUSH.value:
        assert isinstance(adapter, PushPort)
        return adapter.send(
            device_token=str(request.recipient_id),
            title=request.subject or "",
            body=request.body,
        )
    elif channel == NotificationChannel.SLACK.value:
        assert isinstance(adapter, SlackPort)
        return adapter.send(
            channel="#operations",
            message=request.body,
        )
    else:
        return {"status": "failed", "error": f"Unknown channel: {channel}"}
