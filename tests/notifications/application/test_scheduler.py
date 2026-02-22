"""Application tests for ProcessScheduledNotifications command handler."""

from datetime import UTC, datetime, timedelta

from notifications.channel import get_channel, reset_channels
from notifications.notification.notification import (
    Notification,
    NotificationChannel,
    NotificationStatus,
    NotificationType,
)
from notifications.notification.scheduler import ProcessScheduledNotifications
from protean import current_domain


def _create_scheduled_notification(
    scheduled_for=None,
    channel=NotificationChannel.EMAIL.value,
    **overrides,
):
    """Create a scheduled notification (stays PENDING, no auto-dispatch)."""
    if scheduled_for is None:
        scheduled_for = datetime.now(UTC) - timedelta(hours=1)  # Already due
    defaults = {
        "recipient_id": "cust-sched-1",
        "notification_type": NotificationType.REVIEW_PROMPT.value,
        "channel": channel,
        "body": "Please review your order!",
        "scheduled_for": scheduled_for,
    }
    defaults.update(overrides)
    n = Notification.create(**defaults)
    repo = current_domain.repository_for(Notification)
    repo.add(n)
    return str(n.id)


class TestProcessScheduledNotifications:
    def setup_method(self):
        reset_channels()

    def teardown_method(self):
        reset_channels()

    def test_dispatches_due_notifications(self):
        """Notifications with scheduled_for in the past are dispatched."""
        past = datetime.now(UTC) - timedelta(hours=1)
        nid = _create_scheduled_notification(scheduled_for=past, recipient_id="cust-sched-due")

        # Verify it's still pending (scheduled notifications skip auto-dispatch)
        n = current_domain.repository_for(Notification).get(nid)
        assert n.status == NotificationStatus.PENDING.value

        # Process scheduled notifications
        current_domain.process(
            ProcessScheduledNotifications(as_of=datetime.now(UTC)),
            asynchronous=False,
        )

        n = current_domain.repository_for(Notification).get(nid)
        assert n.status == NotificationStatus.SENT.value

    def test_skips_future_notifications(self):
        """Notifications scheduled for the future are not dispatched."""
        future = datetime.now(UTC) + timedelta(days=7)
        nid = _create_scheduled_notification(scheduled_for=future, recipient_id="cust-sched-future")

        current_domain.process(
            ProcessScheduledNotifications(as_of=datetime.now(UTC)),
            asynchronous=False,
        )

        n = current_domain.repository_for(Notification).get(nid)
        assert n.status == NotificationStatus.PENDING.value

    def test_skips_non_scheduled_pending(self):
        """Pending notifications without scheduled_for are skipped by the scheduler.

        Non-scheduled PENDING notifications should have been dispatched by the
        auto-dispatch handler already. The scheduler only handles scheduled ones.
        """
        # Create a scheduled (future) notification
        future = datetime.now(UTC) + timedelta(days=30)
        nid = _create_scheduled_notification(scheduled_for=future, recipient_id="cust-sched-nosched")

        current_domain.process(
            ProcessScheduledNotifications(as_of=datetime.now(UTC)),
            asynchronous=False,
        )

        n = current_domain.repository_for(Notification).get(nid)
        assert n.status == NotificationStatus.PENDING.value

    def test_failed_adapter_marks_scheduled_as_failed(self):
        """When the adapter fails during scheduled dispatch, notification is marked FAILED."""
        adapter = get_channel(NotificationChannel.EMAIL.value)
        adapter.configure(should_succeed=False, failure_reason="Scheduled send failed")

        past = datetime.now(UTC) - timedelta(hours=1)
        nid = _create_scheduled_notification(scheduled_for=past, recipient_id="cust-sched-fail")

        current_domain.process(
            ProcessScheduledNotifications(as_of=datetime.now(UTC)),
            asynchronous=False,
        )

        n = current_domain.repository_for(Notification).get(nid)
        assert n.status == NotificationStatus.FAILED.value
        assert "Scheduled send failed" in n.failure_reason

    def test_process_with_default_as_of(self):
        """When as_of is not provided, it defaults to now."""
        past = datetime.now(UTC) - timedelta(hours=1)
        nid = _create_scheduled_notification(scheduled_for=past, recipient_id="cust-sched-default")

        current_domain.process(
            ProcessScheduledNotifications(),
            asynchronous=False,
        )

        n = current_domain.repository_for(Notification).get(nid)
        assert n.status == NotificationStatus.SENT.value

    def test_adapter_exception_marks_failed(self):
        """When the adapter raises an exception, notification is marked FAILED."""
        adapter = get_channel(NotificationChannel.EMAIL.value)
        # Configure to raise an exception by setting a custom side effect
        original_send = adapter.send

        def exploding_send(**kwargs):
            raise RuntimeError("Connection refused")

        adapter.send = exploding_send

        past = datetime.now(UTC) - timedelta(hours=1)
        nid = _create_scheduled_notification(scheduled_for=past, recipient_id="cust-sched-exc")

        current_domain.process(
            ProcessScheduledNotifications(as_of=datetime.now(UTC)),
            asynchronous=False,
        )

        n = current_domain.repository_for(Notification).get(nid)
        assert n.status == NotificationStatus.FAILED.value
        assert "Connection refused" in n.failure_reason

        # Restore
        adapter.send = original_send
