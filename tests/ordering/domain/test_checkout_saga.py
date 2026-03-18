"""Domain tests for OrderCheckoutSaga — unit tests for handler logic.

These tests verify the saga's internal state transitions in isolation.
The saga now reacts only to internal ordering events (OrderConfirmed,
PaymentPending, PaymentSucceeded, PaymentFailed, OrderCancelled).
External events from Inventory and Payments are translated by subscribers
into ordering commands, which raise these internal events.
"""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

from protean.testing import given

from ordering.checkout.saga import OrderCheckoutSaga
from ordering.order.events import (
    OrderCancelled,
    OrderConfirmed,
    PaymentFailed,
    PaymentPending,
    PaymentSucceeded,
)


def _order_confirmed(order_id="ord-001", confirmed_at=None):
    return OrderConfirmed(
        order_id=order_id,
        confirmed_at=confirmed_at or datetime.now(UTC),
    )


def _payment_pending(order_id="ord-001", payment_id="pay-001"):
    return PaymentPending(
        order_id=order_id,
        payment_id=payment_id,
        payment_method="credit_card",
        initiated_at=datetime.now(UTC),
    )


def _payment_succeeded(order_id="ord-001", payment_id="pay-001", amount=59.99):
    return PaymentSucceeded(
        order_id=order_id,
        payment_id=payment_id,
        amount=amount,
        payment_method="credit_card",
        paid_at=datetime.now(UTC),
    )


def _payment_failed(order_id="ord-001", payment_id="pay-001", reason="Declined"):
    return PaymentFailed(
        order_id=order_id,
        payment_id=payment_id,
        reason=reason,
        failed_at=datetime.now(UTC),
    )


def _order_cancelled(order_id="ord-001", reason="timeout"):
    return OrderCancelled(
        order_id=order_id,
        reason=reason,
        cancelled_by="System",
        cancelled_at=datetime.now(UTC),
    )


class TestOnOrderConfirmed:
    def test_sets_status_awaiting_reservation(self):
        result = given(OrderCheckoutSaga, _order_confirmed())
        assert result.status == "awaiting_reservation"
        assert result.order_id == "ord-001"

    def test_sets_started_at(self):
        now = datetime.now(UTC)
        result = given(OrderCheckoutSaga, _order_confirmed(confirmed_at=now))
        assert result.started_at == now.isoformat()


class TestOnPaymentPending:
    def test_sets_status_awaiting_payment(self):
        result = given(
            OrderCheckoutSaga,
            _order_confirmed(),
            _payment_pending(),
        )
        assert result.status == "awaiting_payment"
        assert result.payment_id == "pay-001"


class TestOnPaymentSucceeded:
    def test_sets_status_completed(self):
        result = given(
            OrderCheckoutSaga,
            _order_confirmed(),
            _payment_pending(),
            _payment_succeeded(),
        )
        assert result.status == "completed"
        assert result.payment_id == "pay-001"
        assert result.amount == 59.99
        assert result.is_complete

    def test_skips_when_already_completed(self):
        result = given(
            OrderCheckoutSaga,
            _order_confirmed(),
            _payment_pending(),
            _payment_succeeded(),
            _payment_succeeded(),  # duplicate
        )
        assert result.status == "completed"
        assert result.is_complete


class TestOnPaymentFailed:
    def test_retrying_when_under_max_retries(self):
        result = given(
            OrderCheckoutSaga,
            _order_confirmed(),
            _payment_pending(),
            _payment_failed(),
        )
        assert result.status == "retrying"
        assert result.retry_count == 1

    @patch("ordering.checkout.saga.current_domain")
    def test_failed_when_max_retries_exceeded(self, mock_domain):
        mock_domain.process = MagicMock()
        result = given(
            OrderCheckoutSaga,
            _order_confirmed(),
            _payment_pending(),
            _payment_failed(reason="Attempt 1"),
            _payment_failed(reason="Attempt 2"),
            _payment_failed(reason="Card expired"),
        )
        assert result.status == "failed"
        assert result.retry_count == 3
        mock_domain.process.assert_called_once()

    def test_catches_validation_error_on_cancel(self):
        from protean.exceptions import ValidationError

        mock_domain = MagicMock()
        mock_domain.process = MagicMock(side_effect=ValidationError({"order": "Already cancelled"}))
        with patch("ordering.checkout.saga.current_domain", mock_domain):
            result = given(
                OrderCheckoutSaga,
                _order_confirmed(),
                _payment_pending(),
                _payment_failed(reason="Attempt 1"),
                _payment_failed(reason="Attempt 2"),
                _payment_failed(reason="Card expired"),
            )
        assert result.status == "failed"

    def test_skips_when_already_failed(self):
        with patch("ordering.checkout.saga.current_domain") as mock_domain:
            mock_domain.process = MagicMock()
            result = given(
                OrderCheckoutSaga,
                _order_confirmed(),
                _payment_pending(),
                _payment_failed(reason="Attempt 1"),
                _payment_failed(reason="Attempt 2"),
                _payment_failed(reason="Attempt 3"),
                _payment_failed(reason="Extra"),  # should be skipped
            )
        assert result.status == "failed"


class TestOnOrderCancelled:
    def test_sets_status_failed(self):
        result = given(
            OrderCheckoutSaga,
            _order_confirmed(),
            _payment_pending(),
            _order_cancelled(reason="timeout"),
        )
        assert result.status == "failed"
        assert "timeout" in result.failure_reason

    def test_skips_when_already_completed(self):
        result = given(
            OrderCheckoutSaga,
            _order_confirmed(),
            _payment_pending(),
            _payment_succeeded(),
            _order_cancelled(reason="late cancel"),
        )
        assert result.status == "completed"
