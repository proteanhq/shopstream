"""Tests for Order state machine — valid transitions and invalid transition guards."""

import pytest
from protean.testing import given

from ordering.order.cancellation import CancelOrder, RefundOrder
from ordering.order.completion import CompleteOrder
from ordering.order.confirmation import ConfirmOrder
from ordering.order.creation import CreateOrder
from ordering.order.fulfillment import MarkProcessing, RecordDelivery, RecordPartialShipment, RecordShipment
from ordering.order.order import Order, OrderStatus
from ordering.order.payment import RecordPaymentFailure, RecordPaymentPending, RecordPaymentSuccess
from ordering.order.returns import ApproveReturn, RecordReturn, RequestReturn

CREATE_ORDER_ARGS = {
    "customer_id": "cust-001",
    "items": [
        {
            "product_id": "prod-001",
            "variant_id": "var-001",
            "sku": "SKU-001",
            "title": "Test Product",
            "quantity": 1,
            "unit_price": 50.0,
        }
    ],
    "shipping_address": {"street": "1 St", "city": "C", "postal_code": "00000", "country": "US"},
    "billing_address": {"street": "1 St", "city": "C", "postal_code": "00000", "country": "US"},
    "subtotal": 50.0,
    "shipping_cost": 0.0,
    "tax_total": 0.0,
    "discount_total": 0.0,
    "grand_total": 50.0,
    "currency": "USD",
}


# Each reachable status, with the status it is reached from and the command that moves it there.
_STEPS = {
    OrderStatus.CONFIRMED: (OrderStatus.CREATED, lambda order_id: ConfirmOrder(order_id=order_id)),
    OrderStatus.PAYMENT_PENDING: (
        OrderStatus.CONFIRMED,
        lambda order_id: RecordPaymentPending(order_id=order_id, payment_id="pay-001", payment_method="credit_card"),
    ),
    OrderStatus.PAID: (
        OrderStatus.PAYMENT_PENDING,
        lambda order_id: RecordPaymentSuccess(
            order_id=order_id, payment_id="pay-001", amount=50.0, payment_method="credit_card"
        ),
    ),
    OrderStatus.PROCESSING: (OrderStatus.PAID, lambda order_id: MarkProcessing(order_id=order_id)),
    OrderStatus.SHIPPED: (
        OrderStatus.PROCESSING,
        lambda order_id: RecordShipment(
            order_id=order_id, shipment_id="ship-001", carrier="FedEx", tracking_number="TRACK-001"
        ),
    ),
    OrderStatus.DELIVERED: (OrderStatus.SHIPPED, lambda order_id: RecordDelivery(order_id=order_id)),
    OrderStatus.COMPLETED: (OrderStatus.DELIVERED, lambda order_id: CompleteOrder(order_id=order_id)),
    OrderStatus.RETURN_REQUESTED: (
        OrderStatus.DELIVERED,
        lambda order_id: RequestReturn(order_id=order_id, reason="Defective"),
    ),
    OrderStatus.RETURN_APPROVED: (OrderStatus.RETURN_REQUESTED, lambda order_id: ApproveReturn(order_id=order_id)),
    OrderStatus.RETURNED: (OrderStatus.RETURN_APPROVED, lambda order_id: RecordReturn(order_id=order_id)),
    OrderStatus.CANCELLED: (
        OrderStatus.CREATED,
        lambda order_id: CancelOrder(order_id=order_id, reason="Test", cancelled_by="System"),
    ),
    OrderStatus.REFUNDED: (OrderStatus.CANCELLED, lambda order_id: RefundOrder(order_id=order_id)),
}


def _order_at_state(target_status):
    """Create an order and advance it to the desired state using given().process() chains."""
    if target_status == OrderStatus.CREATED:
        result = given(Order).process(CreateOrder(**CREATE_ORDER_ARGS))
        return result, str(result.aggregate.id)
    if target_status not in _STEPS:
        raise ValueError(f"Cannot create order at state {target_status}")

    previous_status, make_command = _STEPS[target_status]
    result, order_id = _order_at_state(previous_status)
    return result.process(make_command(order_id)), order_id


