"""BDD tests for preference management."""

from notifications.preference.preference import NotificationPreference
from pytest_bdd import parsers, scenarios, when

scenarios("features/preference_management.feature")


@when("default preferences are created", target_fixture="preference")
def create_default_preferences(customer_id):
    return NotificationPreference.create_default(customer_id=customer_id)


@when("the customer enables SMS", target_fixture="preference")
def enable_sms(preference):
    preference.update_channels(sms=True)
    return preference


@when(
    parsers.cfparse('the customer sets quiet hours from "{start}" to "{end}"'),
    target_fixture="preference",
)
def set_quiet_hours(preference, start, end):
    preference.set_quiet_hours(start, end)
    return preference


@when(
    parsers.cfparse('the customer unsubscribes from "{notification_type}"'),
    target_fixture="preference",
)
def unsubscribe_from(preference, notification_type):
    preference.unsubscribe_from(notification_type)
    return preference
