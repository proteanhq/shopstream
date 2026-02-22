"""Application tests for the internal dispatch handler.

Since adding a Notification to the repo triggers auto-dispatch (sync event processing),
we test the dispatcher behavior through the observable effects of creating notifications:
- Immediate notifications get auto-dispatched to SENT
- Scheduled notifications stay in PENDING
- Failed adapters result in FAILED status
"""

from datetime import UTC, datetime, timedelta

from notifications.channel import get_channel, reset_channels
from notifications.notification.notification import (
    Notification,
    NotificationChannel,
    NotificationStatus,
    NotificationType,
)
from protean import current_domain


class TestNotificationAutoDispatch:
    def setup_method(self):
        reset_channels()

    def teardown_method(self):
        reset_channels()

    def test_immediate_notification_auto_dispatched_to_sent(self):
        """Immediate notifications are auto-dispatched by the event handler."""
        n = Notification.create(
            recipient_id="cust-auto-1",
            notification_type=NotificationType.WELCOME.value,
            channel=NotificationChannel.EMAIL.value,
            body="Welcome!",
            subject="Welcome to ShopStream",
        )
        repo = current_domain.repository_for(Notification)
        repo.add(n)

        updated = repo.get(str(n.id))
        assert updated.status == NotificationStatus.SENT.value
        assert updated.sent_at is not None

    def test_email_recorded_by_adapter(self):
        """The email adapter receives the dispatched message."""
        n = Notification.create(
            recipient_id="cust-auto-2",
            notification_type=NotificationType.WELCOME.value,
            channel=NotificationChannel.EMAIL.value,
            body="Welcome!",
            subject="Welcome to ShopStream",
        )
        repo = current_domain.repository_for(Notification)
        repo.add(n)

        adapter = get_channel(NotificationChannel.EMAIL.value)
        matching = [e for e in adapter.sent_emails if e["to"] == "cust-auto-2"]
        assert len(matching) >= 1

    def test_sms_recorded_by_adapter(self):
        n = Notification.create(
            recipient_id="cust-auto-3",
            notification_type=NotificationType.WELCOME.value,
            channel=NotificationChannel.SMS.value,
            body="Welcome!",
        )
        repo = current_domain.repository_for(Notification)
        repo.add(n)

        adapter = get_channel(NotificationChannel.SMS.value)
        matching = [m for m in adapter.sent_messages if m["to"] == "cust-auto-3"]
        assert len(matching) >= 1

    def test_push_recorded_by_adapter(self):
        n = Notification.create(
            recipient_id="cust-auto-4",
            notification_type=NotificationType.WELCOME.value,
            channel=NotificationChannel.PUSH.value,
            body="Welcome!",
            subject="Welcome",
        )
        repo = current_domain.repository_for(Notification)
        repo.add(n)

        adapter = get_channel(NotificationChannel.PUSH.value)
        matching = [p for p in adapter.sent_pushes if p["device_token"] == "cust-auto-4"]
        assert len(matching) >= 1

    def test_slack_recorded_by_adapter(self):
        n = Notification.create(
            recipient_id="operations",
            notification_type=NotificationType.LOW_STOCK_ALERT.value,
            channel=NotificationChannel.SLACK.value,
            body="Low stock alert!",
        )
        repo = current_domain.repository_for(Notification)
        repo.add(n)

        adapter = get_channel(NotificationChannel.SLACK.value)
        assert len(adapter.sent_messages) >= 1

    def test_scheduled_notification_stays_pending(self):
        """Scheduled notifications are NOT auto-dispatched."""
        future = datetime.now(UTC) + timedelta(days=7)
        n = Notification.create(
            recipient_id="cust-sched-1",
            notification_type=NotificationType.REVIEW_PROMPT.value,
            channel=NotificationChannel.EMAIL.value,
            body="Please review your order!",
            scheduled_for=future,
        )
        repo = current_domain.repository_for(Notification)
        repo.add(n)

        updated = repo.get(str(n.id))
        assert updated.status == NotificationStatus.PENDING.value

    def test_failed_adapter_marks_notification_failed(self):
        """When the adapter fails, the notification is marked FAILED."""
        adapter = get_channel(NotificationChannel.EMAIL.value)
        adapter.configure(should_succeed=False, failure_reason="SMTP error 550")

        n = Notification.create(
            recipient_id="cust-fail-1",
            notification_type=NotificationType.WELCOME.value,
            channel=NotificationChannel.EMAIL.value,
            body="Welcome!",
        )
        repo = current_domain.repository_for(Notification)
        repo.add(n)

        updated = repo.get(str(n.id))
        assert updated.status == NotificationStatus.FAILED.value
        assert "SMTP error 550" in updated.failure_reason
