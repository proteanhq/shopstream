"""NotificationStats — daily counts by notification type and channel."""

from datetime import datetime

from protean.core.projector import on
from protean.fields import DateTime, Integer, String
from protean.utils.globals import current_domain

from notifications.domain import notifications
from notifications.notification.events import NotificationSent
from notifications.notification.notification import Notification


@notifications.projection
class NotificationStats:
    stat_key: str = String(identifier=True, required=True)  # "YYYY-MM-DD:type:channel"
    date: str = String(required=True, max_length=10)
    notification_type: str = String(required=True)
    channel: str = String(required=True)
    count: int = Integer(default=0)
    updated_at: datetime | None = DateTime()


@notifications.projector(projector_for=NotificationStats, aggregates=[Notification])
class NotificationStatsProjector:
    @on(NotificationSent)
    def on_notification_sent(self, event):
        repo = current_domain.repository_for(NotificationStats)

        date_str = event.sent_at.strftime("%Y-%m-%d") if event.sent_at else "unknown"
        # We need the notification type — load from NotificationLog or Notification
        notif = current_domain.repository_for(Notification).get_or_none(event.notification_id)
        notification_type = notif.notification_type if notif is not None else "Unknown"

        stat_key = f"{date_str}:{notification_type}:{event.channel}"

        stat = repo.get_or_none(stat_key)
        if stat is not None:
            stat.count = stat.count + 1
            stat.updated_at = event.sent_at
        else:
            stat = NotificationStats(
                stat_key=stat_key,
                date=date_str,
                notification_type=notification_type,
                channel=event.channel,
                count=1,
                updated_at=event.sent_at,
            )

        repo.add(stat)
