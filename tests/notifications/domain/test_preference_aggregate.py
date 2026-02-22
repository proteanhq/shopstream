"""Tests for NotificationPreference aggregate creation and behavior."""

import json

import pytest
from notifications.preference.preference import NotificationPreference
from protean.exceptions import ValidationError


def _make_preference(**overrides):
    defaults = {"customer_id": "cust-001"}
    defaults.update(overrides)
    return NotificationPreference.create_default(**defaults)


# ---------------------------------------------------------------
# Factory
# ---------------------------------------------------------------
class TestPreferenceCreation:
    def test_create_default_sets_id(self):
        pref = _make_preference()
        assert pref.id is not None

    def test_create_default_sets_customer_id(self):
        pref = _make_preference(customer_id="cust-42")
        assert str(pref.customer_id) == "cust-42"

    def test_create_default_enables_email(self):
        pref = _make_preference()
        assert pref.email_enabled is True

    def test_create_default_disables_sms(self):
        pref = _make_preference()
        assert pref.sms_enabled is False

    def test_create_default_disables_push(self):
        pref = _make_preference()
        assert pref.push_enabled is False

    def test_create_default_sets_empty_unsubscribed_types(self):
        pref = _make_preference()
        assert json.loads(pref.unsubscribed_types) == []

    def test_create_default_sets_no_quiet_hours(self):
        pref = _make_preference()
        assert pref.quiet_hours_start is None
        assert pref.quiet_hours_end is None

    def test_create_default_sets_timestamps(self):
        pref = _make_preference()
        assert pref.created_at is not None
        assert pref.updated_at is not None

    def test_create_default_raises_preferences_created_event(self):
        pref = _make_preference()
        assert len(pref._events) == 1
        event = pref._events[0]
        assert event.__class__.__name__ == "PreferencesCreated"
        assert str(event.preference_id) == str(pref.id)
        assert str(event.customer_id) == str(pref.customer_id)
        assert event.email_enabled is True
        assert event.sms_enabled is False
        assert event.push_enabled is False


# ---------------------------------------------------------------
# Channel management
# ---------------------------------------------------------------
class TestUpdateChannels:
    def test_enable_sms(self):
        pref = _make_preference()
        pref._events.clear()
        pref.update_channels(sms=True)
        assert pref.sms_enabled is True

    def test_enable_push(self):
        pref = _make_preference()
        pref._events.clear()
        pref.update_channels(push=True)
        assert pref.push_enabled is True

    def test_disable_email(self):
        pref = _make_preference()
        pref._events.clear()
        pref.update_channels(email=False)
        assert pref.email_enabled is False

    def test_update_multiple_channels(self):
        pref = _make_preference()
        pref._events.clear()
        pref.update_channels(email=False, sms=True, push=True)
        assert pref.email_enabled is False
        assert pref.sms_enabled is True
        assert pref.push_enabled is True

    def test_update_channels_none_leaves_unchanged(self):
        pref = _make_preference()
        pref._events.clear()
        pref.update_channels(sms=True)
        # email should still be True (default)
        assert pref.email_enabled is True

    def test_update_channels_raises_event(self):
        pref = _make_preference()
        pref._events.clear()
        pref.update_channels(sms=True)
        assert len(pref._events) == 1
        event = pref._events[0]
        assert event.__class__.__name__ == "ChannelsUpdated"
        assert event.sms_enabled is True

    def test_update_channels_requires_at_least_one(self):
        pref = _make_preference()
        pref._events.clear()
        with pytest.raises(ValidationError) as exc:
            pref.update_channels()
        assert "At least one channel" in str(exc.value)

    def test_update_channels_updates_timestamp(self):
        pref = _make_preference()
        old_updated = pref.updated_at
        pref._events.clear()
        pref.update_channels(push=True)
        assert pref.updated_at >= old_updated


