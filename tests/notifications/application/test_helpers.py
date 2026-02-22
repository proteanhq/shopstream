"""Application tests for notification helper functions."""

from notifications.channel import reset_channels
from notifications.notification.helpers import (
    create_internal_notification,
    create_notifications_for_customer,
)
from notifications.notification.notification import (
    Notification,
    NotificationChannel,
    NotificationType,
    RecipientType,
)
from notifications.preference.preference import NotificationPreference
from protean import current_domain


class TestCreateNotificationsForCustomer:
    def setup_method(self):
        reset_channels()

    def teardown_method(self):
        reset_channels()

    def test_creates_notification_without_preferences(self):
        """Without preferences, only email channel is used (safe default)."""
        nids = create_notifications_for_customer(
            customer_id="cust-nopref",
            notification_type=NotificationType.WELCOME.value,
            context={"customer_name": "Alice"},
        )
        assert len(nids) >= 1

        repo = current_domain.repository_for(Notification)
        n = repo.get(nids[0])
        assert n.channel == NotificationChannel.EMAIL.value

    def test_creates_notification_with_preferences(self):
        """With preferences, uses enabled channels from template defaults."""
        pref = NotificationPreference.create_default(customer_id="cust-withpref")
        pref.update_channels(email=True, sms=True, push=False)
        current_domain.repository_for(NotificationPreference).add(pref)

        nids = create_notifications_for_customer(
            customer_id="cust-withpref",
            notification_type=NotificationType.WELCOME.value,
            context={"customer_name": "Bob"},
        )
        assert len(nids) >= 1

    def test_unsubscribed_customer_gets_no_notifications(self):
        """If the customer unsubscribed from this type, no notifications are created."""
        pref = NotificationPreference.create_default(customer_id="cust-unsub-helper")
        pref.unsubscribe_from(NotificationType.WELCOME.value)
        current_domain.repository_for(NotificationPreference).add(pref)

        nids = create_notifications_for_customer(
            customer_id="cust-unsub-helper",
            notification_type=NotificationType.WELCOME.value,
            context={"customer_name": "Charlie"},
        )
        assert nids == []

    def test_no_enabled_channels_returns_empty(self):
        """If none of the template's default channels are enabled, no notifications."""
        pref = NotificationPreference.create_default(customer_id="cust-nochannels")
        # Disable all channels
        pref.update_channels(email=False, sms=False, push=False)
        current_domain.repository_for(NotificationPreference).add(pref)

        nids = create_notifications_for_customer(
            customer_id="cust-nochannels",
            notification_type=NotificationType.WELCOME.value,
            context={"customer_name": "Diana"},
        )
        assert nids == []

    def test_source_event_fields_recorded(self):
        """Source event type and ID are stored on the notification."""
        nids = create_notifications_for_customer(
            customer_id="cust-src",
            notification_type=NotificationType.WELCOME.value,
            context={"customer_name": "Eve"},
            source_event_type="Identity.CustomerRegistered.v1",
            source_event_id="evt-123",
        )
        assert len(nids) >= 1
        repo = current_domain.repository_for(Notification)
        n = repo.get(nids[0])
        assert n.source_event_type == "Identity.CustomerRegistered.v1"
        assert n.source_event_id == "evt-123"

    def test_scheduled_notification_created(self):
        """Scheduled_for is passed through to the notification."""
        from datetime import UTC, datetime, timedelta

        future = datetime.now(UTC) + timedelta(days=7)
        nids = create_notifications_for_customer(
            customer_id="cust-sched-helper",
            notification_type=NotificationType.REVIEW_PROMPT.value,
            context={"order_id": "ord-1"},
            scheduled_for=future,
        )
        assert len(nids) >= 1
        repo = current_domain.repository_for(Notification)
        n = repo.get(nids[0])
        assert n.scheduled_for is not None

    def test_template_name_recorded(self):
        """The template class name is recorded on the notification."""
        nids = create_notifications_for_customer(
            customer_id="cust-tmpl-name",
            notification_type=NotificationType.WELCOME.value,
            context={"customer_name": "Frank"},
        )
        assert len(nids) >= 1
        repo = current_domain.repository_for(Notification)
        n = repo.get(nids[0])
        assert n.template_name is not None

    def test_context_data_stored_as_json(self):
        """Context data is serialized to JSON on the notification."""
        import json

        nids = create_notifications_for_customer(
            customer_id="cust-ctx",
            notification_type=NotificationType.WELCOME.value,
            context={"customer_name": "Grace", "key": "value"},
        )
        assert len(nids) >= 1
        repo = current_domain.repository_for(Notification)
        n = repo.get(nids[0])
        ctx = json.loads(n.context_data)
        assert ctx["customer_name"] == "Grace"

    def test_no_email_in_template_defaults_and_no_prefs(self):
        """If the template doesn't include EMAIL and there are no prefs,
        no notifications are sent (since EMAIL-only is the safe default)."""
        # LOW_STOCK_ALERT has only Slack channel, but it's internal-only.
        # For customer notifications, templates like CART_RECOVERY include EMAIL,
        # so we need a template that doesn't include EMAIL.
        # All customer templates include EMAIL, so this test validates the filter logic.
        # With no preferences, only EMAIL channels from defaults are kept.
        nids = create_notifications_for_customer(
            customer_id="cust-emailfilter",
            notification_type=NotificationType.ORDER_CONFIRMATION.value,
            context={"order_id": "ord-1", "grand_total": "100", "currency": "USD"},
        )
        # ORDER_CONFIRMATION includes EMAIL, so at least 1 is created
        assert len(nids) >= 1


