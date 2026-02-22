"""Application tests for CancelNotification command handler."""

from datetime import UTC, datetime, timedelta

import pytest
from notifications.notification.cancellation import CancelNotification
from notifications.notification.notification import (
    Notification,
    NotificationChannel,
    NotificationStatus,
    NotificationType,
)
from protean import current_domain
from protean.exceptions import ValidationError


def _create_pending_notification(**overrides):
    """Create a notification that stays PENDING (scheduled for future dispatch)."""
    future = datetime.now(UTC) + timedelta(days=30)
    defaults = {
        "recipient_id": "cust-001",
        "notification_type": NotificationType.WELCOME.value,
        "channel": NotificationChannel.EMAIL.value,
        "body": "Welcome to ShopStream!",
        "scheduled_for": future,
    }
    defaults.update(overrides)
    n = Notification.create(**defaults)
    repo = current_domain.repository_for(Notification)
    repo.add(n)
    return str(n.id)


class TestCancelNotificationCommand:
    def test_cancel_sets_cancelled_status(self):
        nid = _create_pending_notification()
        current_domain.process(
            CancelNotification(notification_id=nid, reason="No longer needed"),
            asynchronous=False,
        )
        n = current_domain.repository_for(Notification).get(nid)
        assert n.status == NotificationStatus.CANCELLED.value

    def test_cancel_sets_reason(self):
        nid = _create_pending_notification()
        current_domain.process(
            CancelNotification(notification_id=nid, reason="User opted out"),
            asynchronous=False,
        )
        n = current_domain.repository_for(Notification).get(nid)
        assert n.failure_reason == "User opted out"

    def test_cannot_cancel_sent_notification(self):
        # Create immediate notification (auto-dispatched to SENT)
        n = Notification.create(
            recipient_id="cust-cancel-sent",
            notification_type=NotificationType.WELCOME.value,
            channel=NotificationChannel.EMAIL.value,
            body="Welcome!",
        )
        repo = current_domain.repository_for(Notification)
        repo.add(n)
        nid = str(n.id)
        # After auto-dispatch it should be SENT
        updated = repo.get(nid)
        assert updated.status == NotificationStatus.SENT.value
        with pytest.raises(ValidationError):
            current_domain.process(
                CancelNotification(notification_id=nid, reason="Too late"),
                asynchronous=False,
            )
