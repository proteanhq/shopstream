"""Application tests for RetryNotification command handler."""

from datetime import UTC, datetime, timedelta

import pytest
from notifications.channel import get_channel, reset_channels
from notifications.notification.notification import (
    Notification,
    NotificationChannel,
    NotificationStatus,
    NotificationType,
)
from notifications.notification.retry import RetryNotification
from protean import current_domain
from protean.exceptions import ValidationError


def _create_pending_notification(**overrides):
    """Create a notification that stays PENDING (scheduled for future)."""
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


def _create_failed_notification(**overrides):
    """Create a notification that fails during dispatch."""
    reset_channels()
    adapter = get_channel(NotificationChannel.EMAIL.value)
    adapter.configure(should_succeed=False, failure_reason="Delivery error")

    defaults = {
        "recipient_id": "cust-001",
        "notification_type": NotificationType.WELCOME.value,
        "channel": NotificationChannel.EMAIL.value,
        "body": "Welcome to ShopStream!",
    }
    defaults.update(overrides)
    n = Notification.create(**defaults)
    repo = current_domain.repository_for(Notification)
    repo.add(n)

    # Reset adapter for subsequent dispatches
    adapter.configure(should_succeed=True)
    return str(n.id)


class TestRetryNotificationCommand:
    def teardown_method(self):
        reset_channels()

    def test_retry_resets_to_pending(self):
        nid = _create_failed_notification()
        # Verify it's failed
        n = current_domain.repository_for(Notification).get(nid)
        assert n.status == NotificationStatus.FAILED.value

        current_domain.process(RetryNotification(notification_id=nid), asynchronous=False)
        n = current_domain.repository_for(Notification).get(nid)
        assert n.status == NotificationStatus.PENDING.value

    def test_retry_clears_failure_reason(self):
        nid = _create_failed_notification()
        current_domain.process(RetryNotification(notification_id=nid), asynchronous=False)
        n = current_domain.repository_for(Notification).get(nid)
        assert n.failure_reason is None

    def test_retry_non_failed_raises(self):
        nid = _create_pending_notification()
        with pytest.raises(ValidationError):
            current_domain.process(RetryNotification(notification_id=nid), asynchronous=False)

    def test_retry_beyond_max_retries_raises(self):
        # Create with max_retries=1, force failure
        reset_channels()
        adapter = get_channel(NotificationChannel.EMAIL.value)
        adapter.configure(should_succeed=False, failure_reason="Delivery error")

        n = Notification.create(
            recipient_id="cust-max-retry",
            notification_type=NotificationType.WELCOME.value,
            channel=NotificationChannel.EMAIL.value,
            body="Welcome!",
            max_retries=1,
        )
        repo = current_domain.repository_for(Notification)
        repo.add(n)
        nid = str(n.id)
        # Now it's FAILED with retry_count=1 (from auto-dispatch failure)
        # max_retries=1, retry_count=1, so retry should immediately fail
        with pytest.raises(ValidationError, match="Maximum retry attempts exceeded"):
            current_domain.process(RetryNotification(notification_id=nid), asynchronous=False)
