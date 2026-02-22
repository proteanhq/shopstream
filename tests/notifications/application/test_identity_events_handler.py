"""Application tests for Identity cross-domain event handlers.

Tests both the welcome notification handler and the preference auto-creation handler.
"""

from datetime import UTC, datetime

from notifications.notification.identity_events import IdentityEventsHandler
from notifications.notification.notification import (
    Notification,
    NotificationStatus,
    NotificationType,
)
from notifications.preference.identity_events import PreferenceIdentityEventsHandler
from notifications.preference.preference import NotificationPreference
from protean import current_domain
from shared.events.identity import CustomerRegistered


def _fire_customer_registered(customer_id="cust-001", first_name="Alice", last_name="Smith", email="alice@example.com"):
    event = CustomerRegistered(
        customer_id=customer_id,
        external_id=f"ext-{customer_id}",
        first_name=first_name,
        last_name=last_name,
        email=email,
        registered_at=datetime.now(UTC),
    )
    return event


class TestWelcomeNotificationHandler:
    def test_welcome_notification_created(self):
        event = _fire_customer_registered()
        handler = IdentityEventsHandler()
        handler.on_customer_registered(event)

        repo = current_domain.repository_for(Notification)
        notifications = (
            repo._dao.query.filter(
                recipient_id="cust-001",
                notification_type=NotificationType.WELCOME.value,
            )
            .all()
            .items
        )
        assert len(notifications) >= 1

    def test_welcome_notification_is_sent(self):
        """After auto-dispatch, the notification status should be Sent."""
        event = _fire_customer_registered(customer_id="cust-welcome-1")
        handler = IdentityEventsHandler()
        handler.on_customer_registered(event)

        repo = current_domain.repository_for(Notification)
        notifications = (
            repo._dao.query.filter(
                recipient_id="cust-welcome-1",
            )
            .all()
            .items
        )
        # Auto-dispatched by NotificationDispatcher
        assert notifications[0].status == NotificationStatus.SENT.value

    def test_welcome_uses_email_channel(self):
        event = _fire_customer_registered(customer_id="cust-welcome-2")
        handler = IdentityEventsHandler()
        handler.on_customer_registered(event)

        repo = current_domain.repository_for(Notification)
        notifications = (
            repo._dao.query.filter(
                recipient_id="cust-welcome-2",
            )
            .all()
            .items
        )
        assert notifications[0].channel == "Email"

    def test_welcome_uses_first_name_in_subject(self):
        event = _fire_customer_registered(customer_id="cust-welcome-3", first_name="Bob")
        handler = IdentityEventsHandler()
        handler.on_customer_registered(event)

        repo = current_domain.repository_for(Notification)
        notifications = (
            repo._dao.query.filter(
                recipient_id="cust-welcome-3",
            )
            .all()
            .items
        )
        assert "Bob" in notifications[0].subject


class TestPreferenceAutoCreationHandler:
    def test_creates_default_preferences(self):
        event = _fire_customer_registered(customer_id="cust-pref-1")
        handler = PreferenceIdentityEventsHandler()
        handler.on_customer_registered(event)

        repo = current_domain.repository_for(NotificationPreference)
        prefs = repo._dao.query.filter(customer_id="cust-pref-1").all().items
        assert len(prefs) == 1
        assert prefs[0].email_enabled is True
        assert prefs[0].sms_enabled is False

    def test_idempotent_creation(self):
        event = _fire_customer_registered(customer_id="cust-pref-2")
        handler = PreferenceIdentityEventsHandler()
        handler.on_customer_registered(event)
        # Fire again — should not create duplicates
        handler.on_customer_registered(event)

        repo = current_domain.repository_for(NotificationPreference)
        prefs = repo._dao.query.filter(customer_id="cust-pref-2").all().items
        assert len(prefs) == 1
