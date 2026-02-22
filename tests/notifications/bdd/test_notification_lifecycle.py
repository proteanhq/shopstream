"""BDD tests for notification lifecycle."""

from pytest_bdd import parsers, scenarios, when

scenarios("features/notification_lifecycle.feature")


@when(
    "the notification is marked as sent",
    target_fixture="notification",
)
def mark_sent(notification):
    notification.mark_sent()
    return notification


@when(
    "the notification is marked as delivered",
    target_fixture="notification",
)
def mark_delivered(notification):
    notification.mark_delivered()
    return notification


@when(
    parsers.cfparse('the notification is cancelled with reason "{reason}"'),
    target_fixture="notification",
)
def cancel_notification(notification, reason):
    notification.cancel(reason)
    return notification


@when(
    "the notification is retried",
    target_fixture="notification",
)
def retry_notification(notification):
    notification.retry()
    return notification
