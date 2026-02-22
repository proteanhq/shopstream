"""Tests for Notification aggregate creation and structure."""

from datetime import UTC, datetime, timedelta

from notifications.notification.notification import (
    Notification,
    NotificationChannel,
    NotificationStatus,
    NotificationType,
    RecipientType,
)


def _make_notification(**overrides):
    defaults = {
        "recipient_id": "cust-001",
        "notification_type": NotificationType.WELCOME.value,
        "channel": NotificationChannel.EMAIL.value,
        "body": "Welcome to ShopStream!",
    }
    defaults.update(overrides)
    return Notification.create(**defaults)


class TestNotificationCreation:
    def test_create_sets_id(self):
        n = _make_notification()
        assert n.id is not None

    def test_create_sets_recipient(self):
        n = _make_notification(recipient_id="cust-123")
        assert str(n.recipient_id) == "cust-123"

    def test_create_defaults_to_customer_recipient_type(self):
        n = _make_notification()
        assert n.recipient_type == RecipientType.CUSTOMER.value

    def test_create_with_internal_recipient_type(self):
        n = _make_notification(recipient_type=RecipientType.INTERNAL.value)
        assert n.recipient_type == RecipientType.INTERNAL.value

    def test_create_sets_notification_type(self):
        n = _make_notification(notification_type=NotificationType.ORDER_CONFIRMATION.value)
        assert n.notification_type == NotificationType.ORDER_CONFIRMATION.value

    def test_create_sets_channel(self):
        n = _make_notification(channel=NotificationChannel.SMS.value)
        assert n.channel == NotificationChannel.SMS.value

    def test_create_sets_body(self):
        n = _make_notification(body="Test notification body")
        assert n.body == "Test notification body"

    def test_create_sets_subject(self):
        n = _make_notification(subject="Test Subject")
        assert n.subject == "Test Subject"

    def test_create_defaults_subject_to_none(self):
        n = _make_notification()
        assert n.subject is None

    def test_create_sets_pending_status(self):
        n = _make_notification()
        assert n.status == NotificationStatus.PENDING.value

    def test_create_sets_timestamps(self):
        n = _make_notification()
        assert n.created_at is not None
        assert n.updated_at is not None

    def test_create_defaults_retry_count_to_zero(self):
        n = _make_notification()
        assert n.retry_count == 0

    def test_create_defaults_max_retries_to_three(self):
        n = _make_notification()
        assert n.max_retries == 3

    def test_create_with_custom_max_retries(self):
        n = _make_notification(max_retries=5)
        assert n.max_retries == 5


class TestNotificationOptionalFields:
    def test_create_with_template_name(self):
        n = _make_notification(template_name="WelcomeTemplate")
        assert n.template_name == "WelcomeTemplate"

    def test_create_with_source_event_type(self):
        n = _make_notification(source_event_type="Identity.CustomerRegistered.v1")
        assert n.source_event_type == "Identity.CustomerRegistered.v1"

    def test_create_with_source_event_id(self):
        n = _make_notification(source_event_id="evt-abc-123")
        assert n.source_event_id == "evt-abc-123"

    def test_create_with_context_data(self):
        n = _make_notification(context_data='{"first_name": "John"}')
        assert n.context_data == '{"first_name": "John"}'

    def test_create_with_scheduled_for(self):
        future = datetime.now(UTC) + timedelta(days=7)
        n = _make_notification(scheduled_for=future)
        assert n.scheduled_for == future

    def test_create_without_scheduled_for(self):
        n = _make_notification()
        assert n.scheduled_for is None


class TestNotificationCreatedEvent:
    def test_create_raises_notification_created_event(self):
        n = _make_notification()
        assert len(n._events) == 1
        event = n._events[0]
        assert event.__class__.__name__ == "NotificationCreated"

    def test_event_contains_notification_id(self):
        n = _make_notification()
        event = n._events[0]
        assert str(event.notification_id) == str(n.id)

    def test_event_contains_recipient_info(self):
        n = _make_notification(recipient_id="cust-42")
        event = n._events[0]
        assert str(event.recipient_id) == "cust-42"
        assert event.recipient_type == RecipientType.CUSTOMER.value

    def test_event_contains_type_and_channel(self):
        n = _make_notification(
            notification_type=NotificationType.PAYMENT_RECEIPT.value,
            channel=NotificationChannel.SMS.value,
        )
        event = n._events[0]
        assert event.notification_type == NotificationType.PAYMENT_RECEIPT.value
        assert event.channel == NotificationChannel.SMS.value

    def test_event_contains_subject(self):
        n = _make_notification(subject="Welcome!")
        event = n._events[0]
        assert event.subject == "Welcome!"

    def test_event_contains_template_name(self):
        n = _make_notification(template_name="WelcomeTemplate")
        event = n._events[0]
        assert event.template_name == "WelcomeTemplate"

    def test_event_contains_source_event_type(self):
        n = _make_notification(source_event_type="Identity.CustomerRegistered.v1")
        event = n._events[0]
        assert event.source_event_type == "Identity.CustomerRegistered.v1"

    def test_event_contains_scheduled_for(self):
        future = datetime.now(UTC) + timedelta(hours=24)
        n = _make_notification(scheduled_for=future)
        event = n._events[0]
        assert event.scheduled_for == future

    def test_event_contains_created_at(self):
        n = _make_notification()
        event = n._events[0]
        assert event.created_at is not None
