"""Application tests for Identity cross-domain subscribers.

Tests both the welcome notification subscriber and the preference auto-creation subscriber.
"""

from datetime import UTC, datetime

from protean import current_domain

from notifications.notification.identity_subscriber import IdentityEventsSubscriber
from notifications.notification.notification import (
    Notification,
    NotificationStatus,
    NotificationType,
)
from notifications.preference.identity_subscriber import PreferenceIdentitySubscriber
from notifications.preference.preference import NotificationPreference


def _build_message(event_type: str, data: dict) -> dict:
    """Build a broker message payload with metadata and data."""
    return {
        "data": data,
        "metadata": {"headers": {"type": event_type}},
    }


def _customer_registered_message(
    customer_id="cust-001", first_name="Alice", last_name="Smith", email="alice@example.com"
):
    return _build_message(
        "Identity.CustomerRegistered.v1",
        {
            "customer_id": customer_id,
            "external_id": f"ext-{customer_id}",
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
            "registered_at": datetime.now(UTC).isoformat(),
        },
    )


class TestWelcomeNotificationHandler:
    def test_welcome_notification_created(self):
        subscriber = IdentityEventsSubscriber()
        subscriber(_customer_registered_message())

        repo = current_domain.repository_for(Notification)
        notifications = (
            repo.query.filter(
                recipient_id="cust-001",
                notification_type=NotificationType.WELCOME.value,
            )
            .all()
            .items
        )
        assert len(notifications) >= 1

    def test_welcome_notification_is_sent(self):
        """After auto-dispatch, the notification status should be Sent."""
        subscriber = IdentityEventsSubscriber()
        subscriber(_customer_registered_message(customer_id="cust-welcome-1"))

        repo = current_domain.repository_for(Notification)
        notifications = (
            repo.query.filter(
                recipient_id="cust-welcome-1",
            )
            .all()
            .items
        )
        # Auto-dispatched by NotificationDispatcher
        assert notifications[0].status == NotificationStatus.SENT.value

    def test_welcome_uses_email_channel(self):
        subscriber = IdentityEventsSubscriber()
        subscriber(_customer_registered_message(customer_id="cust-welcome-2"))

        repo = current_domain.repository_for(Notification)
        notifications = (
            repo.query.filter(
                recipient_id="cust-welcome-2",
            )
            .all()
            .items
        )
        assert notifications[0].channel == "Email"

    def test_welcome_uses_first_name_in_subject(self):
        subscriber = IdentityEventsSubscriber()
        subscriber(_customer_registered_message(customer_id="cust-welcome-3", first_name="Bob"))

        repo = current_domain.repository_for(Notification)
        notifications = (
            repo.query.filter(
                recipient_id="cust-welcome-3",
            )
            .all()
            .items
        )
        assert "Bob" in notifications[0].subject


class TestPreferenceAutoCreationHandler:
    def test_creates_default_preferences(self):
        subscriber = PreferenceIdentitySubscriber()
        subscriber(_customer_registered_message(customer_id="cust-pref-1"))

        repo = current_domain.repository_for(NotificationPreference)
        prefs = repo.query.filter(customer_id="cust-pref-1").all().items
        assert len(prefs) == 1
        assert prefs[0].email_enabled is True
        assert prefs[0].sms_enabled is False

    def test_idempotent_creation(self):
        subscriber = PreferenceIdentitySubscriber()
        msg = _customer_registered_message(customer_id="cust-pref-2")
        subscriber(msg)
        # Fire again — should not create duplicates
        subscriber(msg)

        repo = current_domain.repository_for(NotificationPreference)
        prefs = repo.query.filter(customer_id="cust-pref-2").all().items
        assert len(prefs) == 1


class TestPreferenceQueryFailure:
    def test_creates_preference_when_query_fails(self):
        """When the preference query fails, subscriber creates a new preference anyway."""
        from unittest.mock import MagicMock, patch

        subscriber = PreferenceIdentitySubscriber()
        mock_repo = MagicMock(spec=[])  # spec=[] prevents auto-magic coroutine behavior
        mock_repo.query = MagicMock()
        mock_repo.query.filter.return_value.all.side_effect = Exception("DB error")
        mock_repo.add = MagicMock()

        with patch("notifications.preference.identity_subscriber.current_domain") as mock_domain:
            mock_domain.repository_for = MagicMock(return_value=mock_repo)

            mock_preference = MagicMock()
            mock_preference.id = "pref-mock-001"
            with patch("notifications.preference.identity_subscriber.NotificationPreference") as mock_pref_cls:
                mock_pref_cls.create_default = MagicMock(return_value=mock_preference)
                subscriber(_customer_registered_message(customer_id="cust-pref-fail"))
                mock_pref_cls.create_default.assert_called_once_with(customer_id="cust-pref-fail")
                mock_repo.add.assert_called_once()


class TestIgnoresUnrelatedIdentityEvents:
    def test_identity_subscriber_ignores_non_customer_registered(self):
        """Non-CustomerRegistered events on the identity stream should be ignored."""
        subscriber = IdentityEventsSubscriber()
        subscriber(_build_message("Identity.CustomerDeactivated.v1", {"customer_id": "cust-ignore"}))

    def test_preference_subscriber_ignores_non_customer_registered(self):
        """Non-CustomerRegistered events should be ignored by the preference subscriber."""
        subscriber = PreferenceIdentitySubscriber()
        subscriber(_build_message("Identity.CustomerDeactivated.v1", {"customer_id": "cust-ignore"}))