# ---------------------------------------------------------------
# Happy path transitions
# ---------------------------------------------------------------
class TestValidTransitions:
    def test_created_to_confirmed(self):
        result, order_id = _order_at_state(OrderStatus.CREATED)
        result = result.process(ConfirmOrder(order_id=order_id))
        assert result.status == OrderStatus.CONFIRMED.value

    def test_confirmed_to_payment_pending(self):
        result, order_id = _order_at_state(OrderStatus.CONFIRMED)
        result = result.process(
            RecordPaymentPending(order_id=order_id, payment_id="pay-001", payment_method="credit_card")
        )
        assert result.status == OrderStatus.PAYMENT_PENDING.value

    def test_payment_pending_to_paid(self):
        result, order_id = _order_at_state(OrderStatus.PAYMENT_PENDING)
        result = result.process(
            RecordPaymentSuccess(order_id=order_id, payment_id="pay-001", amount=50.0, payment_method="credit_card")
        )
        assert result.status == OrderStatus.PAID.value

    def test_payment_failure_returns_to_confirmed(self):
        result, order_id = _order_at_state(OrderStatus.PAYMENT_PENDING)
        result = result.process(RecordPaymentFailure(order_id=order_id, payment_id="pay-001", reason="Card declined"))
        assert result.status == OrderStatus.CONFIRMED.value

    def test_paid_to_processing(self):
        result, order_id = _order_at_state(OrderStatus.PAID)
        result = result.process(MarkProcessing(order_id=order_id))
        assert result.status == OrderStatus.PROCESSING.value

    def test_processing_to_shipped(self):
        result, order_id = _order_at_state(OrderStatus.PROCESSING)
        result = result.process(
            RecordShipment(order_id=order_id, shipment_id="ship-001", carrier="FedEx", tracking_number="TRACK-001")
        )
        assert result.status == OrderStatus.SHIPPED.value

    def test_processing_to_partially_shipped(self):
        result, order_id = _order_at_state(OrderStatus.PROCESSING)
        item_id = str(result.aggregate.items[0].id)
        result = result.process(
            RecordPartialShipment(
                order_id=order_id,
                shipment_id="ship-001",
                carrier="FedEx",
                tracking_number="TRACK-001",
                shipped_item_ids=[item_id],
            )
        )
        assert result.status == OrderStatus.PARTIALLY_SHIPPED.value

    def test_partially_shipped_to_shipped(self):
        result, order_id = _order_at_state(OrderStatus.PROCESSING)
        item_id = str(result.aggregate.items[0].id)
        result = result.process(
            RecordPartialShipment(
                order_id=order_id,
                shipment_id="ship-001",
                carrier="FedEx",
                tracking_number="TRACK-P",
                shipped_item_ids=[item_id],
            )
        )
        result = result.process(
            RecordShipment(order_id=order_id, shipment_id="ship-002", carrier="FedEx", tracking_number="TRACK-F")
        )
        assert result.status == OrderStatus.SHIPPED.value

    def test_shipped_to_delivered(self):
        result, order_id = _order_at_state(OrderStatus.SHIPPED)
        result = result.process(RecordDelivery(order_id=order_id))
        assert result.status == OrderStatus.DELIVERED.value

    def test_delivered_to_completed(self):
        result, order_id = _order_at_state(OrderStatus.DELIVERED)
        result = result.process(CompleteOrder(order_id=order_id))
        assert result.status == OrderStatus.COMPLETED.value

    def test_delivered_to_return_requested(self):
        result, order_id = _order_at_state(OrderStatus.DELIVERED)
        result = result.process(RequestReturn(order_id=order_id, reason="Defective product"))
        assert result.status == OrderStatus.RETURN_REQUESTED.value

    def test_return_requested_to_return_approved(self):
        result, order_id = _order_at_state(OrderStatus.RETURN_REQUESTED)
        result = result.process(ApproveReturn(order_id=order_id))
        assert result.status == OrderStatus.RETURN_APPROVED.value

    def test_return_approved_to_returned(self):
        result, order_id = _order_at_state(OrderStatus.RETURN_APPROVED)
        result = result.process(RecordReturn(order_id=order_id))
        assert result.status == OrderStatus.RETURNED.value

    def test_returned_to_refunded(self):
        result, order_id = _order_at_state(OrderStatus.RETURNED)
        result = result.process(RefundOrder(order_id=order_id))
        assert result.status == OrderStatus.REFUNDED.value

    def test_cancelled_to_refunded(self):
        result, order_id = _order_at_state(OrderStatus.CANCELLED)
        result = result.process(RefundOrder(order_id=order_id))
        assert result.status == OrderStatus.REFUNDED.value


# ---------------------------------------------------------------
# Cancellation from allowed states
# ---------------------------------------------------------------
class TestCancellation:
    @pytest.mark.parametrize(
        "state",
        [
            OrderStatus.CREATED,
            OrderStatus.CONFIRMED,
            OrderStatus.PAYMENT_PENDING,
            OrderStatus.PAID,
        ],
    )
    def test_cancel_from_allowed_state(self, state):
        result, order_id = _order_at_state(state)
        result = result.process(CancelOrder(order_id=order_id, reason="Customer request", cancelled_by="Customer"))
        assert result.status == OrderStatus.CANCELLED.value

    @pytest.mark.parametrize(
        "state",
        [
            OrderStatus.PROCESSING,
            OrderStatus.SHIPPED,
            OrderStatus.DELIVERED,
            OrderStatus.COMPLETED,
            OrderStatus.RETURNED,
            OrderStatus.REFUNDED,
        ],
    )
    def test_cannot_cancel_from_disallowed_state(self, state):
        result, order_id = _order_at_state(state)
        result = result.process(CancelOrder(order_id=order_id, reason="Too late", cancelled_by="Customer"))
        assert result.rejected


