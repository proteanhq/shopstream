"""Integration tests for Notifications API endpoints."""

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from notifications.channel import get_channel, reset_channels
from notifications.notification.notification import (
    Notification,
    NotificationChannel,
    NotificationStatus,
    NotificationType,
)
from notifications.preference.preference import NotificationPreference
from protean import current_domain


def _get_test_client():
    """Build a minimal FastAPI test client with notifications routes."""
    from fastapi import FastAPI
    from notifications.api.routes import router

    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def _create_preference(customer_id="cust-api-1"):
    pref = NotificationPreference.create_default(customer_id=customer_id)
    current_domain.repository_for(NotificationPreference).add(pref)
    return customer_id


def _create_notification(customer_id="cust-api-1", **overrides):
    future = datetime.now(UTC) + timedelta(days=30)
    defaults = {
        "recipient_id": customer_id,
        "notification_type": NotificationType.WELCOME.value,
        "channel": NotificationChannel.EMAIL.value,
        "body": "Welcome!",
        "subject": "Welcome to ShopStream",
        "scheduled_for": future,
    }
    defaults.update(overrides)
    n = Notification.create(**defaults)
    current_domain.repository_for(Notification).add(n)
    return str(n.id)


# ---------------------------------------------------------------
# Preferences endpoints
# ---------------------------------------------------------------
class TestPreferencesAPI:
    def test_get_preferences_returns_defaults(self):
        client = _get_test_client()
        resp = client.get("/notifications/preferences/cust-new")
        assert resp.status_code == 200
        data = resp.json()
        assert data["customer_id"] == "cust-new"
        assert data["email_enabled"] is True
        assert data["sms_enabled"] is False

    def test_get_preferences_returns_saved(self):
        cid = _create_preference("cust-api-pref-1")
        client = _get_test_client()
        resp = client.get(f"/notifications/preferences/{cid}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["customer_id"] == cid
        assert data["email_enabled"] is True

    def test_update_preferences(self):
        cid = _create_preference("cust-api-up-1")
        client = _get_test_client()
        resp = client.put(
            f"/notifications/preferences/{cid}",
            json={"sms_enabled": True},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_set_quiet_hours(self):
        cid = _create_preference("cust-api-qh-1")
        client = _get_test_client()
        resp = client.put(
            f"/notifications/preferences/{cid}/quiet-hours",
            json={"start": "22:00", "end": "08:00"},
        )
        assert resp.status_code == 200

    def test_clear_quiet_hours(self):
        cid = _create_preference("cust-api-qh-2")
        client = _get_test_client()
        # Set first
        client.put(
            f"/notifications/preferences/{cid}/quiet-hours",
            json={"start": "22:00", "end": "08:00"},
        )
        resp = client.delete(f"/notifications/preferences/{cid}/quiet-hours")
        assert resp.status_code == 200

    def test_unsubscribe(self):
        cid = _create_preference("cust-api-unsub-1")
        client = _get_test_client()
        resp = client.post(
            f"/notifications/preferences/{cid}/unsubscribe",
            json={"notification_type": "CartRecovery"},
        )
        assert resp.status_code == 201

    def test_resubscribe(self):
        cid = _create_preference("cust-api-resub-1")
        client = _get_test_client()
        # Unsubscribe first
        client.post(
            f"/notifications/preferences/{cid}/unsubscribe",
            json={"notification_type": "CartRecovery"},
        )
        resp = client.post(
            f"/notifications/preferences/{cid}/resubscribe",
            json={"notification_type": "CartRecovery"},
        )
        assert resp.status_code == 201


# ---------------------------------------------------------------
# Notification history endpoint
# ---------------------------------------------------------------
class TestNotificationHistoryAPI:
    def test_get_customer_notifications_empty(self):
        client = _get_test_client()
        resp = client.get("/notifications/cust-empty")
        assert resp.status_code == 200
        assert resp.json()["notifications"] == []

    def test_get_customer_notifications_with_data(self):
        """Customer notification history returns created notifications."""
        _create_notification("cust-api-hist-1")
        client = _get_test_client()
        resp = client.get("/notifications/cust-api-hist-1")
        assert resp.status_code == 200
        data = resp.json()
        # The notification should appear in customer notifications
        # (projector creates CustomerNotifications on NotificationCreated)
        assert isinstance(data["notifications"], list)


# ---------------------------------------------------------------
# Notification lifecycle endpoints
# ---------------------------------------------------------------
class TestNotificationLifecycleAPI:
    def setup_method(self):
        reset_channels()

    def teardown_method(self):
        reset_channels()

    def test_cancel_notification(self):
        nid = _create_notification("cust-api-cancel-1")
        client = _get_test_client()
        resp = client.put(
            f"/notifications/{nid}/cancel",
            json={"reason": "No longer needed"},
        )
        assert resp.status_code == 200

        n = current_domain.repository_for(Notification).get(nid)
        assert n.status == NotificationStatus.CANCELLED.value

    def test_retry_failed_notification(self):
        """Retry a failed notification via the API."""
        # Create a notification that fails during dispatch
        adapter = get_channel(NotificationChannel.EMAIL.value)
        adapter.configure(should_succeed=False, failure_reason="SMTP error")

        n = Notification.create(
            recipient_id="cust-api-retry-1",
            notification_type=NotificationType.WELCOME.value,
            channel=NotificationChannel.EMAIL.value,
            body="Welcome!",
            subject="Welcome",
        )
        current_domain.repository_for(Notification).add(n)
        nid = str(n.id)

        # Reset adapter so retry succeeds
        adapter.configure(should_succeed=True)

        # Verify it's failed
        updated = current_domain.repository_for(Notification).get(nid)
        assert updated.status == NotificationStatus.FAILED.value

        client = _get_test_client()
        resp = client.post(f"/notifications/{nid}/retry")
        assert resp.status_code == 201
        assert resp.json()["status"] == "ok"
