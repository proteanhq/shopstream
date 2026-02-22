"""CustomerNotifications — per-customer notification feed (recent history)."""

from notifications.domain import notifications
from notifications.notification.events import (
    NotificationCreated,
    NotificationDelivered,
    NotificationFailed,
    NotificationSent,
)
from notifications.notification.notification import Notification
from protean.core.projector import on
from protean.fields import DateTime, Identifier, String
from protean.utils.globals import current_domain


@notifications.projection
class CustomerNotifications:
    notification_id: Identifier(identifier=True, required=True)
    customer_id: Identifier(required=True)
    notification_type: String(required=True)
    channel: String(required=True)
    subject: String(max_length=500)
    status: String(required=True)
    created_at: DateTime()
    updated_at: DateTime()


@notifications.projector(projector_for=CustomerNotifications, aggregates=[Notification])
class CustomerNotificationsProjector:
    @on(NotificationCreated)
    def on_notification_created(self, event):
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

    def _update_status(self, notification_id, status, updated_at):
        repo = current_domain.repository_for(CustomerNotifications)
        try:
            cn = repo.get(notification_id)
        except Exception:
            return
        cn.status = status
        cn.updated_at = updated_at
        repo.add(cn)

    @on(NotificationSent)
    def on_notification_sent(self, event):
        self._update_status(event.notification_id, "Sent", event.sent_at)

    @on(NotificationDelivered)
    def on_notification_delivered(self, event):
        self._update_status(event.notification_id, "Delivered", event.delivered_at)

    @on(NotificationFailed)
    def on_notification_failed(self, event):
        self._update_status(event.notification_id, "Failed", event.failed_at)
