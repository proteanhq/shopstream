"""A version conflict on the record step must not send the notification again.

The record step joins the send method's unit of work, and Protean has no way
to commit it on its own inside ``@handle``. The two providers fail differently:

- Memory finds the conflict at commit, so Protean retries the whole send
  method and the channel is called twice (proteanhq/protean#1915).
- Postgres finds it at save time, inside the record step. That step's own
  retry runs in a transaction already marked for rollback, so the result is
  lost and the notification stays DISPATCHING (proteanhq/protean#1914).

These tests run on memory and on Postgres (``--protean-env test``).
"""

import threading
from datetime import UTC, datetime
from typing import Any

import pytest
from protean import current_domain

from notifications.channel import get_channel, reset_channels
from notifications.domain import notifications
from notifications.notification.notification import (
    Notification,
    NotificationChannel,
    NotificationStatus,
    NotificationType,
)


def _write_from_another_worker(notification_id: str) -> None:
    """Save the notification in a separate unit of work, as a second worker would."""

    def write() -> None:
        with notifications.domain_context():
            repo = notifications.repository_for(Notification)
            notification = repo.get(notification_id)
            notification.updated_at = datetime.now(UTC)
            repo.add(notification)

    # A new thread starts with no unit of work, so this write commits on its own.
    worker = threading.Thread(target=write)
    worker.start()
    worker.join()


@pytest.mark.protean_bug(
    issue=1914,
    state="open",
    bug=(
        "On Postgres, a version conflict on a dispatch handler's record step is found at save time. The step's own "
        "retry runs in a transaction already marked for rollback, so the result is lost and the notification stays "
        "DISPATCHING."
    ),
)
@pytest.mark.protean_bug(
    issue=1915,
    state="open",
    bug=(
        "On memory, a version conflict on a dispatch handler's record step is found at commit, so Protean retries the "
        "whole send method and the channel is called twice."
    ),
)
@pytest.mark.xfail(
    strict=True,
    reason="proteanhq/protean#1915 and #1914: a conflict on the record step sends again or loses the result",
)
def test_conflict_on_the_record_step_sends_once(monkeypatch):
    reset_channels()
    adapter = get_channel(NotificationChannel.EMAIL.value)
    original_mark_sent = Notification.mark_sent
    conflicts: list[str] = []

    def mark_sent_after_a_concurrent_write(self: Notification, *args: Any, **kwargs: Any) -> None:
        if not conflicts:
            conflicts.append(str(self.id))
            _write_from_another_worker(str(self.id))
        original_mark_sent(self, *args, **kwargs)

    monkeypatch.setattr(Notification, "mark_sent", mark_sent_after_a_concurrent_write)

    notification = Notification.create(
        recipient_id="cust-record-conflict",
        notification_type=NotificationType.WELCOME.value,
        channel=NotificationChannel.EMAIL.value,
        body="Welcome!",
    )
    current_domain.repository_for(Notification).add(notification)

    assert conflicts == [str(notification.id)]
    assert current_domain.repository_for(Notification).get(str(notification.id)).status == NotificationStatus.SENT.value
    assert len(adapter.sent_emails) == 1
    reset_channels()
