"""Application tests for Payment cross-domain subscriber."""

from datetime import UTC, datetime

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
