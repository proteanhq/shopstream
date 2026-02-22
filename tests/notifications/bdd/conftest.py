"""Shared BDD fixtures and step definitions for the Notifications domain."""

import pytest
from notifications.notification.events import (
    NotificationCancelled,
    NotificationCreated,
    NotificationRetried,
    NotificationSent,
)
from notifications.notification.notification import (
    Notification,
    NotificationChannel,
    NotificationType,
)
from notifications.preference.preference import NotificationPreference
from pytest_bdd import given, parsers, then

_NOTIFICATION_EVENT_CLASSES = {
    "NotificationCreated": NotificationCreated,
    "NotificationSent": NotificationSent,
    "NotificationCancelled": NotificationCancelled,
    "NotificationRetried": NotificationRetried,
}


@pytest.fixture()
def error():
    """Container for captured validation errors."""
    return {"exc": None}


# ---------------------------------------------------------------------------
# Given steps — notifications
# ---------------------------------------------------------------------------
@given(
    parsers.cfparse('a new notification for customer "{customer_id}"'),
    target_fixture="notification",
)
def new_notification(customer_id):
    return Notification.create(
        recipient_id=customer_id,
        notification_type=NotificationType.WELCOME.value,
        channel=NotificationChannel.EMAIL.value,
        body="Welcome to ShopStream!",
    )


@given("a pending notification", target_fixture="notification")
def pending_notification():
    n = Notification.create(
        recipient_id="cust-bdd",
        notification_type=NotificationType.WELCOME.value,
        channel=NotificationChannel.EMAIL.value,
        body="Welcome!",
    )
    n._events.clear()
    return n


@given("a sent notification", target_fixture="notification")
def sent_notification():
    n = Notification.create(
        recipient_id="cust-bdd",
        notification_type=NotificationType.WELCOME.value,
        channel=NotificationChannel.EMAIL.value,
        body="Welcome!",
    )
    n._events.clear()
    n.mark_sent()
    n._events.clear()
    return n


@given("a failed notification", target_fixture="notification")
def failed_notification():
    n = Notification.create(
        recipient_id="cust-bdd",
        notification_type=NotificationType.WELCOME.value,
        channel=NotificationChannel.EMAIL.value,
        body="Welcome!",
    )
    n._events.clear()
    n.mark_failed("Delivery error")
    n._events.clear()
    return n


# ---------------------------------------------------------------------------
# Given steps — preferences
# ---------------------------------------------------------------------------
@given(
    parsers.cfparse('a new customer "{customer_id}"'),
    target_fixture="customer_id",
)
def new_customer(customer_id):
    return customer_id


@given("a customer with default preferences", target_fixture="preference")
def customer_with_default_prefs():
    pref = NotificationPreference.create_default(customer_id="cust-bdd-pref")
    pref._events.clear()
    return pref


# ---------------------------------------------------------------------------
# Then steps — notification status & events
# ---------------------------------------------------------------------------
@then(parsers.cfparse('the notification status is "{status}"'))
def notification_status_is(notification, status):
    assert notification.status == status


@then(parsers.cfparse("a {event_type} event is raised"))
def notification_event_raised(notification, event_type):
    event_cls = _NOTIFICATION_EVENT_CLASSES[event_type]
    assert any(
        isinstance(e, event_cls) for e in notification._events
    ), f"No {event_type} event found. Events: {[type(e).__name__ for e in notification._events]}"


# ---------------------------------------------------------------------------
# Then steps — preferences
# ---------------------------------------------------------------------------
@then("email is enabled")
def email_enabled(preference):
    assert preference.email_enabled is True


@then("SMS is disabled")
def sms_disabled(preference):
    assert preference.sms_enabled is False


@then("push is disabled")
def push_disabled(preference):
    assert preference.push_enabled is False


@then("SMS is enabled")
def sms_enabled(preference):
    assert preference.sms_enabled is True


@then(parsers.cfparse('quiet hours are set to "{start}" - "{end}"'))
def quiet_hours_set(preference, start, end):
    assert preference.quiet_hours_start == start
    assert preference.quiet_hours_end == end


@then(parsers.cfparse('the customer is not subscribed to "{notification_type}"'))
def not_subscribed(preference, notification_type):
    assert preference.is_subscribed_to(notification_type) is False
