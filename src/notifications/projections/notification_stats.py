"""NotificationStats — daily counts by notification type and channel."""

from notifications.domain import notifications
from notifications.notification.events import NotificationSent
from notifications.notification.notification import Notification
from protean.core.projector import on
from protean.fields import DateTime, Integer, String
from protean.utils.globals import current_domain


@notifications.projection
class NotificationStats:
    stat_key: String(identifier=True, required=True)  # "YYYY-MM-DD:type:channel"
    date: String(required=True, max_length=10)
    notification_type: String(required=True)
    channel: String(required=True)
    count: Integer(default=0)
    updated_at: DateTime()


@notifications.projector(projector_for=NotificationStats, aggregates=[Notification])
class NotificationStatsProjector:
    @on(NotificationSent)
    def on_notification_sent(self, event):
        repo = current_domain.repository_for(NotificationStats)

        date_str = event.sent_at.strftime("%Y-%m-%d") if event.sent_at else "unknown"
        # We need the notification type — load from NotificationLog or Notification
        try:
            notif = current_domain.repository_for(Notification).get(event.notification_id)
            notification_type = notif.notification_type
        except Exception:
            notification_type = "Unknown"

        stat_key = f"{date_str}:{notification_type}:{event.channel}"

        try:
            stat = repo.get(stat_key)
            stat.count = stat.count + 1
            stat.updated_at = event.sent_at
        except Exception:
            stat = NotificationStats(
                stat_key=stat_key,
                date=date_str,
                notification_type=notification_type,
                channel=event.channel,
                count=1,
                updated_at=event.sent_at,
            )

        repo.add(stat)
