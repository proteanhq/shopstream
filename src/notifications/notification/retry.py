"""RetryNotification command + handler — retry a failed notification."""

from notifications.domain import notifications
from notifications.notification.notification import Notification
from protean.fields import Identifier
from protean.utils.globals import current_domain
from protean.utils.mixins import handle


@notifications.command(part_of="Notification")
class RetryNotification:
    """Request to retry a failed notification."""

    notification_id: Identifier(required=True)


@notifications.command_handler(part_of=Notification)
class RetryNotificationHandler:
    @handle(RetryNotification)
    def retry_notification(self, command: RetryNotification):
        repo = current_domain.repository_for(Notification)
        notification = repo.get(command.notification_id)
        notification.retry()
        repo.add(notification)
