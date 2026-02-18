"""Tests for order payment lifecycle."""

import pytest
from ordering.order.events import PaymentFailed, PaymentPending, PaymentSucceeded
from ordering.order.order import Order, OrderStatus
from protean.exceptions import ValidationError


def _make_confirmed_order():
    order = Order.create(
        customer_id="cust-001",
        items_data=[
            {"product_id": "p1", "variant_id": "v1", "sku": "S1", "title": "T", "quantity": 1, "unit_price": 50.0}
        ],
        shipping_address={"street": "1 St", "city": "C", "postal_code": "00000", "country": "US"},
        billing_address={"street": "1 St", "city": "C", "postal_code": "00000", "country": "US"},
        pricing={"subtotal": 50.0, "grand_total": 50.0},
    )
    order.confirm()
    order._events.clear()
    return order


class TestRecordPaymentPending:
    def test_transitions_to_payment_pending(self):
        order = _make_confirmed_order()
        order.record_payment_pending("pay-001", "credit_card")
        assert order.status == OrderStatus.PAYMENT_PENDING.value

    def test_sets_payment_info(self):
        order = _make_confirmed_order()
        order.record_payment_pending("pay-001", "credit_card")
        assert order.payment_id == "pay-001"
        assert order.payment_method == "credit_card"
        assert order.payment_status == "pending"

    def test_raises_event(self):
        order = _make_confirmed_order()
        order.record_payment_pending("pay-001", "credit_card")
        assert len(order._events) == 1
        event = order._events[0]
        assert isinstance(event, PaymentPending)
        assert event.payment_id == "pay-001"


class TestRecordPaymentSuccess:
    def test_transitions_to_paid(self):
        order = _make_confirmed_order()
        order.record_payment_pending("pay-001", "credit_card")
        order._events.clear()
        order.record_payment_success("pay-001", 50.0, "credit_card")
        assert order.status == OrderStatus.PAID.value

    def test_sets_payment_status(self):
        order = _make_confirmed_order()
        order.record_payment_pending("pay-001", "credit_card")
        order.record_payment_success("pay-001", 50.0, "credit_card")
        assert order.payment_status == "succeeded"

    def test_raises_event(self):
        order = _make_confirmed_order()
        order.record_payment_pending("pay-001", "cc")
        order._events.clear()
        order.record_payment_success("pay-001", 50.0, "cc")
        assert len(order._events) == 1
        event = order._events[0]
        assert isinstance(event, PaymentSucceeded)
        assert event.amount == 50.0

    def test_cannot_pay_from_created(self):
        order = Order.create(
            customer_id="cust-001",
            items_data=[
                {"product_id": "p1", "variant_id": "v1", "sku": "S1", "title": "T", "quantity": 1, "unit_price": 10.0}
            ],
            shipping_address={"street": "1 St", "city": "C", "postal_code": "00000", "country": "US"},
            billing_address={"street": "1 St", "city": "C", "postal_code": "00000", "country": "US"},
            pricing={"subtotal": 10.0, "grand_total": 10.0},
        )
        with pytest.raises(ValidationError):
            order.record_payment_success("pay-001", 10.0, "cc")


class TestRecordPaymentFailure:
    def test_returns_to_confirmed(self):
        order = _make_confirmed_order()
        order.record_payment_pending("pay-001", "cc")
        order._events.clear()
        order.record_payment_failure("pay-001", "Card declined")
        assert order.status == OrderStatus.CONFIRMED.value

    def test_sets_payment_status_to_failed(self):
        order = _make_confirmed_order()
        order.record_payment_pending("pay-001", "cc")
        order.record_payment_failure("pay-001", "Insufficient funds")
        assert order.payment_status == "failed"

    def test_raises_event(self):
        order = _make_confirmed_order()
        order.record_payment_pending("pay-001", "cc")
        order._events.clear()
        order.record_payment_failure("pay-001", "Declined")
        assert len(order._events) == 1
        event = order._events[0]
        assert isinstance(event, PaymentFailed)
        assert event.reason == "Declined"

    def test_can_retry_after_failure(self):
        order = _make_confirmed_order()
        order.record_payment_pending("pay-001", "cc")
        order.record_payment_failure("pay-001", "Declined")
        # Now at CONFIRMED again — can retry
        order.record_payment_pending("pay-002", "debit")
        assert order.status == OrderStatus.PAYMENT_PENDING.value
