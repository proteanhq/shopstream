"""Application tests for Payment cross-domain subscriber."""

from datetime import UTC, datetime

import pytest
from protean import current_domain

from notifications.notification.notification import (
    Notification,
    NotificationType,
)
from notifications.notification.payment_subscriber import PaymentEventsSubscriber


def _build_message(event_type: str, data: dict) -> dict:
    """Build a broker message payload with metadata and data."""
    return {
        "data": data,
        "metadata": {"headers": {"type": event_type}},
    }


class TestPaymentReceiptHandler:
    def test_creates_payment_receipt_notification(self):
        subscriber = PaymentEventsSubscriber()
        subscriber(
            _build_message(
                "Payments.PaymentSucceeded.v1",
                {
                    "payment_id": "pay-001",
                    "order_id": "ord-001",
                    "customer_id": "cust-pay-1",
                    "amount": 49.99,
                    "currency": "USD",
                    "gateway_transaction_id": "txn-001",
                    "succeeded_at": datetime.now(UTC).isoformat(),
                },
            )
        )

        repo = current_domain.repository_for(Notification)
        notifications = (
            repo.query.filter(
                recipient_id="cust-pay-1",
                notification_type=NotificationType.PAYMENT_RECEIPT.value,
            )
            .all()
            .items
        )
        assert len(notifications) >= 1


class TestRefundNotificationHandler:
    def test_creates_refund_notification(self):
        subscriber = PaymentEventsSubscriber()
        subscriber(
            _build_message(
                "Payments.RefundCompleted.v1",
                {
                    "payment_id": "pay-002",
                    "refund_id": "ref-001",
                    "order_id": "ord-002",
                    "customer_id": "cust-refund-1",
                    "amount": 25.00,
                    "currency": "USD",
                    "gateway_refund_id": "gw-ref-001",
                    "reason": "Item returned",
                    "completed_at": datetime.now(UTC).isoformat(),
                },
            )
        )

        repo = current_domain.repository_for(Notification)
        notifications = (
            repo.query.filter(
                recipient_id="cust-refund-1",
                notification_type=NotificationType.REFUND_NOTIFICATION.value,
            )
            .all()
            .items
        )
        assert len(notifications) >= 1

    def test_skips_when_no_customer_id(self):
        subscriber = PaymentEventsSubscriber()
        subscriber(
            _build_message(
                "Payments.RefundCompleted.v1",
                {
                    "payment_id": "pay-003",
                    "refund_id": "ref-002",
                    "order_id": "ord-003",
                    "amount": 10.00,
                    "currency": "USD",
                    "gateway_refund_id": "gw-ref-002",
                    "completed_at": datetime.now(UTC).isoformat(),
                },
            )
        )
        # Should not raise — just logs and skips


class TestIgnoresUnrelatedEvents:
    def test_ignores_non_matching_events(self):
        """Non-payment events on the stream should be ignored."""
        subscriber = PaymentEventsSubscriber()
        subscriber(_build_message("Payments.PaymentInitiated.v1", {"payment_id": "pay-ignore"}))


def _notification_for(customer_id, notification_type):
    notifications = (
        current_domain.repository_for(Notification)
        .query.filter(recipient_id=customer_id, notification_type=notification_type)
        .all()
        .items
    )
    assert len(notifications) >= 1
    return notifications[0]


class TestAmountAsDecimalString:
    def test_receipt_renders_a_4_place_string_with_2_places(self):
        PaymentEventsSubscriber()(
            _build_message(
                "Payments.PaymentSucceeded.v2",
                {"payment_id": "pay-s1", "order_id": "ord-s1", "customer_id": "cust-pay-s1", "amount": "49.9900"},
            )
        )

        notification = _notification_for("cust-pay-s1", NotificationType.PAYMENT_RECEIPT.value)
        assert "USD 49.99 " in notification.body
        assert notification.source_event_type == "Payments.PaymentSucceeded.v2"

    def test_receipt_renders_a_whole_float_amount_with_2_places(self):
        PaymentEventsSubscriber()(
            _build_message(
                "Payments.PaymentSucceeded.v1",
                {"payment_id": "pay-s2", "order_id": "ord-s2", "customer_id": "cust-pay-s2", "amount": 50.0},
            )
        )

        notification = _notification_for("cust-pay-s2", NotificationType.PAYMENT_RECEIPT.value)
        assert "USD 50.00 " in notification.body
        assert notification.source_event_type == "Payments.PaymentSucceeded.v1"

    def test_refund_renders_a_4_place_string_with_2_places(self):
        PaymentEventsSubscriber()(
            _build_message(
                "Payments.RefundCompleted.v2",
                {
                    "payment_id": "pay-s3",
                    "refund_id": "ref-s3",
                    "order_id": "ord-s3",
                    "customer_id": "cust-pay-s3",
                    "amount": "25.0000",
                },
            )
        )

        notification = _notification_for("cust-pay-s3", NotificationType.REFUND_NOTIFICATION.value)
        assert notification.subject == "Refund Processed - USD 25.00"
        assert notification.source_event_type == "Payments.RefundCompleted.v2"

    def test_refund_rounds_the_decimal_half_even_to_2_places(self):
        # As a float, 49.995 is just below 49.995 and would show as 49.99.
        PaymentEventsSubscriber()(
            _build_message(
                "Payments.RefundCompleted.v2",
                {
                    "payment_id": "pay-s4",
                    "refund_id": "ref-s4",
                    "order_id": "ord-s4",
                    "customer_id": "cust-pay-s4",
                    "amount": "49.9950",
                },
            )
        )

        notification = _notification_for("cust-pay-s4", NotificationType.REFUND_NOTIFICATION.value)
        assert notification.subject == "Refund Processed - USD 50.00"


class TestMissingAmount:
    @pytest.mark.parametrize(
        ("event_type", "notification_type"),
        [
            ("Payments.PaymentSucceeded.v2", NotificationType.PAYMENT_RECEIPT.value),
            ("Payments.RefundCompleted.v2", NotificationType.REFUND_NOTIFICATION.value),
        ],
    )
    def test_null_amount_sends_no_notification(self, event_type, notification_type):
        PaymentEventsSubscriber()(
            _build_message(
                event_type,
                {"payment_id": "pay-null", "order_id": "ord-null", "customer_id": "cust-pay-null", "amount": None},
            )
        )

        notifications = (
            current_domain.repository_for(Notification)
            .query.filter(recipient_id="cust-pay-null", notification_type=notification_type)
            .all()
            .items
        )
        assert notifications == []
