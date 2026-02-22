"""Tests for error/exception handling paths in production-safety code.

These paths handle infrastructure failures (DB errors, etc.) that can't
occur with in-memory adapters. We patch at the module level to simulate failures.
"""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

from notifications.channel import reset_channels
from notifications.notification.notification import (
    NotificationType,
)
from notifications.preference.preference import NotificationPreference
from protean import current_domain


class TestHelpersPreferenceLookupFailure:
    def setup_method(self):
        reset_channels()

    def teardown_method(self):
        reset_channels()

    def test_preference_query_exception_uses_email_default(self):
        """When preference lookup raises, fall back to email-only default."""
        real_repo_for = current_domain.repository_for

        def mock_repo_for(cls):
            if cls is NotificationPreference:
                mock_repo = MagicMock()
                mock_repo._dao.query.filter.side_effect = RuntimeError("DB failed")
                return mock_repo
            return real_repo_for(cls)

        with patch(
            "notifications.notification.helpers.current_domain",
        ) as mock_domain:
            mock_domain.repository_for = mock_repo_for

            from notifications.notification.helpers import create_notifications_for_customer

            nids = create_notifications_for_customer(
                customer_id="cust-db-fail",
                notification_type=NotificationType.WELCOME.value,
                context={"customer_name": "Test"},
            )
            # Should still create notification using email default
            assert len(nids) >= 1


class TestSchedulerErrorPaths:
    def setup_method(self):
        reset_channels()

    def teardown_method(self):
        reset_channels()

    def test_query_exception_returns_gracefully(self):
        """When the pending query fails, handler logs and returns."""
        from notifications.notification.scheduler import ProcessScheduledNotificationsHandler

        handler = ProcessScheduledNotificationsHandler()

        mock_repo = MagicMock()
        mock_repo._dao.query.filter.side_effect = RuntimeError("DB error")

        with patch("notifications.notification.scheduler.current_domain") as mock_domain:
            mock_domain.repository_for.return_value = mock_repo

            from notifications.notification.scheduler import ProcessScheduledNotifications

            command = ProcessScheduledNotifications(as_of=datetime.now(UTC))
            handler.process_scheduled(command)
            # Should not raise — hits the except branch

    def test_skips_non_scheduled_pending(self):
        """PENDING notifications without scheduled_for are skipped by the scheduler."""
        from notifications.notification.scheduler import ProcessScheduledNotificationsHandler

        handler = ProcessScheduledNotificationsHandler()

        # Create a mock notification that is PENDING with no scheduled_for
        mock_notification = MagicMock()
        mock_notification.scheduled_for = None
        mock_notification.status = "Pending"

        mock_repo = MagicMock()
        mock_repo._dao.query.filter.return_value.all.return_value.items = [mock_notification]

        with patch("notifications.notification.scheduler.current_domain") as mock_domain:
            mock_domain.repository_for.return_value = mock_repo

            from notifications.notification.scheduler import ProcessScheduledNotifications

            command = ProcessScheduledNotifications(as_of=datetime.now(UTC))
            handler.process_scheduled(command)
            # Should skip the notification (scheduled_for is None → continue)
            # repo.add should not be called for the notification
            mock_repo.add.assert_not_called()
