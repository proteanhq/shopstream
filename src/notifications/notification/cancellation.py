"""CancelNotification command + handler — cancel a pending notification."""

from notifications.domain import notifications
from notifications.notification.notification import Notification
from protean.fields import Identifier, String
from protean.utils.globals import current_domain
from protean.utils.mixins import handle


@notifications.command(part_of="Notification")
class CancelNotification:
    """Request to cancel a pending or scheduled notification."""

    notification_id: Identifier(required=True)
    reason: String(required=True, max_length=500)


@notifications.command_handler(part_of=Notification)
class CancelNotificationHandler:
    @handle(CancelNotification)
    def cancel_notification(self, command: CancelNotification):
        repo = current_domain.repository_for(Notification)
        notification = repo.get(command.notification_id)
        notification.cancel(command.reason)
        repo.add(notification)
