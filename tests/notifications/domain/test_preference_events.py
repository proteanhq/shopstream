"""Tests for NotificationPreference domain events — verifying event structure and versioning."""

from notifications.preference.events import (
    ChannelsUpdated,
    PreferencesCreated,
    QuietHoursCleared,
    QuietHoursSet,
    TypeResubscribed,
    TypeUnsubscribed,
)


class TestPreferenceEventVersioning:
    def test_preferences_created_version(self):
        assert PreferencesCreated.__version__ == "v1"

    def test_channels_updated_version(self):
        assert ChannelsUpdated.__version__ == "v1"

    def test_quiet_hours_set_version(self):
        assert QuietHoursSet.__version__ == "v1"

    def test_quiet_hours_cleared_version(self):
        assert QuietHoursCleared.__version__ == "v1"

    def test_type_unsubscribed_version(self):
        assert TypeUnsubscribed.__version__ == "v1"

    def test_type_resubscribed_version(self):
        assert TypeResubscribed.__version__ == "v1"