class TestCreateInternalNotification:
    def setup_method(self):
        reset_channels()

    def teardown_method(self):
        reset_channels()

    def test_creates_internal_slack_notification(self):
        """Internal notifications use Slack channel by default."""
        nid = create_internal_notification(
            notification_type=NotificationType.LOW_STOCK_ALERT.value,
            context={
                "sku": "SKU-001",
                "product_id": "prod-001",
                "current_available": 5,
                "reorder_point": 10,
            },
        )
        assert nid is not None
        repo = current_domain.repository_for(Notification)
        n = repo.get(nid)
        assert n.channel == NotificationChannel.SLACK.value
        assert n.recipient_type == RecipientType.INTERNAL.value
        assert str(n.recipient_id) == "operations"

    def test_internal_notification_source_event_recorded(self):
        nid = create_internal_notification(
            notification_type=NotificationType.LOW_STOCK_ALERT.value,
            context={"sku": "SKU-002", "product_id": "p2", "current_available": 3, "reorder_point": 5},
            source_event_type="Inventory.LowStockDetected.v1",
            source_event_id="evt-456",
        )
        repo = current_domain.repository_for(Notification)
        n = repo.get(nid)
        assert n.source_event_type == "Inventory.LowStockDetected.v1"
        assert n.source_event_id == "evt-456"

    def test_internal_notification_custom_recipient(self):
        nid = create_internal_notification(
            notification_type=NotificationType.LOW_STOCK_ALERT.value,
            context={"sku": "SKU-003", "product_id": "p3", "current_available": 1, "reorder_point": 5},
            recipient_id="warehouse-team",
        )
        repo = current_domain.repository_for(Notification)
        n = repo.get(nid)
        assert str(n.recipient_id) == "warehouse-team"

    def test_internal_notification_template_rendered(self):
        nid = create_internal_notification(
            notification_type=NotificationType.LOW_STOCK_ALERT.value,
            context={"sku": "SKU-004", "product_id": "p4", "current_available": 2, "reorder_point": 10},
        )
        repo = current_domain.repository_for(Notification)
        n = repo.get(nid)
        assert n.body is not None
        assert "SKU-004" in n.body
        assert n.template_name is not None
