"""NotificationLog — full audit trail of all notifications."""

from datetime import datetime
from typing import Any

from protean.core.projector import on
from protean.fields import DateTime, Identifier, Integer, String
from protean.utils.globals import current_domain

from notifications.domain import notifications
from notifications.notification.events import (
    NotificationBounced,
    NotificationCancelled,
    NotificationCreated,
    NotificationDelivered,
    NotificationFailed,
    NotificationRetried,
    NotificationSent,
)
from notifications.notification.notification import Notification


@notifications.projection
class NotificationLog:
    notification_id: str = Identifier(identifier=True, required=True)
    recipient_id: str = Identifier(required=True)
    recipient_type: str = String(required=True)
    notification_type: str = String(required=True)
    channel: str = String(required=True)
    subject: str | None = String(max_length=500)
    status: str = String(required=True)
    template_name: str | None = String(max_length=200)
    source_event_type: str | None = String(max_length=200)
    failure_reason: str | None = String(max_length=500)
    retry_count: int = Integer(default=0)
    scheduled_for: datetime | None = DateTime()
    created_at: datetime | None = DateTime()
    sent_at: datetime | None = DateTime()
    delivered_at: datetime | None = DateTime()
    updated_at: datetime | None = DateTime()


@notifications.projector(projector_for=NotificationLog, aggregates=[Notification])
class NotificationLogProjector:
    @on(NotificationCreated)
    def on_notification_created(self, event: NotificationCreated) -> None:
        current_domain.repository_for(NotificationLog).add(
            NotificationLog(
                notification_id=event.notification_id,
                recipient_id=event.recipient_id,
                recipient_type=event.recipient_type,
                notification_type=event.notification_type,
                channel=event.channel,
                subject=event.subject,
                status="Pending",
                template_name=event.template_name,
                source_event_type=event.source_event_type,
                scheduled_for=event.scheduled_for,
                created_at=event.created_at,
                updated_at=event.created_at,
            )
        )

    def _update_log(self, notification_id: str, **fields: Any) -> None:
        repo = current_domain.repository_for(NotificationLog)
        log = repo.get_or_none(notification_id)
        if log is None:
            return
        for key, value in fields.items():
            setattr(log, key, value)
        repo.add(log)

    @on(NotificationSent)
    def on_notification_sent(self, event: NotificationSent) -> None:
        self._update_log(
            event.notification_id,
            status="Sent",
            sent_at=event.sent_at,
            updated_at=event.sent_at,
        )

    @on(NotificationDelivered)
    def on_notification_delivered(self, event: NotificationDelivered) -> None:
        self._update_log(
            event.notification_id,
            status="Delivered",
            delivered_at=event.delivered_at,
            updated_at=event.delivered_at,
        )

    @on(NotificationFailed)
    def on_notification_failed(self, event: NotificationFailed) -> None:
        self._update_log(
            event.notification_id,
            status="Failed",
            failure_reason=event.reason,
            retry_count=event.retry_count,
            updated_at=event.failed_at,
        )

    @on(NotificationBounced)
    def on_notification_bounced(self, event: NotificationBounced) -> None:
        self._update_log(
            event.notification_id,
            status="Bounced",
            failure_reason=event.reason,
            updated_at=event.bounced_at,
        )

    @on(NotificationCancelled)
    def on_notification_cancelled(self, event: NotificationCancelled) -> None:
        self._update_log(
            event.notification_id,
            status="Cancelled",
            failure_reason=event.reason,
            updated_at=event.cancelled_at,
        )

    @on(NotificationRetried)
    def on_notification_retried(self, event: NotificationRetried) -> None:
        self._update_log(
            event.notification_id,
            status="Pending",
            retry_count=event.retry_count,
            updated_at=event.retried_at,
        )
