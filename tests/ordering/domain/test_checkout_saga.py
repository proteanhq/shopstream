"""Domain tests for OrderCheckoutSaga — unit tests for handler logic.

These tests verify the saga's internal state transitions in isolation.
Commands dispatched to the ordering domain are mocked since we're testing
the saga's decision logic, not the downstream command handlers.
"""

from datetime import UTC, datetime
from unittest.mock import patch

from ordering.checkout.saga import OrderCheckoutSaga
from ordering.order.events import OrderConfirmed
from shared.events.inventory import ReservationReleased, StockReserved
from shared.events.payments import PaymentFailed, PaymentSucceeded


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


class TestOnStockReserved:
    @patch("ordering.checkout.saga.current_domain")
    def test_sets_status_awaiting_payment(self, mock_domain):
        saga = OrderCheckoutSaga()
        saga.order_id = "ord-001"
        saga.status = "awaiting_reservation"
        event = StockReserved(
            inventory_item_id="inv-001",
            reservation_id="res-001",
            order_id="ord-001",
            quantity=2,
            previous_available=10,
            new_available=8,
            reserved_at=datetime.now(UTC),
            expires_at=datetime.now(UTC),
        )
        saga.on_stock_reserved(event)
        assert saga.status == "awaiting_payment"
        assert saga.reservation_id == "res-001"
        mock_domain.process.assert_called_once()


class TestOnPaymentSucceeded:
    @patch("ordering.checkout.saga.current_domain")
    def test_sets_status_completed(self, mock_domain):
        saga = OrderCheckoutSaga()
        saga.order_id = "ord-001"
        saga.status = "awaiting_payment"
        event = PaymentSucceeded(
            payment_id="pay-001",
            order_id="ord-001",
            customer_id="cust-001",
            amount=59.99,
            currency="USD",
            gateway_transaction_id="txn-001",
            succeeded_at=datetime.now(UTC),
        )
        saga.on_payment_succeeded(event)
        assert saga.status == "completed"
        assert saga.payment_id == "pay-001"
        mock_domain.process.assert_called_once()


class TestOnPaymentFailed:
    def test_retrying_when_can_retry(self):
        saga = OrderCheckoutSaga()
        saga.order_id = "ord-001"
        saga.status = "awaiting_payment"
        event = PaymentFailed(
            payment_id="pay-001",
            order_id="ord-001",
            customer_id="cust-001",
            reason="Declined",
            attempt_number=1,
            can_retry=True,
            failed_at=datetime.now(UTC),
        )
        saga.on_payment_failed(event)
        assert saga.status == "retrying"

    @patch("ordering.checkout.saga.current_domain")
    def test_failed_when_cannot_retry(self, mock_domain):
        saga = OrderCheckoutSaga()
        saga.order_id = "ord-001"
        saga.status = "awaiting_payment"
        event = PaymentFailed(
            payment_id="pay-001",
            order_id="ord-001",
            customer_id="cust-001",
            reason="Card expired",
            attempt_number=3,
            can_retry=False,
            failed_at=datetime.now(UTC),
        )
        saga.on_payment_failed(event)
        assert saga.status == "failed"
        mock_domain.process.assert_called_once()


class TestOnReservationReleased:
    @patch("ordering.checkout.saga.current_domain")
    def test_sets_status_failed(self, mock_domain):
        saga = OrderCheckoutSaga()
        saga.order_id = "ord-001"
        saga.status = "awaiting_payment"
        event = ReservationReleased(
            inventory_item_id="inv-001",
            reservation_id="res-001",
            order_id="ord-001",
            quantity=2,
            reason="timeout",
            previous_available=8,
            new_available=10,
            released_at=datetime.now(UTC),
        )
        saga.on_reservation_released(event)
        assert saga.status == "failed"
        assert "timeout" in saga.failure_reason
        mock_domain.process.assert_called_once()
