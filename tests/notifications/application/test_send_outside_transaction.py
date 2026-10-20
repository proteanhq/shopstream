"""Channel sends run with no open database transaction.

On Postgres a unit of work is one real transaction. It opens at the first
repository access and holds a pooled connection until it ends. Every
``@handle`` method runs inside a unit of work, so ``current_uow`` is set
during a send; what must hold is that it has opened no session yet.
These tests run on memory and on Postgres (``--protean-env test``).
"""

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from protean import UnitOfWork, current_domain
from protean.exceptions import TransactionError
from protean.utils.globals import current_uow

from notifications.channel import get_channel, reset_channels
from notifications.channel.transaction_guard import SendInsideTransactionError, open_session_providers
from notifications.notification.notification import (
    Notification,
    NotificationChannel,
    NotificationStatus,
    NotificationType,
)
from notifications.notification.scheduler import ProcessScheduledNotifications

ALL_CHANNELS = [channel.value for channel in NotificationChannel]

# A minimal valid send for each channel's port, called directly on the adapter.
SEND_CALLS = {
    NotificationChannel.EMAIL.value: lambda adapter: adapter.send(to="cust-guard", subject="Hi", body="Hi"),
    NotificationChannel.SMS.value: lambda adapter: adapter.send(to="cust-guard", body="Hi"),
    NotificationChannel.PUSH.value: lambda adapter: adapter.send(device_token="cust-guard", title="Hi", body="Hi"),
    NotificationChannel.SLACK.value: lambda adapter: adapter.send(channel="#operations", message="Hi"),
}


def _checked_out_connections() -> int | None:
    """Pooled connections checked out right now, or None on a provider with no pool (memory)."""
    engine = getattr(current_domain.providers["default"], "_engine", None)
    return None if engine is None else engine.pool.checkedout()


@pytest.fixture
def observed_sends(monkeypatch: pytest.MonkeyPatch) -> Iterator[list[dict[str, Any]]]:
    """Record the unit-of-work state each fake adapter sees when ``send()`` runs."""
    reset_channels()
    observations: list[dict[str, Any]] = []
    for channel in ALL_CHANNELS:
        adapter = get_channel(channel)
        original = adapter.send

        def recording_send(*args: Any, _channel: str = channel, _original: Any = original, **kwargs: Any) -> Any:
            observations.append(
                {
                    "channel": _channel,
                    "uow_active": bool(current_uow),
                    "sessions": open_session_providers(),
                    "checked_out": _checked_out_connections(),
                }
            )
            return _original(*args, **kwargs)

        monkeypatch.setattr(adapter, "send", recording_send)
    yield observations
    reset_channels()


def _create(channel: str, recipient_id: str, scheduled_for: datetime | None = None) -> str:
    notification = Notification.create(
        recipient_id=recipient_id,
        notification_type=NotificationType.WELCOME.value,
        channel=channel,
        subject="Hello",
        body="Hello there",
        scheduled_for=scheduled_for,
    )
    current_domain.repository_for(Notification).add(notification)
    return str(notification.id)


class TestDispatcherSendsOutsideTransaction:
    @pytest.mark.parametrize("channel", ALL_CHANNELS)
    def test_send_sees_no_open_session(self, channel, observed_sends):
        nid = _create(channel, f"cust-notx-{channel}")

        assert len(observed_sends) == 1
        seen = observed_sends[0]
        assert seen["channel"] == channel
        # A handler always has a unit of work; it must not have a session yet.
        assert seen["uow_active"] is True
        assert seen["sessions"] == []
        # On Postgres, no pooled connection is held during the send.
        assert seen["checked_out"] in (None, 0)
        assert current_domain.repository_for(Notification).get(nid).status == NotificationStatus.SENT.value


class TestSchedulerSendsOutsideTransaction:
    def test_each_due_send_sees_no_open_session(self, observed_sends):
        past = datetime.now(UTC) - timedelta(hours=1)
        nids = [_create(channel, f"cust-sched-notx-{channel}", scheduled_for=past) for channel in ALL_CHANNELS]
        assert observed_sends == []

        current_domain.process(ProcessScheduledNotifications(as_of=datetime.now(UTC)), asynchronous=False)

        assert sorted(seen["channel"] for seen in observed_sends) == sorted(ALL_CHANNELS)
        for seen in observed_sends:
            assert seen["uow_active"] is True, seen
            assert seen["sessions"] == [], seen
            assert seen["checked_out"] in (None, 0), seen
        repo = current_domain.repository_for(Notification)
        assert [repo.get(nid).status for nid in nids] == [NotificationStatus.SENT.value] * len(nids)


class TestTransactionGuard:
    def setup_method(self):
        reset_channels()

    def teardown_method(self):
        reset_channels()

    @pytest.mark.parametrize("channel", ALL_CHANNELS)
    def test_send_after_a_repository_access_raises(self, channel):
        adapter = get_channel(channel)
        with UnitOfWork():
            current_domain.repository_for(Notification).get_or_none("guard-probe")
            with pytest.raises(SendInsideTransactionError, match=f"{channel} send ran inside an open transaction"):
                SEND_CALLS[channel](adapter)

    def test_send_in_a_unit_of_work_without_repository_access_is_allowed(self):
        adapter = get_channel(NotificationChannel.SMS.value)
        with UnitOfWork():
            result = adapter.send(to="cust-guard", body="Hi")
        assert result["status"] == "sent"

    def test_send_outside_any_unit_of_work_is_allowed(self):
        adapter = get_channel(NotificationChannel.PUSH.value)
        result = adapter.send(device_token="cust-guard", title="Hi", body="Hi")
        assert result["status"] == "sent"

    def test_dispatcher_surfaces_a_guard_failure_instead_of_recording_failed(self, monkeypatch):
        adapter = get_channel(NotificationChannel.EMAIL.value)

        def send_inside_transaction(**kwargs):
            raise SendInsideTransactionError("Email send ran inside an open transaction")

        monkeypatch.setattr(adapter, "send", send_inside_transaction)
        notification = Notification.create(
            recipient_id="cust-guard-surface",
            notification_type=NotificationType.WELCOME.value,
            channel=NotificationChannel.EMAIL.value,
            body="Hi",
        )
        repo = current_domain.repository_for(Notification)

        with pytest.raises(TransactionError, match="SendInsideTransactionError"):
            repo.add(notification)
        assert repo.get(str(notification.id)).status == NotificationStatus.PENDING.value
