"""ExpireStaleDispatches fails notifications left DISPATCHING, and never sends them.

Under sync processing a claim is followed at once by its send. These tests
switch the domain to async event processing while they claim a notification,
so ``NotificationDispatchStarted`` stays in the outbox and the notification
stays DISPATCHING, as it would if the send were dead-lettered.

The domain clock is frozen, and time passes by advancing it. The claim, the
send deadline and the sweep all read that clock.
"""

from datetime import UTC, datetime, timedelta, timezone

import pytest
from protean import current_domain

from notifications.channel import get_channel, reset_channels
from notifications.domain import notifications
from notifications.notification.dispatch import SEND_DEADLINE, NotificationDispatcher, RecordDispatchResult
from notifications.notification.dispatch_expiry import STALE_DISPATCH_AFTER, ExpireStaleDispatches
from notifications.notification.events import NotificationDispatchStarted
from notifications.notification.notification import (
    STALE_DISPATCH_REASON,
    Notification,
    NotificationChannel,
    NotificationStatus,
    NotificationType,
)
from notifications.notification.retry import RetryNotification
from tests.conftest import FrozenClock
from tests.conftest import as_utc as stored_utc


@pytest.fixture(autouse=True)
def _fresh_channels():
    reset_channels()
    yield
    reset_channels()


@pytest.fixture
def clock(frozen_clock) -> FrozenClock:
    return frozen_clock(notifications, datetime.now(UTC))


def _create(recipient_id: str, scheduled_for: datetime | None = None) -> str:
    notification = Notification.create(
        recipient_id=recipient_id,
        notification_type=NotificationType.WELCOME.value,
        channel=NotificationChannel.EMAIL.value,
        body="Welcome!",
        scheduled_for=scheduled_for,
    )
    current_domain.repository_for(Notification).add(notification)
    return str(notification.id)


def _create_dispatching(recipient_id: str, monkeypatch: pytest.MonkeyPatch) -> tuple[str, datetime]:
    """Return a notification claimed for dispatch whose send never ran, and its claim time."""
    with monkeypatch.context() as m:
        m.setitem(current_domain.config, "event_processing", "async")
        nid = _create(recipient_id)
        repo = current_domain.repository_for(Notification)
        notification = repo.get(nid)
        notification.claim_dispatch(current_domain.clock.now())
        repo.add(notification)
    claimed = current_domain.repository_for(Notification).get(nid)
    assert claimed.status == NotificationStatus.DISPATCHING.value
    return nid, stored_utc(claimed.updated_at)


def _start_event(nid: str, started_at: datetime, retry_count: int = 0) -> NotificationDispatchStarted:
    """The claim's start event, as the send step would receive it."""
    return NotificationDispatchStarted(
        notification_id=nid,
        recipient_id="cust-stale",
        channel=NotificationChannel.EMAIL.value,
        body="Welcome!",
        retry_count=retry_count,
        started_at=started_at,
    )


def _expire(as_of: datetime | None = None) -> None:
    current_domain.process(ExpireStaleDispatches(as_of=as_of), asynchronous=False)


class TestExpireStaleDispatches:
    def test_stale_dispatch_is_marked_failed_without_a_send(self, monkeypatch, clock):
        nid, claimed_at = _create_dispatching("cust-stale-1", monkeypatch)

        clock.advance(STALE_DISPATCH_AFTER)
        _expire()

        notification = current_domain.repository_for(Notification).get(nid)
        assert notification.status == NotificationStatus.FAILED.value
        assert notification.failure_reason == STALE_DISPATCH_REASON
        assert notification.retry_count == 1
        assert get_channel(NotificationChannel.EMAIL.value).sent_emails == []

    def test_recent_dispatch_is_left_alone(self, monkeypatch, clock):
        nid, claimed_at = _create_dispatching("cust-stale-2", monkeypatch)

        clock.advance(STALE_DISPATCH_AFTER - timedelta(seconds=1))
        _expire()

        assert current_domain.repository_for(Notification).get(nid).status == NotificationStatus.DISPATCHING.value

    def test_other_statuses_are_untouched(self, clock):
        sent = _create("cust-stale-sent")
        pending = _create("cust-stale-pending", scheduled_for=datetime.now(UTC) + timedelta(days=1))

        clock.advance(timedelta(days=2))
        _expire()

        repo = current_domain.repository_for(Notification)
        assert repo.get(sent).status == NotificationStatus.SENT.value
        assert repo.get(pending).status == NotificationStatus.PENDING.value

    def test_cutoff_in_another_timezone_is_compared_in_utc(self, monkeypatch, clock):
        nid, claimed_at = _create_dispatching("cust-stale-tz", monkeypatch)
        clock.advance(STALE_DISPATCH_AFTER)
        _expire((claimed_at + STALE_DISPATCH_AFTER).astimezone(timezone(timedelta(hours=2))))

        assert current_domain.repository_for(Notification).get(nid).status == NotificationStatus.FAILED.value

    def test_result_recorded_after_the_sweep_is_skipped(self, monkeypatch, clock):
        nid, claimed_at = _create_dispatching("cust-stale-late", monkeypatch)
        clock.advance(STALE_DISPATCH_AFTER)
        _expire()

        current_domain.process(RecordDispatchResult(notification_id=nid, retry_count=0), asynchronous=False)

        notification = current_domain.repository_for(Notification).get(nid)
        assert notification.status == NotificationStatus.FAILED.value
        assert notification.failure_reason == STALE_DISPATCH_REASON

    def test_expired_notification_is_sent_by_a_retry(self, monkeypatch, clock):
        nid, claimed_at = _create_dispatching("cust-stale-retry", monkeypatch)
        clock.advance(STALE_DISPATCH_AFTER)
        _expire()

        current_domain.process(RetryNotification(notification_id=nid), asynchronous=False)

        assert current_domain.repository_for(Notification).get(nid).status == NotificationStatus.SENT.value
        assert len(get_channel(NotificationChannel.EMAIL.value).sent_emails) == 1


