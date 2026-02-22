"""Tests for projector edge cases — directly invoke projector methods.

In sync test mode, projectors may not see all events from the dispatch handler's
UoW. These tests directly call projector methods to cover update/delete paths.
"""

from datetime import UTC, datetime, timedelta

import pytest
from notifications.channel import reset_channels
from notifications.notification.events import (
    NotificationBounced,
    NotificationCancelled,
    NotificationDelivered,
    NotificationFailed,
    NotificationRetried,
    NotificationSent,
)
from notifications.notification.notification import (
    Notification,
    NotificationChannel,
    NotificationType,
)
from notifications.projections.customer_notifications import (
    CustomerNotifications,
    CustomerNotificationsProjector,
)
from notifications.projections.failed_notifications import (
    FailedNotifications,
    FailedNotificationsProjector,
)
from notifications.projections.notification_log import (
    NotificationLog,
    NotificationLogProjector,
)
from notifications.projections.notification_stats import (
    NotificationStats,
    NotificationStatsProjector,
)
from protean import current_domain
from protean.exceptions import ObjectNotFoundError


def _create_notification_and_log(recipient_id="cust-proj-edge"):
    """Create a notification (scheduled to stay PENDING) and return its ID."""
    future = datetime.now(UTC) + timedelta(days=30)
    n = Notification.create(
        recipient_id=recipient_id,
        notification_type=NotificationType.WELCOME.value,
        channel=NotificationChannel.EMAIL.value,
        body="Test body",
        subject="Test subject",
        scheduled_for=future,
    )
    repo = current_domain.repository_for(Notification)
    repo.add(n)
    return str(n.id)


class TestNotificationLogProjectorUpdates:
    def test_sent_update(self):
        nid = _create_notification_and_log("cust-log-sent-edge")
        now = datetime.now(UTC)

        projector = NotificationLogProjector()
        event = NotificationSent(
            notification_id=nid,
            recipient_id="cust-log-sent-edge",
            channel=NotificationChannel.EMAIL.value,
            sent_at=now,
        )
        projector.on_notification_sent(event)

        log = current_domain.repository_for(NotificationLog).get(nid)
        assert log.status == "Sent"
        assert log.sent_at is not None

    def test_delivered_update(self):
        nid = _create_notification_and_log("cust-log-del-edge")
        now = datetime.now(UTC)

        projector = NotificationLogProjector()
        projector.on_notification_delivered(
            NotificationDelivered(
                notification_id=nid,
                recipient_id="cust-log-del-edge",
                channel=NotificationChannel.EMAIL.value,
                delivered_at=now,
            )
        )

        log = current_domain.repository_for(NotificationLog).get(nid)
        assert log.status == "Delivered"
        assert log.delivered_at is not None

    def test_failed_update(self):
        nid = _create_notification_and_log("cust-log-fail-edge")
        now = datetime.now(UTC)

        projector = NotificationLogProjector()
        projector.on_notification_failed(
            NotificationFailed(
                notification_id=nid,
                recipient_id="cust-log-fail-edge",
                channel=NotificationChannel.EMAIL.value,
                reason="SMTP error",
                retry_count=1,
                max_retries=3,
                failed_at=now,
            )
        )

        log = current_domain.repository_for(NotificationLog).get(nid)
        assert log.status == "Failed"
        assert log.failure_reason == "SMTP error"

    def test_bounced_update(self):
        nid = _create_notification_and_log("cust-log-bounce-edge")
        now = datetime.now(UTC)

        projector = NotificationLogProjector()
        projector.on_notification_bounced(
            NotificationBounced(
                notification_id=nid,
                recipient_id="cust-log-bounce-edge",
                channel=NotificationChannel.EMAIL.value,
                reason="Invalid address",
                bounced_at=now,
            )
        )

        log = current_domain.repository_for(NotificationLog).get(nid)
        assert log.status == "Bounced"
        assert log.failure_reason == "Invalid address"

    def test_cancelled_update(self):
        nid = _create_notification_and_log("cust-log-cancel-edge")
        now = datetime.now(UTC)

        projector = NotificationLogProjector()
        projector.on_notification_cancelled(
            NotificationCancelled(
                notification_id=nid,
                recipient_id="cust-log-cancel-edge",
                channel=NotificationChannel.EMAIL.value,
                reason="Customer opted out",
                cancelled_at=now,
            )
        )

        log = current_domain.repository_for(NotificationLog).get(nid)
        assert log.status == "Cancelled"
        assert log.failure_reason == "Customer opted out"

    def test_retried_update(self):
        nid = _create_notification_and_log("cust-log-retry-edge")
        now = datetime.now(UTC)

        projector = NotificationLogProjector()
        projector.on_notification_retried(
            NotificationRetried(
                notification_id=nid,
                recipient_id="cust-log-retry-edge",
                channel=NotificationChannel.EMAIL.value,
                retry_count=1,
                retried_at=now,
            )
        )

        log = current_domain.repository_for(NotificationLog).get(nid)
        assert log.status == "Pending"
        assert log.retry_count == 1

    def test_update_nonexistent_log_does_not_raise(self):
        """Updating a log that doesn't exist should silently return."""
        projector = NotificationLogProjector()
        projector.on_notification_sent(
            NotificationSent(
                notification_id="nonexistent-log-id",
                recipient_id="x",
                channel=NotificationChannel.EMAIL.value,
                sent_at=datetime.now(UTC),
            )
        )