# ---------------------------------------------------------------
# Quiet hours
# ---------------------------------------------------------------
class TestQuietHours:
    def test_set_quiet_hours(self):
        pref = _make_preference()
        pref._events.clear()
        pref.set_quiet_hours("22:00", "08:00")
        assert pref.quiet_hours_start == "22:00"
        assert pref.quiet_hours_end == "08:00"

    def test_set_quiet_hours_raises_event(self):
        pref = _make_preference()
        pref._events.clear()
        pref.set_quiet_hours("23:00", "07:00")
        assert len(pref._events) == 1
        event = pref._events[0]
        assert event.__class__.__name__ == "QuietHoursSet"
        assert event.start == "23:00"
        assert event.end == "07:00"

    def test_clear_quiet_hours(self):
        pref = _make_preference()
        pref._events.clear()
        pref.set_quiet_hours("22:00", "08:00")
        pref._events.clear()
        pref.clear_quiet_hours()
        assert pref.quiet_hours_start is None
        assert pref.quiet_hours_end is None

    def test_clear_quiet_hours_raises_event(self):
        pref = _make_preference()
        pref._events.clear()
        pref.set_quiet_hours("22:00", "08:00")
        pref._events.clear()
        pref.clear_quiet_hours()
        assert len(pref._events) == 1
        event = pref._events[0]
        assert event.__class__.__name__ == "QuietHoursCleared"

    def test_set_quiet_hours_requires_both(self):
        pref = _make_preference()
        pref._events.clear()
        with pytest.raises(ValidationError) as exc:
            pref.set_quiet_hours("22:00", "")
        assert "Both start and end" in str(exc.value)

    def test_set_quiet_hours_requires_start(self):
        pref = _make_preference()
        pref._events.clear()
        with pytest.raises(ValidationError) as exc:
            pref.set_quiet_hours("", "08:00")
        assert "Both start and end" in str(exc.value)

    def test_set_quiet_hours_invalid_format(self):
        pref = _make_preference()
        pref._events.clear()
        with pytest.raises(ValidationError) as exc:
            pref.set_quiet_hours("25:00", "08:00")
        assert "Invalid time format" in str(exc.value)

    def test_set_quiet_hours_invalid_minutes(self):
        pref = _make_preference()
        pref._events.clear()
        with pytest.raises(ValidationError) as exc:
            pref.set_quiet_hours("22:60", "08:00")
        assert "Invalid time format" in str(exc.value)

    def test_set_quiet_hours_non_numeric(self):
        pref = _make_preference()
        pref._events.clear()
        with pytest.raises(ValidationError) as exc:
            pref.set_quiet_hours("ab:cd", "08:00")
        assert "Invalid time format" in str(exc.value)

    def test_set_quiet_hours_bad_separator(self):
        pref = _make_preference()
        pref._events.clear()
        with pytest.raises(ValidationError) as exc:
            pref.set_quiet_hours("2200", "08:00")
        assert "Invalid time format" in str(exc.value)


# ---------------------------------------------------------------
# Per-type unsubscribe
# ---------------------------------------------------------------
class TestTypeSubscription:
    def test_unsubscribe_from_type(self):
        pref = _make_preference()
        pref._events.clear()
        pref.unsubscribe_from("CartRecovery")
        types = json.loads(pref.unsubscribed_types)
        assert "CartRecovery" in types

    def test_unsubscribe_raises_event(self):
        pref = _make_preference()
        pref._events.clear()
        pref.unsubscribe_from("CartRecovery")
        assert len(pref._events) == 1
        event = pref._events[0]
        assert event.__class__.__name__ == "TypeUnsubscribed"
        assert event.notification_type == "CartRecovery"

    def test_cannot_unsubscribe_twice(self):
        pref = _make_preference()
        pref._events.clear()
        pref.unsubscribe_from("CartRecovery")
        pref._events.clear()
        with pytest.raises(ValidationError) as exc:
            pref.unsubscribe_from("CartRecovery")
        assert "Already unsubscribed" in str(exc.value)

    def test_resubscribe_to_type(self):
        pref = _make_preference()
        pref._events.clear()
        pref.unsubscribe_from("CartRecovery")
        pref._events.clear()
        pref.resubscribe_to("CartRecovery")
        types = json.loads(pref.unsubscribed_types)
        assert "CartRecovery" not in types

    def test_resubscribe_raises_event(self):
        pref = _make_preference()
        pref._events.clear()
        pref.unsubscribe_from("CartRecovery")
        pref._events.clear()
        pref.resubscribe_to("CartRecovery")
        assert len(pref._events) == 1
        event = pref._events[0]
        assert event.__class__.__name__ == "TypeResubscribed"
        assert event.notification_type == "CartRecovery"

    def test_cannot_resubscribe_if_not_unsubscribed(self):
        pref = _make_preference()
        pref._events.clear()
        with pytest.raises(ValidationError) as exc:
            pref.resubscribe_to("CartRecovery")
        assert "Not currently unsubscribed" in str(exc.value)

    def test_multiple_unsubscribes(self):
        pref = _make_preference()
        pref._events.clear()
        pref.unsubscribe_from("CartRecovery")
        pref._events.clear()
        pref.unsubscribe_from("ReviewPrompt")
        types = json.loads(pref.unsubscribed_types)
        assert "CartRecovery" in types
        assert "ReviewPrompt" in types


# ---------------------------------------------------------------
# Query helpers
# ---------------------------------------------------------------
class TestQueryHelpers:
    def test_is_subscribed_to_by_default(self):
        pref = _make_preference()
        assert pref.is_subscribed_to("Welcome") is True

    def test_is_not_subscribed_after_unsubscribe(self):
        pref = _make_preference()
        pref.unsubscribe_from("CartRecovery")
        assert pref.is_subscribed_to("CartRecovery") is False

    def test_is_subscribed_after_resubscribe(self):
        pref = _make_preference()
        pref.unsubscribe_from("CartRecovery")
        pref.resubscribe_to("CartRecovery")
        assert pref.is_subscribed_to("CartRecovery") is True

    def test_get_enabled_channels_default(self):
        pref = _make_preference()
        channels = pref.get_enabled_channels()
        assert channels == ["Email"]

    def test_get_enabled_channels_all(self):
        pref = _make_preference()
        pref.update_channels(sms=True, push=True)
        channels = pref.get_enabled_channels()
        assert "Email" in channels
        assert "SMS" in channels
        assert "Push" in channels

    def test_get_enabled_channels_none(self):
        pref = _make_preference()
        pref.update_channels(email=False)
        channels = pref.get_enabled_channels()
        assert channels == []
