"""Domain tests for OrderCheckoutSaga — unit tests for handler logic.

These tests verify the saga's internal state transitions in isolation.
The saga now reacts only to internal ordering events (OrderConfirmed,
PaymentPending, PaymentSucceeded, PaymentFailed, OrderCancelled).
External events from Inventory and Payments are translated by subscribers
into ordering commands, which raise these internal events.
"""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

from ordering.checkout.saga import OrderCheckoutSaga
from ordering.order.events import (
    OrderCancelled,
    OrderConfirmed,
    PaymentFailed,
    PaymentPending,
    PaymentSucceeded,
)


class TestOnOrderConfirmed:
    def test_sets_status_awaiting_reservation(self):
        saga = OrderCheckoutSaga()
        event = OrderConfirmed(
            order_id="ord-001",
            confirmed_at=datetime.now(UTC),
        )
        saga.on_order_confirmed(event)
        assert saga.status == "awaiting_reservation"
        assert saga.order_id == "ord-001"

    def test_sets_started_at(self):
        saga = OrderCheckoutSaga()
        now = datetime.now(UTC)
        event = OrderConfirmed(order_id="ord-001", confirmed_at=now)
        saga.on_order_confirmed(event)
        assert saga.started_at == now


class TestOnPaymentPending:
    def test_sets_status_awaiting_payment(self):
        saga = OrderCheckoutSaga()
        saga.order_id = "ord-001"
        saga.status = "awaiting_reservation"
        event = PaymentPending(
            order_id="ord-001",
            payment_id="pay-001",
            payment_method="credit_card",
            initiated_at=datetime.now(UTC),
        )
        saga.on_payment_pending(event)
        assert saga.status == "awaiting_payment"
        assert saga.payment_id == "pay-001"


class TestOnPaymentSucceeded:
    def test_sets_status_completed(self):
        saga = OrderCheckoutSaga()
        saga.order_id = "ord-001"
        saga.status = "awaiting_payment"
        event = PaymentSucceeded(
            order_id="ord-001",
            payment_id="pay-001",
            amount=59.99,
            payment_method="credit_card",
            paid_at=datetime.now(UTC),
        )
        saga.on_payment_succeeded(event)
        assert saga.status == "completed"
        assert saga.payment_id == "pay-001"
        assert saga.amount == 59.99

    def test_skips_when_already_completed(self):
        saga = OrderCheckoutSaga()
        saga.order_id = "ord-001"
        saga.status = "completed"
        event = PaymentSucceeded(
            order_id="ord-001",
            payment_id="pay-001",
            amount=59.99,
            payment_method="credit_card",
            paid_at=datetime.now(UTC),
        )
        saga.on_payment_succeeded(event)
        assert saga.status == "completed"


class TestOnPaymentFailed:
    def test_retrying_when_under_max_retries(self):
        saga = OrderCheckoutSaga()
        saga.order_id = "ord-001"
        saga.status = "awaiting_payment"
        saga.retry_count = 0
        event = PaymentFailed(
            order_id="ord-001",
            payment_id="pay-001",
            reason="Declined",
            failed_at=datetime.now(UTC),
        )
        saga.on_payment_failed(event)
        assert saga.status == "retrying"
        assert saga.retry_count == 1

    @patch("ordering.checkout.saga.current_domain")
    def test_failed_when_max_retries_exceeded(self, mock_domain):
        mock_domain.process = MagicMock()
        saga = OrderCheckoutSaga()
        saga.order_id = "ord-001"
        saga.status = "awaiting_payment"
        saga.retry_count = 2  # Next failure = 3rd retry = max
        event = PaymentFailed(
            order_id="ord-001",
            payment_id="pay-001",
            reason="Card expired",
            failed_at=datetime.now(UTC),
        )
        saga.on_payment_failed(event)
        assert saga.status == "failed"
        assert saga.retry_count == 3
        mock_domain.process.assert_called_once()

    def test_catches_validation_error_on_cancel(self):
        from unittest.mock import MagicMock, patch

        from protean.exceptions import ValidationError

        mock_domain = MagicMock()
        mock_domain.process = MagicMock(side_effect=ValidationError({"order": "Already cancelled"}))
        saga = OrderCheckoutSaga()
        saga.order_id = "ord-001"
        saga.status = "awaiting_payment"
        saga.retry_count = 2
        event = PaymentFailed(
            order_id="ord-001",
            payment_id="pay-001",
            reason="Card expired",
            failed_at=datetime.now(UTC),
        )
        with patch("ordering.checkout.saga.current_domain", mock_domain):
            saga.on_payment_failed(event)
        assert saga.status == "failed"

    def test_skips_when_already_failed(self):
        saga = OrderCheckoutSaga()
        saga.order_id = "ord-001"
        saga.status = "failed"
        event = PaymentFailed(
            order_id="ord-001",
            payment_id="pay-001",
            reason="Declined",
            failed_at=datetime.now(UTC),
        )
        saga.on_payment_failed(event)
        assert saga.status == "failed"


class TestOnOrderCancelled:
    def test_sets_status_failed(self):
        saga = OrderCheckoutSaga()
        saga.order_id = "ord-001"
        saga.status = "awaiting_payment"
        event = OrderCancelled(
            order_id="ord-001",
            reason="timeout",
            cancelled_by="System",
            cancelled_at=datetime.now(UTC),
        )
        saga.on_order_cancelled(event)
        assert saga.status == "failed"
        assert "timeout" in saga.failure_reason

    def test_skips_when_already_completed(self):
        saga = OrderCheckoutSaga()
        saga.order_id = "ord-001"
        saga.status = "completed"
        event = OrderCancelled(
            order_id="ord-001",
            reason="late cancel",
            cancelled_by="Customer",
            cancelled_at=datetime.now(UTC),
        )
        saga.on_order_cancelled(event)
        assert saga.status == "completed"
