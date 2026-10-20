"""Tests for dispatch edge cases: notification not found, non-PENDING, exception, unknown channel."""

from datetime import UTC, datetime, timedelta

import pytest
from protean import current_domain

from notifications.channel import get_channel, reset_channels
from notifications.notification.dispatch import (
    NotificationDispatcher,
    RecordDispatchResult,
    _dispatch_via_channel,
)
from notifications.notification.events import NotificationDispatchRequested
from notifications.notification.notification import (
    Notification,
    NotificationChannel,
    NotificationStatus,
    NotificationType,
)


def _dispatch_request(notification_id: str, recipient_id: str = "cust-x") -> NotificationDispatchRequested:
    return NotificationDispatchRequested(
        notification_id=notification_id,
        recipient_id=recipient_id,
        channel=NotificationChannel.EMAIL.value,
        subject="Test",
        body="Hello",
        requested_at=datetime.now(UTC),
    )


class TestDispatcherEdgeCases:
    def setup_method(self):
        reset_channels()

    def teardown_method(self):
        reset_channels()

    def test_result_for_unknown_notification_does_not_raise(self):
        """Recording a result for a notification that can't be loaded logs and returns."""
        current_domain.process(
            RecordDispatchResult(notification_id="non-existent-id-123"),
            asynchronous=False,
        )

    def test_redelivered_request_does_not_record_a_second_result(self):
        """A request redelivered after the notification was sent leaves it SENT."""
        n = Notification.create(
            recipient_id="cust-disp-nonpend",
            notification_type=NotificationType.WELCOME.value,
            channel=NotificationChannel.EMAIL.value,
            body="Welcome!",
        )
        repo = current_domain.repository_for(Notification)
        repo.add(n)
        sent = repo.get(str(n.id))
        assert sent.status == NotificationStatus.SENT.value

        NotificationDispatcher().on_dispatch_requested(_dispatch_request(str(n.id), "cust-disp-nonpend"))

        after = repo.get(str(n.id))
        assert after.status == NotificationStatus.SENT.value
        assert after.sent_at == sent.sent_at

    def test_request_for_cancelled_notification_leaves_it_cancelled(self):
        """A notification cancelled before its send is recorded stays CANCELLED."""
        n = Notification.create(
            recipient_id="cust-disp-cancel",
            notification_type=NotificationType.REVIEW_PROMPT.value,
            channel=NotificationChannel.EMAIL.value,
            body="Review?",
            scheduled_for=datetime.now(UTC) + timedelta(days=1),
        )
        repo = current_domain.repository_for(Notification)
        repo.add(n)
        pending = repo.get(str(n.id))
        pending.cancel("Customer opted out")
        repo.add(pending)

        NotificationDispatcher().on_dispatch_requested(_dispatch_request(str(n.id), "cust-disp-cancel"))

        assert repo.get(str(n.id)).status == NotificationStatus.CANCELLED.value

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

    def test_failed_send_with_a_non_string_error_is_recorded_failed(self, monkeypatch):
        """An adapter that breaks the contract with a non-string error is still recorded FAILED."""
        adapter = get_channel(NotificationChannel.EMAIL.value)
        monkeypatch.setattr(adapter, "send", lambda **kwargs: {"status": "failed", "error": 503})

        n = Notification.create(
            recipient_id="cust-disp-interr",
            notification_type=NotificationType.WELCOME.value,
            channel=NotificationChannel.EMAIL.value,
            body="Welcome!",
        )
        repo = current_domain.repository_for(Notification)
        repo.add(n)

        updated = repo.get(str(n.id))
        assert updated.status == NotificationStatus.FAILED.value
        assert updated.failure_reason == "503"

    @pytest.mark.parametrize("error", [None, ""])
    def test_failed_send_without_an_error_text_is_recorded_failed(self, error, monkeypatch):
        """A failed send whose adapter gives no error text is still recorded FAILED."""
        adapter = get_channel(NotificationChannel.EMAIL.value)
        monkeypatch.setattr(adapter, "send", lambda **kwargs: {"status": "failed", "error": error})

        n = Notification.create(
            recipient_id="cust-disp-noerr",
            notification_type=NotificationType.WELCOME.value,
            channel=NotificationChannel.EMAIL.value,
            body="Welcome!",
        )
        repo = current_domain.repository_for(Notification)
        repo.add(n)

        updated = repo.get(str(n.id))
        assert updated.status == NotificationStatus.FAILED.value
        assert updated.failure_reason == "Unknown dispatch error"

    def test_adapter_exception_without_a_message_is_recorded_failed(self, monkeypatch):
        """An exception with an empty message records its type name as the reason."""
        adapter = get_channel(NotificationChannel.EMAIL.value)

        def silent_failure(**kwargs):
            raise TimeoutError()

        monkeypatch.setattr(adapter, "send", silent_failure)

        n = Notification.create(
            recipient_id="cust-disp-silent",
            notification_type=NotificationType.WELCOME.value,
            channel=NotificationChannel.EMAIL.value,
            body="Welcome!",
        )
        repo = current_domain.repository_for(Notification)
        repo.add(n)

        updated = repo.get(str(n.id))
        assert updated.status == NotificationStatus.FAILED.value
        assert updated.failure_reason == "TimeoutError"

    def test_long_adapter_error_is_cut_to_the_stored_length(self):
        """An adapter error longer than the stored reason still records FAILED."""
        adapter = get_channel(NotificationChannel.EMAIL.value)
        adapter.configure(should_succeed=False, failure_reason="x" * 800)

        n = Notification.create(
            recipient_id="cust-disp-long",
            notification_type=NotificationType.WELCOME.value,
            channel=NotificationChannel.EMAIL.value,
            body="Welcome!",
        )
        repo = current_domain.repository_for(Notification)
        repo.add(n)

        updated = repo.get(str(n.id))
        assert updated.status == NotificationStatus.FAILED.value
        assert updated.failure_reason == "x" * 500


class TestDispatchViaChannel:
    def test_email_without_subject_sends_an_empty_subject(self):
        adapter = get_channel(NotificationChannel.EMAIL.value)
        request = NotificationDispatchRequested(**{**_dispatch_request("nosubj-1").to_dict(), "subject": None})

        _dispatch_via_channel(adapter, request)

        assert adapter.sent_emails[-1]["subject"] == ""

    def test_push_without_subject_sends_an_empty_title(self):
        adapter = get_channel(NotificationChannel.PUSH.value)
        request = NotificationDispatchRequested(
            **{**_dispatch_request("nosubj-2").to_dict(), "channel": NotificationChannel.PUSH.value, "subject": None}
        )

        _dispatch_via_channel(adapter, request)

        assert adapter.sent_pushes[-1]["title"] == ""

    def test_slack_goes_to_the_operations_channel(self):
        adapter = get_channel(NotificationChannel.SLACK.value)
        request = NotificationDispatchRequested(
            **{**_dispatch_request("slack-1").to_dict(), "channel": NotificationChannel.SLACK.value}
        )

        _dispatch_via_channel(adapter, request)

        assert adapter.sent_messages[-1]["channel"] == "#operations"
        assert adapter.sent_messages[-1]["message"] == "Hello"

    def setup_method(self):
        reset_channels()

    def teardown_method(self):
        reset_channels()

    def test_unknown_channel_returns_failed(self):
        """Unknown channel type returns a failed status dict."""

        request = _dispatch_request("unk-1", "cust-unk")
        request = NotificationDispatchRequested(**{**request.to_dict(), "channel": "Carrier Pigeon"})

        result = _dispatch_via_channel(None, request)
        assert result["status"] == "failed"
        assert "Unknown channel" in result["error"]
