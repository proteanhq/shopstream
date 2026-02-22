"""Tests for dispatch handler edge cases — notification not found, non-PENDING, exception, unknown channel."""

from datetime import UTC, datetime

from notifications.channel import get_channel, reset_channels
from notifications.notification.dispatch import (
    NotificationDispatcher,
    _dispatch_via_channel,
)
from notifications.notification.events import NotificationCreated
from notifications.notification.notification import (
    Notification,
    NotificationChannel,
    NotificationStatus,
    NotificationType,
)
from protean import current_domain


class TestDispatcherEdgeCases:
    def setup_method(self):
        reset_channels()

    def teardown_method(self):
        reset_channels()

    def test_notification_not_found_does_not_raise(self):
        """When the notification can't be loaded, dispatcher logs and returns."""
        event = NotificationCreated(
            notification_id="non-existent-id-123",
            recipient_id="cust-x",
            recipient_type="Customer",
            notification_type=NotificationType.WELCOME.value,
            channel=NotificationChannel.EMAIL.value,
            subject="Test",
            created_at=datetime.now(UTC),
        )
        dispatcher = NotificationDispatcher()
        dispatcher.on_notification_created(event)
        # Should not raise — logs error and returns

    def test_non_pending_notification_skipped(self):
        """If the notification has already been dispatched, skip re-dispatch."""
        # Create an immediate notification that auto-dispatches to SENT
        n = Notification.create(
            recipient_id="cust-disp-nonpend",
            notification_type=NotificationType.WELCOME.value,
            channel=NotificationChannel.EMAIL.value,
            body="Welcome!",
        )
        repo = current_domain.repository_for(Notification)
        repo.add(n)

        # Verify it's already SENT
        updated = repo.get(str(n.id))
        assert updated.status == NotificationStatus.SENT.value

        # Manually invoke the dispatcher again — should skip
        event = NotificationCreated(
            notification_id=str(n.id),
            recipient_id="cust-disp-nonpend",
            recipient_type="Customer",
            notification_type=NotificationType.WELCOME.value,
            channel=NotificationChannel.EMAIL.value,
            subject="Test",
            created_at=datetime.now(UTC),
        )
        dispatcher = NotificationDispatcher()
        dispatcher.on_notification_created(event)
        # Should log "not in PENDING status" and return

    def test_adapter_exception_marks_failed(self):
        """When the adapter itself raises an exception, notification is marked FAILED."""
        adapter = get_channel(NotificationChannel.EMAIL.value)
        original_send = adapter.send

        def exploding_send(**kwargs):
            raise RuntimeError("Connection timeout")

        adapter.send = exploding_send

        n = Notification.create(
            recipient_id="cust-disp-exc",
            notification_type=NotificationType.WELCOME.value,
            channel=NotificationChannel.EMAIL.value,
            body="Welcome!",
        )
        repo = current_domain.repository_for(Notification)
        repo.add(n)

        updated = repo.get(str(n.id))
        assert updated.status == NotificationStatus.FAILED.value
        assert "Connection timeout" in updated.failure_reason

        adapter.send = original_send


class TestDispatchViaChannel:
    def setup_method(self):
        reset_channels()

    def teardown_method(self):
        reset_channels()

    def test_unknown_channel_returns_failed(self):
        """Unknown channel type returns a failed status dict."""

        class FakeNotification:
            """Stand-in that bypasses aggregate validation."""

            channel = "Carrier Pigeon"
            recipient_id = "cust-unk"
            subject = "Hello"
            body = "Hello body"

        result = _dispatch_via_channel(None, FakeNotification())
        assert result["status"] == "failed"
        assert "Unknown channel" in result["error"]
