"""Tests for Notification domain events — verifying event structure and versioning."""

from notifications.notification.events import (
    NotificationBounced,
    NotificationCancelled,
    NotificationCreated,
    NotificationDelivered,
    NotificationFailed,
    NotificationRetried,
    NotificationSent,
)


class TestEventVersioning:
    def test_notification_created_version(self):
        assert NotificationCreated.__version__ == "v1"

    def test_notification_sent_version(self):
        assert NotificationSent.__version__ == "v1"

    def test_notification_delivered_version(self):
        assert NotificationDelivered.__version__ == "v1"

    def test_notification_failed_version(self):
        assert NotificationFailed.__version__ == "v1"

    def test_notification_bounced_version(self):
        assert NotificationBounced.__version__ == "v1"

    def test_notification_cancelled_version(self):
        assert NotificationCancelled.__version__ == "v1"

    def test_notification_retried_version(self):
        assert NotificationRetried.__version__ == "v1"
