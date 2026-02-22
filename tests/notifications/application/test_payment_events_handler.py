"""Application tests for Payment cross-domain event handlers."""

from datetime import UTC, datetime

from notifications.notification.notification import (
    Notification,
    NotificationType,
)
from notifications.notification.payment_events import PaymentEventsHandler
from protean import current_domain
from shared.events.payments import PaymentSucceeded, RefundCompleted


class TestPaymentReceiptHandler:
    def test_creates_payment_receipt_notification(self):
        event = PaymentSucceeded(
            payment_id="pay-001",
            order_id="ord-001",
            customer_id="cust-pay-1",
            amount=49.99,
            currency="USD",
            gateway_transaction_id="txn-001",
            succeeded_at=datetime.now(UTC),
        )
        handler = PaymentEventsHandler()
        handler.on_payment_succeeded(event)

        repo = current_domain.repository_for(Notification)
        notifications = (
            repo._dao.query.filter(
                recipient_id="cust-pay-1",
                notification_type=NotificationType.PAYMENT_RECEIPT.value,
            )
            .all()
            .items
        )
        assert len(notifications) >= 1


class TestRefundNotificationHandler:
    def test_creates_refund_notification(self):
        event = RefundCompleted(
            payment_id="pay-002",
            refund_id="ref-001",
            order_id="ord-002",
            customer_id="cust-refund-1",
            amount=25.00,
            currency="USD",
            reason="Item returned",
            completed_at=datetime.now(UTC),
        )
        handler = PaymentEventsHandler()
        handler.on_refund_completed(event)

        repo = current_domain.repository_for(Notification)
        notifications = (
            repo._dao.query.filter(
                recipient_id="cust-refund-1",
                notification_type=NotificationType.REFUND_NOTIFICATION.value,
            )
            .all()
            .items
        )
        assert len(notifications) >= 1

    def test_skips_when_no_customer_id(self):
        event = RefundCompleted(
            payment_id="pay-003",
            refund_id="ref-002",
            order_id="ord-003",
            customer_id=None,
            amount=10.00,
            currency="USD",
            completed_at=datetime.now(UTC),
        )
        handler = PaymentEventsHandler()
        handler.on_refund_completed(event)
        # Should not raise — just logs and skips