# ---------------------------------------------------------------
# Invalid transitions
# ---------------------------------------------------------------
class TestInvalidTransitions:
    def test_confirm_confirmed_order_is_idempotent(self):
        result, order_id = _order_at_state(OrderStatus.CONFIRMED)
        result = result.process(ConfirmOrder(order_id=order_id))
        assert result.status == OrderStatus.CONFIRMED.value

    def test_cannot_ship_created_order(self):
        result, order_id = _order_at_state(OrderStatus.CREATED)
        result = result.process(RecordShipment(order_id=order_id, shipment_id="s", carrier="c", tracking_number="t"))
        assert result.rejected

    def test_cannot_deliver_created_order(self):
        result, order_id = _order_at_state(OrderStatus.CREATED)
        result = result.process(RecordDelivery(order_id=order_id))
        assert result.rejected

    def test_cannot_complete_created_order(self):
        result, order_id = _order_at_state(OrderStatus.CREATED)
        result = result.process(CompleteOrder(order_id=order_id))
        assert result.rejected

    def test_cannot_request_return_from_created(self):
        result, order_id = _order_at_state(OrderStatus.CREATED)
        result = result.process(RequestReturn(order_id=order_id, reason="reason"))
        assert result.rejected

    def test_cannot_refund_paid_order(self):
        result, order_id = _order_at_state(OrderStatus.PAID)
        result = result.process(RefundOrder(order_id=order_id))
        assert result.rejected

    def test_cannot_mark_processing_created_order(self):
        result, order_id = _order_at_state(OrderStatus.CREATED)
        result = result.process(MarkProcessing(order_id=order_id))
        assert result.rejected

    def test_cannot_payment_pending_from_paid(self):
        result, order_id = _order_at_state(OrderStatus.PAID)
        result = result.process(RecordPaymentPending(order_id=order_id, payment_id="pay-002", payment_method="debit"))
        assert result.rejected

    def test_completed_is_terminal(self):
        result, order_id = _order_at_state(OrderStatus.COMPLETED)
        result = result.process(RequestReturn(order_id=order_id, reason="Too late"))
        assert result.rejected

    def test_refunded_is_idempotent(self):
        result, order_id = _order_at_state(OrderStatus.REFUNDED)
        result = result.process(RefundOrder(order_id=order_id))
        assert result.status == OrderStatus.REFUNDED.value


# ---------------------------------------------------------------
# Idempotent transitions (race condition resilience)
# ---------------------------------------------------------------
class TestIdempotentTransitions:
    def test_cancel_already_cancelled_is_idempotent(self):
        result, order_id = _order_at_state(OrderStatus.CANCELLED)
        result = result.process(CancelOrder(order_id=order_id, reason="Duplicate", cancelled_by="System"))
        assert result.status == OrderStatus.CANCELLED.value

    def test_payment_pending_already_pending_is_idempotent(self):
        result, order_id = _order_at_state(OrderStatus.PAYMENT_PENDING)
        result = result.process(RecordPaymentPending(order_id=order_id, payment_id="pay-002", payment_method="debit"))
        assert result.status == OrderStatus.PAYMENT_PENDING.value

    def test_payment_success_already_paid_is_idempotent(self):
        result, order_id = _order_at_state(OrderStatus.PAID)
        result = result.process(
            RecordPaymentSuccess(order_id=order_id, payment_id="pay-001", amount=50.0, payment_method="credit_card")
        )
        assert result.status == OrderStatus.PAID.value

    def test_refund_already_refunded_is_idempotent(self):
        result, order_id = _order_at_state(OrderStatus.REFUNDED)
        result = result.process(RefundOrder(order_id=order_id))
        assert result.status == OrderStatus.REFUNDED.value


class TestRaceConditionRejections:
    """Payment events arriving after cancellation should be rejected."""

    def test_payment_pending_on_cancelled_raises(self):
        result, order_id = _order_at_state(OrderStatus.CANCELLED)
        result = result.process(
            RecordPaymentPending(order_id=order_id, payment_id="pay-001", payment_method="credit_card")
        )
        assert result.rejected

    def test_payment_success_on_cancelled_raises(self):
        result, order_id = _order_at_state(OrderStatus.CANCELLED)
        result = result.process(
            RecordPaymentSuccess(order_id=order_id, payment_id="pay-001", amount=50.0, payment_method="credit_card")
        )
        assert result.rejected

    def test_payment_failure_on_cancelled_raises(self):
        result, order_id = _order_at_state(OrderStatus.CANCELLED)
        result = result.process(RecordPaymentFailure(order_id=order_id, payment_id="pay-001", reason="declined"))
        assert result.rejected
