"""Tests for dispatch edge cases: notification not found, not claimable, exception, unknown channel."""

from datetime import UTC, datetime, timedelta

import pytest
from protean import current_domain
from protean.exceptions import TransactionError

from notifications.channel import get_channel, reset_channels
from notifications.channel.errors import ChannelUnavailableError
from notifications.notification.dispatch import (
    NotificationDispatcher,
    RecordDispatchResult,
    _dispatch_via_channel,
)
from notifications.notification.events import NotificationDispatchRequested, NotificationDispatchStarted
from notifications.notification.notification import (
    Notification,
    NotificationChannel,
    NotificationStatus,
    NotificationType,
)


def _dispatch_request(notification_id: str) -> NotificationDispatchRequested:
    return NotificationDispatchRequested(notification_id=notification_id, requested_at=datetime.now(UTC))


def _dispatch_started(notification_id: str, recipient_id: str = "cust-x") -> NotificationDispatchStarted:
    return NotificationDispatchStarted(
        notification_id=notification_id,
        recipient_id=recipient_id,
        channel=NotificationChannel.EMAIL.value,
        subject="Test",
        body="Hello",
        retry_count=0,
        started_at=datetime.now(UTC),
    )


class TestDispatcherEdgeCases:
    def setup_method(self):
        reset_channels()

    def teardown_method(self):
        reset_channels()

    def test_result_for_unknown_notification_does_not_raise(self):
        """Recording a result for a notification that can't be loaded logs and returns."""
        current_domain.process(
            RecordDispatchResult(notification_id="non-existent-id-123", retry_count=0),
            asynchronous=False,
        )

    def test_request_for_unknown_notification_does_not_raise(self):
        """A dispatch request for a notification that can't be loaded logs and returns."""
        NotificationDispatcher().on_dispatch_requested(_dispatch_request("non-existent-id-456"))

    def test_redelivered_request_does_not_send_again(self):
        """A request redelivered after the notification was sent finds it claimed and skips."""
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
        adapter = get_channel(NotificationChannel.EMAIL.value)
        assert len(adapter.sent_emails) == 1

        NotificationDispatcher().on_dispatch_requested(_dispatch_request(str(n.id)))

        after = repo.get(str(n.id))
        assert after.status == NotificationStatus.SENT.value
        assert after.sent_at == sent.sent_at
        assert len(adapter.sent_emails) == 1

    def test_request_for_cancelled_notification_sends_nothing(self):
        """A notification cancelled before its claim stays CANCELLED and is never sent."""
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

        NotificationDispatcher().on_dispatch_requested(_dispatch_request(str(n.id)))

        assert repo.get(str(n.id)).status == NotificationStatus.CANCELLED.value
        assert get_channel(NotificationChannel.EMAIL.value).sent_emails == []

    def test_two_requests_before_the_claim_send_once(self):
        """Only one of two dispatch requests raised while PENDING can claim the notification."""
        n = Notification.create(
            recipient_id="cust-disp-twice",
            notification_type=NotificationType.WELCOME.value,
            channel=NotificationChannel.EMAIL.value,
            body="Welcome!",
        )
        n.request_dispatch()
        assert [e.__class__.__name__ for e in n._events].count("NotificationDispatchRequested") == 2
        repo = current_domain.repository_for(Notification)
        repo.add(n)

        assert repo.get(str(n.id)).status == NotificationStatus.SENT.value
        assert len(get_channel(NotificationChannel.EMAIL.value).sent_emails) == 1

    def test_result_for_a_notification_no_longer_dispatching_is_not_recorded(self):
        """A result arriving after the notification left DISPATCHING leaves it unchanged."""
        n = Notification.create(
            recipient_id="cust-disp-late",
            notification_type=NotificationType.WELCOME.value,
            channel=NotificationChannel.EMAIL.value,
            body="Welcome!",
        )
        repo = current_domain.repository_for(Notification)
        repo.add(n)
        assert repo.get(str(n.id)).status == NotificationStatus.SENT.value

        current_domain.process(
            RecordDispatchResult(notification_id=str(n.id), retry_count=0, failure_reason="Late failure"),
            asynchronous=False,
        )

        after = repo.get(str(n.id))
        assert after.status == NotificationStatus.SENT.value
        assert after.failure_reason is None

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


