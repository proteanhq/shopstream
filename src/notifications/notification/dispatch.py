"""Notification dispatch: send through the channel, then record the result.

A send and its database write never share a transaction. On Postgres a unit
of work is one real transaction that opens at the first repository access and
holds a pooled connection until it ends, so a channel call made after a read
or write would hold that connection and any row locks for the length of the
call.

``NotificationDispatcher`` reacts to ``NotificationDispatchRequested``, which
carries everything the send needs. It reaches no repository before the send,
so its unit of work has no session while the channel is called. It then
processes ``RecordDispatchResult``, whose handler loads the notification and,
while it is still PENDING, marks it SENT or FAILED.
"""

from typing import Any

import structlog
from protean.fields import Identifier, Text
from protean.utils.globals import current_domain
from protean.utils.mixins import handle

from notifications.channel import ChannelAdapter, get_channel
from notifications.channel.email_port import EmailPort
from notifications.channel.push_port import PushPort
from notifications.channel.slack_port import SlackPort
from notifications.channel.sms_port import SMSPort
from notifications.channel.transaction_guard import SendInsideTransactionError
from notifications.domain import notifications
from notifications.notification.events import NotificationDispatchRequested
from notifications.notification.notification import (
    Notification,
    NotificationChannel,
    NotificationStatus,
)

logger = structlog.get_logger(__name__)


@notifications.command(part_of="Notification")
class RecordDispatchResult:
    """Record the outcome of one channel send."""

    notification_id: str = Identifier(required=True)
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

        # The send ran without reading the notification, so it may have been
        # cancelled or already recorded (a redelivered request) in the meantime.
        if NotificationStatus(notification.status) != NotificationStatus.PENDING:
            logger.info(
                "Notification not in PENDING status, dispatch result not recorded",
                notification_id=str(command.notification_id),
                status=notification.status,
            )
            return

        if command.failure_reason is None:
            notification.mark_sent()
        else:
            notification.mark_failed(command.failure_reason)
        repo.add(notification)


@notifications.event_handler(part_of=Notification)
class NotificationDispatcher:
    """Sends a notification through its channel when its dispatch is requested."""

    @handle(NotificationDispatchRequested)
    def on_dispatch_requested(self, event: NotificationDispatchRequested) -> None:
        """Send through the channel adapter, then record the result.

        The send runs before any repository access, so no transaction is open
        during it. ``RecordDispatchResult`` opens the session afterwards.
        """
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
        except Exception as e:
            failure_reason = str(e) or type(e).__name__
            logger.error(
                "Notification dispatch failed",
                notification_id=str(event.notification_id),
                error=failure_reason,
            )

        current_domain.process(
            RecordDispatchResult(notification_id=event.notification_id, failure_reason=failure_reason),
            asynchronous=False,
        )


def _dispatch_via_channel(adapter: ChannelAdapter, request: NotificationDispatchRequested) -> dict[str, Any]:
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
