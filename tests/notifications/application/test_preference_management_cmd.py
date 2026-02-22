"""Application tests for preference management command handlers."""

import json

import pytest
from notifications.preference.management import (
    ClearQuietHours,
    SetQuietHours,
    UpdateNotificationPreferences,
)
from notifications.preference.preference import NotificationPreference
from notifications.preference.subscription import ResubscribeToType, UnsubscribeFromType
from protean import current_domain
from protean.exceptions import ValidationError


def _create_preference(customer_id="cust-001"):
    pref = NotificationPreference.create_default(customer_id=customer_id)
    current_domain.repository_for(NotificationPreference).add(pref)
    return str(pref.customer_id)


# ---------------------------------------------------------------
# UpdateNotificationPreferences
# ---------------------------------------------------------------
class TestUpdatePreferencesCommand:
    def test_update_enables_sms(self):
        cid = _create_preference()
        current_domain.process(
            UpdateNotificationPreferences(customer_id=cid, sms_enabled=True),
            asynchronous=False,
        )
        repo = current_domain.repository_for(NotificationPreference)
        prefs = repo._dao.query.filter(customer_id=cid).all().items
        assert prefs[0].sms_enabled is True

    def test_update_disables_email(self):
        cid = _create_preference()
        current_domain.process(
            UpdateNotificationPreferences(customer_id=cid, email_enabled=False),
            asynchronous=False,
        )
        repo = current_domain.repository_for(NotificationPreference)
        prefs = repo._dao.query.filter(customer_id=cid).all().items
        assert prefs[0].email_enabled is False

    def test_update_enables_push(self):
        cid = _create_preference()
        current_domain.process(
            UpdateNotificationPreferences(customer_id=cid, push_enabled=True),
            asynchronous=False,
        )
        repo = current_domain.repository_for(NotificationPreference)
        prefs = repo._dao.query.filter(customer_id=cid).all().items
        assert prefs[0].push_enabled is True


# ---------------------------------------------------------------
# SetQuietHours / ClearQuietHours
# ---------------------------------------------------------------
class TestQuietHoursCommands:
    def test_set_quiet_hours(self):
        cid = _create_preference()
        current_domain.process(
            SetQuietHours(customer_id=cid, start="22:00", end="08:00"),
            asynchronous=False,
        )
        repo = current_domain.repository_for(NotificationPreference)
        prefs = repo._dao.query.filter(customer_id=cid).all().items
        assert prefs[0].quiet_hours_start == "22:00"
        assert prefs[0].quiet_hours_end == "08:00"

    def test_clear_quiet_hours(self):
        cid = _create_preference()
        current_domain.process(
            SetQuietHours(customer_id=cid, start="22:00", end="08:00"),
            asynchronous=False,
        )
        current_domain.process(
            ClearQuietHours(customer_id=cid),
            asynchronous=False,
        )
        repo = current_domain.repository_for(NotificationPreference)
        prefs = repo._dao.query.filter(customer_id=cid).all().items
        assert prefs[0].quiet_hours_start is None
        assert prefs[0].quiet_hours_end is None


# ---------------------------------------------------------------
# UnsubscribeFromType / ResubscribeToType
# ---------------------------------------------------------------
class TestSubscriptionCommands:
    def test_unsubscribe_from_type(self):
        cid = _create_preference()
        current_domain.process(
            UnsubscribeFromType(customer_id=cid, notification_type="CartRecovery"),
            asynchronous=False,
        )
        repo = current_domain.repository_for(NotificationPreference)
        prefs = repo._dao.query.filter(customer_id=cid).all().items
        types = json.loads(prefs[0].unsubscribed_types)
        assert "CartRecovery" in types

    def test_resubscribe_to_type(self):
        cid = _create_preference()
        current_domain.process(
            UnsubscribeFromType(customer_id=cid, notification_type="CartRecovery"),
            asynchronous=False,
        )
        current_domain.process(
            ResubscribeToType(customer_id=cid, notification_type="CartRecovery"),
            asynchronous=False,
        )
        repo = current_domain.repository_for(NotificationPreference)
        prefs = repo._dao.query.filter(customer_id=cid).all().items
        types = json.loads(prefs[0].unsubscribed_types)
        assert "CartRecovery" not in types

    def test_cannot_unsubscribe_twice(self):
        cid = _create_preference()
        current_domain.process(
            UnsubscribeFromType(customer_id=cid, notification_type="CartRecovery"),
            asynchronous=False,
        )
        with pytest.raises(ValidationError):
            current_domain.process(
                UnsubscribeFromType(customer_id=cid, notification_type="CartRecovery"),
                asynchronous=False,
            )

    def test_cannot_resubscribe_if_not_unsubscribed(self):
        cid = _create_preference()
        with pytest.raises(ValidationError):
            current_domain.process(
                ResubscribeToType(customer_id=cid, notification_type="CartRecovery"),
                asynchronous=False,
            )
