"""Application tests for PaymentEventsSubscriber — Ordering reacts to Payment events.

Tests the subscriber ACL pattern: raw dict payloads are filtered by event type
and translated into domain commands (RecordPaymentSuccess, RecordPaymentFailure).
"""

from protean import current_domain

from ordering.checkout.payment_subscriber import PaymentEventsSubscriber
from ordering.order.cancellation import CancelOrder
from ordering.order.confirmation import ConfirmOrder
from ordering.order.creation import CreateOrder
from ordering.order.order import Order, OrderStatus
from ordering.order.payment import RecordPaymentPending, RecordPaymentSuccess


def _build_message(event_type: str, data: dict) -> dict:
    """Build a broker message payload with metadata and data."""
    return {
        "data": data,
        "metadata": {"headers": {"type": event_type}},
    }


def _create_confirmed_order():
    """Create an order in CONFIRMED state."""
    order_id = current_domain.process(
        CreateOrder(
            customer_id="cust-001",
            items=[
                {
                    "product_id": "prod-001",
                    "variant_id": "var-001",
                    "sku": "SKU-001",
                    "title": "Widget",
                    "quantity": 1,
                    "unit_price": 25.0,
                },
            ],
            shipping_address={
                "street": "123 Main",
                "city": "Town",
                "state": "CA",
                "postal_code": "90210",
                "country": "US",
            },
            billing_address={
                "street": "123 Main",
                "city": "Town",
                "state": "CA",
                "postal_code": "90210",
                "country": "US",
            },
            subtotal=25.0,
            grand_total=27.5,
        ),
        asynchronous=False,
    )
    current_domain.process(ConfirmOrder(order_id=order_id), asynchronous=False)
    return order_id


def _create_payment_pending_order():
    """Create an order in PAYMENT_PENDING state."""
    order_id = _create_confirmed_order()
    current_domain.process(
        RecordPaymentPending(
            order_id=order_id,
            payment_id="pay-001",
            payment_method="credit_card",
        ),
        asynchronous=False,
    )
    return order_id


class TestPaymentSucceededSubscriber:
    def test_payment_succeeded_records_success(self):
        """PaymentSucceeded event should transition order to PAID."""
        order_id = _create_payment_pending_order()

        subscriber = PaymentEventsSubscriber()
        subscriber(
            _build_message(
                "Payments.PaymentSucceeded.v1",
                {
                    "order_id": order_id,
                    "payment_id": "pay-001",
                    "amount": 27.5,
                },
            )
        )

        order = current_domain.repository_for(Order).get(order_id)
        assert order.status == OrderStatus.PAID.value
        assert order.payment_id == "pay-001"

    def test_payment_succeeded_skips_when_no_order_id(self):
        """PaymentSucceeded with no order_id in data should be silently ignored."""
        subscriber = PaymentEventsSubscriber()
        # Should not raise
        subscriber(
            _build_message(
                "Payments.PaymentSucceeded.v1",
                {
                    "payment_id": "pay-orphan",
                    "amount": 50.0,
                },
            )
        )

    def test_payment_succeeded_handles_already_transitioned(self):
        """PaymentSucceeded on an already-PAID order should not raise (ValidationError caught)."""
        order_id = _create_payment_pending_order()

        # Walk order to PAID state
        current_domain.process(
            RecordPaymentSuccess(
                order_id=order_id,
                payment_id="pay-001",
                amount=27.5,
                payment_method="credit_card",
            ),
            asynchronous=False,
        )
        order = current_domain.repository_for(Order).get(order_id)
        assert order.status == OrderStatus.PAID.value

        subscriber = PaymentEventsSubscriber()
        # Should not raise — ValidationError is caught internally
        subscriber(
            _build_message(
                "Payments.PaymentSucceeded.v1",
                {
                    "order_id": order_id,
                    "payment_id": "pay-duplicate",
                    "amount": 27.5,
                },
            )
        )

        # Order should still be PAID
        order = current_domain.repository_for(Order).get(order_id)
        assert order.status == OrderStatus.PAID.value


