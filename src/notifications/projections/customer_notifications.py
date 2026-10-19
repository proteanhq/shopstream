"""CustomerNotifications — per-customer notification feed (recent history)."""

from datetime import datetime

from protean.core.projector import on
from protean.fields import DateTime, Identifier, String
from protean.utils.globals import current_domain

from notifications.domain import notifications
from notifications.notification.events import (
    NotificationCreated,
    NotificationDelivered,
    NotificationFailed,
    NotificationSent,
)
from notifications.notification.notification import Notification


@notifications.projection
class CustomerNotifications:
    notification_id: str = Identifier(identifier=True, required=True)
    customer_id: str = Identifier(required=True)
    notification_type: str = String(required=True)
    channel: str = String(required=True)
    subject: str | None = String(max_length=500)
    status: str = String(required=True)
    created_at: datetime | None = DateTime()
    updated_at: datetime | None = DateTime()


@notifications.projector(projector_for=CustomerNotifications, aggregates=[Notification])
class CustomerNotificationsProjector:
    @on(NotificationCreated)
    def on_notification_created(self, event: NotificationCreated) -> None:
        # Only track customer notifications (skip internal)
        if event.recipient_type != "Customer":
            return

        current_domain.repository_for(CustomerNotifications).add(
            CustomerNotifications(
                notification_id=event.notification_id,
                customer_id=event.recipient_id,
                notification_type=event.notification_type,
                channel=event.channel,
                subject=event.subject,
                status="Pending",
                created_at=event.created_at,
                updated_at=event.created_at,
            )
        )

    def _update_status(self, notification_id: str, status: str, updated_at: datetime | None) -> None:
        repo = current_domain.repository_for(CustomerNotifications)
        cn = repo.get_or_none(notification_id)
        if cn is None:
            return
        cn.status = status
        cn.updated_at = updated_at
        repo.add(cn)

    @on(NotificationSent)
    def on_notification_sent(self, event: NotificationSent) -> None:
        self._update_status(event.notification_id, "Sent", event.sent_at)

    @on(NotificationDelivered)
    def on_notification_delivered(self, event: NotificationDelivered) -> None:
        self._update_status(event.notification_id, "Delivered", event.delivered_at)

    @on(NotificationFailed)
    def on_notification_failed(self, event: NotificationFailed) -> None:
        self._update_status(event.notification_id, "Failed", event.failed_at)