class TestCustomerNotificationsProjectorUpdates:
    def test_sent_status_update(self):
        nid = _create_notification_and_log("cust-cn-sent-edge")
        now = datetime.now(UTC)

        projector = CustomerNotificationsProjector()
        projector.on_notification_sent(
            NotificationSent(
                notification_id=nid,
                recipient_id="cust-cn-sent-edge",
                channel=NotificationChannel.EMAIL.value,
                sent_at=now,
            )
        )

        cn = current_domain.repository_for(CustomerNotifications).get(nid)
        assert cn.status == "Sent"

    def test_delivered_status_update(self):
        nid = _create_notification_and_log("cust-cn-del-edge")
        now = datetime.now(UTC)

        projector = CustomerNotificationsProjector()
        projector.on_notification_delivered(
            NotificationDelivered(
                notification_id=nid,
                recipient_id="cust-cn-del-edge",
                channel=NotificationChannel.EMAIL.value,
                delivered_at=now,
            )
        )

        cn = current_domain.repository_for(CustomerNotifications).get(nid)
        assert cn.status == "Delivered"

    def test_failed_status_update(self):
        nid = _create_notification_and_log("cust-cn-fail-edge")
        now = datetime.now(UTC)

        projector = CustomerNotificationsProjector()
        projector.on_notification_failed(
            NotificationFailed(
                notification_id=nid,
                recipient_id="cust-cn-fail-edge",
                channel=NotificationChannel.EMAIL.value,
                reason="SMTP error",
                retry_count=1,
                max_retries=3,
                failed_at=now,
            )
        )

        cn = current_domain.repository_for(CustomerNotifications).get(nid)
        assert cn.status == "Failed"

    def test_update_nonexistent_notification_does_not_raise(self):
        projector = CustomerNotificationsProjector()
        projector.on_notification_sent(
            NotificationSent(
                notification_id="nonexistent-cn-id",
                recipient_id="x",
                channel=NotificationChannel.EMAIL.value,
                sent_at=datetime.now(UTC),
            )
        )


class TestNotificationStatsProjector:
    def setup_method(self):
        reset_channels()

    def teardown_method(self):
        reset_channels()

    def test_stat_created_on_first_sent(self):
        """First sent event creates a new stat entry."""
        nid = _create_notification_and_log("cust-stat-1")
        now = datetime.now(UTC)

        projector = NotificationStatsProjector()
        projector.on_notification_sent(
            NotificationSent(
                notification_id=nid,
                recipient_id="cust-stat-1",
                channel=NotificationChannel.EMAIL.value,
                sent_at=now,
            )
        )

        repo = current_domain.repository_for(NotificationStats)
        all_stats = repo._dao.query.all().items
        assert len(all_stats) >= 1

    def test_stat_incremented_on_second_sent(self):
        """Second sent event for same date/type/channel increments count."""
        nid1 = _create_notification_and_log("cust-stat-2a")
        nid2 = _create_notification_and_log("cust-stat-2b")
        now = datetime.now(UTC)

        projector = NotificationStatsProjector()
        projector.on_notification_sent(
            NotificationSent(
                notification_id=nid1,
                recipient_id="cust-stat-2a",
                channel=NotificationChannel.EMAIL.value,
                sent_at=now,
            )
        )
        projector.on_notification_sent(
            NotificationSent(
                notification_id=nid2,
                recipient_id="cust-stat-2b",
                channel=NotificationChannel.EMAIL.value,
                sent_at=now,
            )
        )

        repo = current_domain.repository_for(NotificationStats)
        date_str = now.strftime("%Y-%m-%d")
        stat_key = f"{date_str}:{NotificationType.WELCOME.value}:{NotificationChannel.EMAIL.value}"
        stat = repo.get(stat_key)
        assert stat.count == 2

    def test_stat_for_unknown_notification(self):
        """Sent event for non-existent notification uses 'Unknown' type."""
        projector = NotificationStatsProjector()
        now = datetime.now(UTC)
        projector.on_notification_sent(
            NotificationSent(
                notification_id="nonexistent-stat-id",
                recipient_id="x",
                channel=NotificationChannel.EMAIL.value,
                sent_at=now,
            )
        )

        repo = current_domain.repository_for(NotificationStats)
        date_str = now.strftime("%Y-%m-%d")
        stat_key = f"{date_str}:Unknown:{NotificationChannel.EMAIL.value}"
        stat = repo.get(stat_key)
        assert stat.notification_type == "Unknown"