class TestDispatcherChannelOutage:
    def setup_method(self):
        reset_channels()

    def teardown_method(self):
        reset_channels()

    @staticmethod
    def _claim_without_send(channel: str, monkeypatch) -> NotificationDispatchStarted:
        """Save a claimed notification and return its start event, without sending it."""
        # Async processing saves the claim without handling NotificationDispatchStarted.
        with monkeypatch.context() as m:
            m.setitem(current_domain.config, "event_processing", "async")
            n = Notification.create(
                recipient_id="cust-outage",
                notification_type=NotificationType.WELCOME.value,
                channel=channel,
                subject="Welcome",
                body="Welcome!",
            )
            n.claim_dispatch(current_domain.clock.now())
            started = [e for e in n._events if isinstance(e, NotificationDispatchStarted)]
            current_domain.repository_for(Notification).add(n)
        assert len(started) == 1
        return started[0]

    @pytest.mark.parametrize("channel", [c.value for c in NotificationChannel])
    def test_outage_propagates_and_leaves_the_notification_dispatching(self, channel, monkeypatch):
        started = self._claim_without_send(channel, monkeypatch)
        get_channel(channel).set_outage(True)

        with pytest.raises(ChannelUnavailableError):
            NotificationDispatcher().on_dispatch_started(started)

        stored = current_domain.repository_for(Notification).get(str(started.notification_id))
        assert stored.status == NotificationStatus.DISPATCHING.value
        assert stored.failure_reason is None

    @pytest.mark.parametrize("channel", [c.value for c in NotificationChannel])
    def test_redelivered_send_after_the_outage_marks_it_sent(self, channel, monkeypatch):
        started = self._claim_without_send(channel, monkeypatch)
        get_channel(channel).set_outage(True)
        with pytest.raises(ChannelUnavailableError):
            NotificationDispatcher().on_dispatch_started(started)

        get_channel(channel).set_outage(False)
        NotificationDispatcher().on_dispatch_started(started)

        stored = current_domain.repository_for(Notification).get(str(started.notification_id))
        assert stored.status == NotificationStatus.SENT.value
        assert len(_sent_records(get_channel(channel))) == 1

    def test_outage_under_sync_processing_reaches_the_creator_and_leaves_the_claim(self):
        get_channel(NotificationChannel.EMAIL.value).set_outage(True)
        n = Notification.create(
            recipient_id="cust-outage-sync",
            notification_type=NotificationType.WELCOME.value,
            channel=NotificationChannel.EMAIL.value,
            body="Welcome!",
        )

        with pytest.raises(TransactionError, match="ChannelUnavailableError"):
            current_domain.repository_for(Notification).add(n)

        stored = current_domain.repository_for(Notification).get(str(n.id))
        assert stored.status == NotificationStatus.DISPATCHING.value
        assert stored.failure_reason is None


def _sent_records(adapter) -> list:
    """The records a fake adapter keeps of what it sent; each adapter names the list differently."""
    for name in ("sent_emails", "sent_messages", "sent_pushes"):
        if hasattr(adapter, name):
            return getattr(adapter, name)
    raise AssertionError(f"{type(adapter).__name__} keeps no record of sends")


class TestDispatchViaChannel:
    def test_email_without_subject_sends_an_empty_subject(self):
        adapter = get_channel(NotificationChannel.EMAIL.value)
        request = NotificationDispatchStarted(**{**_dispatch_started("nosubj-1").to_dict(), "subject": None})

        _dispatch_via_channel(adapter, request)

        assert adapter.sent_emails[-1]["subject"] == ""

    def test_push_without_subject_sends_an_empty_title(self):
        adapter = get_channel(NotificationChannel.PUSH.value)
        request = NotificationDispatchStarted(
            **{**_dispatch_started("nosubj-2").to_dict(), "channel": NotificationChannel.PUSH.value, "subject": None}
        )

        _dispatch_via_channel(adapter, request)

        assert adapter.sent_pushes[-1]["title"] == ""

    def test_slack_goes_to_the_operations_channel(self):
        adapter = get_channel(NotificationChannel.SLACK.value)
        request = NotificationDispatchStarted(
            **{**_dispatch_started("slack-1").to_dict(), "channel": NotificationChannel.SLACK.value}
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

        request = _dispatch_started("unk-1", "cust-unk")
        request = NotificationDispatchStarted(**{**request.to_dict(), "channel": "Carrier Pigeon"})

        result = _dispatch_via_channel(None, request)
        assert result["status"] == "failed"
        assert "Unknown channel" in result["error"]