class TestAttemptsAfterExpiry:
    def test_late_result_of_an_expired_claim_does_not_settle_the_retried_claim(self, monkeypatch, clock):
        nid, claimed_at = _create_dispatching("cust-stale-attempt", monkeypatch)
        clock.advance(STALE_DISPATCH_AFTER)
        _expire()
        repo = current_domain.repository_for(Notification)
        with monkeypatch.context() as m:
            m.setitem(current_domain.config, "event_processing", "async")
            current_domain.process(RetryNotification(notification_id=nid), asynchronous=False)
            retried = repo.get(nid)
            retried.claim_dispatch(current_domain.clock.now())
            repo.add(retried)
        assert repo.get(nid).retry_count == 1

        current_domain.process(
            RecordDispatchResult(notification_id=nid, retry_count=0, failure_reason="Late failure"),
            asynchronous=False,
        )
        assert repo.get(nid).status == NotificationStatus.DISPATCHING.value

        current_domain.process(RecordDispatchResult(notification_id=nid, retry_count=1), asynchronous=False)
        assert repo.get(nid).status == NotificationStatus.SENT.value

    def test_start_event_delivered_after_expiry_sends_nothing(self, monkeypatch, clock):
        nid, claimed_at = _create_dispatching("cust-stale-start", monkeypatch)
        clock.advance(STALE_DISPATCH_AFTER)
        _expire()

        NotificationDispatcher().on_dispatch_started(_start_event(nid, claimed_at))

        assert get_channel(NotificationChannel.EMAIL.value).sent_emails == []
        notification = current_domain.repository_for(Notification).get(nid)
        assert notification.status == NotificationStatus.FAILED.value
        assert notification.failure_reason == STALE_DISPATCH_REASON

    def test_start_event_of_an_expired_claim_after_a_retry_sends_once(self, monkeypatch, clock):
        nid, claimed_at = _create_dispatching("cust-stale-twice", monkeypatch)
        clock.advance(STALE_DISPATCH_AFTER)
        _expire()
        current_domain.process(RetryNotification(notification_id=nid), asynchronous=False)
        assert len(get_channel(NotificationChannel.EMAIL.value).sent_emails) == 1

        NotificationDispatcher().on_dispatch_started(_start_event(nid, claimed_at))

        assert len(get_channel(NotificationChannel.EMAIL.value).sent_emails) == 1
        assert current_domain.repository_for(Notification).get(nid).status == NotificationStatus.SENT.value

    def test_claim_past_its_send_deadline_is_left_for_the_sweep(self, monkeypatch, clock):
        nid, claimed_at = _create_dispatching("cust-stale-deadline", monkeypatch)
        clock.advance(SEND_DEADLINE)

        NotificationDispatcher().on_dispatch_started(_start_event(nid, claimed_at))

        assert get_channel(NotificationChannel.EMAIL.value).sent_emails == []
        assert current_domain.repository_for(Notification).get(nid).status == NotificationStatus.DISPATCHING.value


class TestFutureCutoff:
    def test_a_future_as_of_does_not_expire_a_fresh_claim(self, monkeypatch, clock):
        nid, claimed_at = _create_dispatching("cust-stale-future", monkeypatch)

        _expire(claimed_at + STALE_DISPATCH_AFTER + timedelta(hours=1))

        assert current_domain.repository_for(Notification).get(nid).status == NotificationStatus.DISPATCHING.value

    def test_the_claim_survives_a_future_cutoff_and_is_sent_once(self, monkeypatch, clock):
        nid, claimed_at = _create_dispatching("cust-stale-future-send", monkeypatch)
        _expire(claimed_at + STALE_DISPATCH_AFTER + timedelta(hours=1))

        NotificationDispatcher().on_dispatch_started(_start_event(nid, claimed_at))

        assert len(get_channel(NotificationChannel.EMAIL.value).sent_emails) == 1
        assert current_domain.repository_for(Notification).get(nid).status == NotificationStatus.SENT.value