class TestFailedNotificationsProjector:
    def setup_method(self):
        reset_channels()

    def teardown_method(self):
        reset_channels()

    def test_failed_notification_created(self):
        nid = _create_notification_and_log("cust-fail-proj-1")
        now = datetime.now(UTC)

        projector = FailedNotificationsProjector()
        projector.on_notification_failed(
            NotificationFailed(
                notification_id=nid,
                recipient_id="cust-fail-proj-1",
                channel=NotificationChannel.EMAIL.value,
                reason="SMTP timeout",
                retry_count=1,
                max_retries=3,
                failed_at=now,
            )
        )

        repo = current_domain.repository_for(FailedNotifications)
        failed = repo.get(nid)
        assert str(failed.notification_id) == nid
        assert failed.failure_reason == "SMTP timeout"
        assert failed.retry_count == 1

    def test_failed_notification_updated_on_second_failure(self):
        nid = _create_notification_and_log("cust-fail-proj-2")
        now = datetime.now(UTC)

        projector = FailedNotificationsProjector()
        # First failure
        projector.on_notification_failed(
            NotificationFailed(
                notification_id=nid,
                recipient_id="cust-fail-proj-2",
                channel=NotificationChannel.EMAIL.value,
                reason="First failure",
                retry_count=1,
                max_retries=3,
                failed_at=now,
            )
        )
        # Second failure (after retry)
        projector.on_notification_failed(
            NotificationFailed(
                notification_id=nid,
                recipient_id="cust-fail-proj-2",
                channel=NotificationChannel.EMAIL.value,
                reason="Second failure",
                retry_count=2,
                max_retries=3,
                failed_at=now,
            )
        )

        repo = current_domain.repository_for(FailedNotifications)
        failed = repo.get(nid)
        assert failed.failure_reason == "Second failure"
        assert failed.retry_count == 2

    def test_retried_notification_removed_from_queue(self):
        nid = _create_notification_and_log("cust-fail-proj-3")
        now = datetime.now(UTC)

        projector = FailedNotificationsProjector()
        # Add to failed queue
        projector.on_notification_failed(
            NotificationFailed(
                notification_id=nid,
                recipient_id="cust-fail-proj-3",
                channel=NotificationChannel.EMAIL.value,
                reason="Temporary failure",
                retry_count=1,
                max_retries=3,
                failed_at=now,
            )
        )
        # Retry — should remove from queue
        projector.on_notification_retried(
            NotificationRetried(
                notification_id=nid,
                recipient_id="cust-fail-proj-3",
                channel=NotificationChannel.EMAIL.value,
                retry_count=1,
                retried_at=now,
            )
        )

        repo = current_domain.repository_for(FailedNotifications)
        with pytest.raises(ObjectNotFoundError):
            repo.get(nid)

    def test_sent_notification_removed_from_failed_queue(self):
        nid = _create_notification_and_log("cust-fail-proj-4")
        now = datetime.now(UTC)

        projector = FailedNotificationsProjector()
        # Add to failed queue
        projector.on_notification_failed(
            NotificationFailed(
                notification_id=nid,
                recipient_id="cust-fail-proj-4",
                channel=NotificationChannel.EMAIL.value,
                reason="Temporary failure",
                retry_count=1,
                max_retries=3,
                failed_at=now,
            )
        )
        # Sent — should remove from queue
        projector.on_notification_sent(
            NotificationSent(
                notification_id=nid,
                recipient_id="cust-fail-proj-4",
                channel=NotificationChannel.EMAIL.value,
                sent_at=now,
            )
        )

        repo = current_domain.repository_for(FailedNotifications)
        with pytest.raises(ObjectNotFoundError):
            repo.get(nid)

    def test_retry_nonexistent_does_not_raise(self):
        projector = FailedNotificationsProjector()
        projector.on_notification_retried(
            NotificationRetried(
                notification_id="nonexistent-retry-id",
                recipient_id="x",
                channel=NotificationChannel.EMAIL.value,
                retry_count=1,
                retried_at=datetime.now(UTC),
            )
        )

    def test_sent_nonexistent_does_not_raise(self):
        projector = FailedNotificationsProjector()
        projector.on_notification_sent(
            NotificationSent(
                notification_id="nonexistent-sent-id",
                recipient_id="x",
                channel=NotificationChannel.EMAIL.value,
                sent_at=datetime.now(UTC),
            )
        )

    def test_failed_unknown_notification_type(self):
        """When the notification can't be loaded, type falls back to 'Unknown'."""
        now = datetime.now(UTC)
        projector = FailedNotificationsProjector()
        projector.on_notification_failed(
            NotificationFailed(
                notification_id="nonexistent-fail-id",
                recipient_id="x",
                channel=NotificationChannel.EMAIL.value,
                reason="Failure",
                retry_count=1,
                max_retries=3,
                failed_at=now,
            )
        )

        repo = current_domain.repository_for(FailedNotifications)
        failed = repo.get("nonexistent-fail-id")
        assert failed.notification_type == "Unknown"