class TestPaymentFailedSubscriber:
    def test_payment_failed_records_failure(self):
        """PaymentFailed event should return order to CONFIRMED."""
        order_id = _create_payment_pending_order()

        subscriber = PaymentEventsSubscriber()
        subscriber(
            _build_message(
                "Payments.PaymentFailed.v1",
                {
                    "order_id": order_id,
                    "payment_id": "pay-001",
                    "reason": "Insufficient funds",
                },
            )
        )

        order = current_domain.repository_for(Order).get(order_id)
        assert order.status == OrderStatus.CONFIRMED.value
        assert order.payment_status == "failed"

    def test_payment_failed_skips_when_no_order_id(self):
        """PaymentFailed with no order_id in data should be silently ignored."""
        subscriber = PaymentEventsSubscriber()
        # Should not raise
        subscriber(
            _build_message(
                "Payments.PaymentFailed.v1",
                {
                    "payment_id": "pay-orphan",
                    "reason": "Card expired",
                },
            )
        )

    def test_payment_failed_handles_already_transitioned(self):
        """PaymentFailed on an already-CANCELLED order should not raise (ValidationError caught)."""
        order_id = _create_confirmed_order()

        # Cancel the order directly
        current_domain.process(
            CancelOrder(order_id=order_id, reason="Customer request", cancelled_by="Customer"),
            asynchronous=False,
        )
        order = current_domain.repository_for(Order).get(order_id)
        assert order.status == OrderStatus.CANCELLED.value

        subscriber = PaymentEventsSubscriber()
        # Should not raise — ValidationError is caught internally
        subscriber(
            _build_message(
                "Payments.PaymentFailed.v1",
                {
                    "order_id": order_id,
                    "payment_id": "pay-001",
                    "reason": "Card declined",
                },
            )
        )

        # Order should still be CANCELLED
        order = current_domain.repository_for(Order).get(order_id)
        assert order.status == OrderStatus.CANCELLED.value


class TestPaymentSucceededValidationErrorCaught:
    def test_catches_validation_error_on_record_success(self):
        """When domain.process raises ValidationError, it's caught and logged."""
        from unittest.mock import MagicMock, patch

        from protean.exceptions import ValidationError

        subscriber = PaymentEventsSubscriber()
        mock_domain = MagicMock()
        mock_domain.process = MagicMock(side_effect=ValidationError({"order": "Already paid"}))
        with patch("ordering.checkout.payment_subscriber.current_domain", mock_domain):
            subscriber(
                _build_message(
                    "Payments.PaymentSucceeded.v1",
                    {"order_id": "ord-err-001", "payment_id": "pay-001", "amount": 50.0},
                )
            )
            mock_domain.process.assert_called_once()


class TestPaymentFailedValidationErrorCaught:
    def test_catches_validation_error_on_record_failure(self):
        """When domain.process raises ValidationError on PaymentFailed, it's caught."""
        from unittest.mock import MagicMock, patch

        from protean.exceptions import ValidationError

        subscriber = PaymentEventsSubscriber()
        mock_domain = MagicMock()
        mock_domain.process = MagicMock(side_effect=ValidationError({"order": "Already cancelled"}))
        with patch("ordering.checkout.payment_subscriber.current_domain", mock_domain):
            subscriber(
                _build_message(
                    "Payments.PaymentFailed.v1",
                    {"order_id": "ord-err-002", "payment_id": "pay-002", "reason": "Declined"},
                )
            )
            mock_domain.process.assert_called_once()


class TestPaymentSubscriberIgnoresUnrelated:
    def test_ignores_unrelated_events(self):
        """Events that are neither PaymentSucceeded nor PaymentFailed should be ignored."""
        subscriber = PaymentEventsSubscriber()
        # Should not raise or have any effect
        subscriber(
            _build_message(
                "Payments.PaymentInitiated.v1",
                {
                    "order_id": "order-999",
                    "payment_id": "pay-999",
                    "amount": 100.0,
                },
            )
        )
