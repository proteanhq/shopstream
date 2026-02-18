"""Tests for Order state machine — valid transitions and invalid transition guards."""

import pytest
from ordering.order.order import Order, OrderStatus
from protean.exceptions import ValidationError


def _make_order():
    return Order.create(
        customer_id="cust-001",
        items_data=[
            {
                "product_id": "prod-001",
                "variant_id": "var-001",
                "sku": "SKU-001",
                "title": "Test Product",
                "quantity": 1,
                "unit_price": 50.0,
            }
        ],
        shipping_address={"street": "1 St", "city": "C", "postal_code": "00000", "country": "US"},
        billing_address={"street": "1 St", "city": "C", "postal_code": "00000", "country": "US"},
        pricing={"subtotal": 50.0, "grand_total": 50.0},
    )


def _order_at_state(target_status):
    """Create an order and advance it to the desired state."""
    order = _make_order()
    order._events.clear()

    if target_status == OrderStatus.CREATED:
        return order

    order.confirm()
    order._events.clear()
    if target_status == OrderStatus.CONFIRMED:
        return order

    order.record_payment_pending("pay-001", "credit_card")
    order._events.clear()
    if target_status == OrderStatus.PAYMENT_PENDING:
        return order

    order.record_payment_success("pay-001", 50.0, "credit_card")
    order._events.clear()
    if target_status == OrderStatus.PAID:
        return order

    order.mark_processing()
    order._events.clear()
    if target_status == OrderStatus.PROCESSING:
        return order

    order.record_shipment("ship-001", "FedEx", "TRACK-001")
    order._events.clear()
    if target_status == OrderStatus.SHIPPED:
        return order

    order.record_delivery()
    order._events.clear()
    if target_status == OrderStatus.DELIVERED:
        return order

    if target_status == OrderStatus.COMPLETED:
        order.complete()
        order._events.clear()
        return order

    if target_status == OrderStatus.RETURN_REQUESTED:
        order.request_return("Defective")
        order._events.clear()
        return order

    if target_status == OrderStatus.RETURN_APPROVED:
        order.request_return("Defective")
        order._events.clear()
        order.approve_return()
        order._events.clear()
        return order

    if target_status == OrderStatus.RETURNED:
        order.request_return("Defective")
        order.approve_return()
        order.record_return()
        order._events.clear()
        return order

    if target_status == OrderStatus.CANCELLED:
        # Rewind: create a fresh order and cancel from CREATED
        order2 = _make_order()
        order2._events.clear()
        order2.cancel("Test", "System")
        order2._events.clear()
        return order2

    if target_status == OrderStatus.REFUNDED:
        order2 = _make_order()
        order2._events.clear()
        order2.cancel("Test", "System")
        order2._events.clear()
        order2.refund()
        order2._events.clear()
        return order2

    raise ValueError(f"Cannot create order at state {target_status}")


# ---------------------------------------------------------------
# Happy path transitions
# ---------------------------------------------------------------
class TestValidTransitions:
    def test_created_to_confirmed(self):
        order = _order_at_state(OrderStatus.CREATED)
        order.confirm()
        assert order.status == OrderStatus.CONFIRMED.value

    def test_confirmed_to_payment_pending(self):
        order = _order_at_state(OrderStatus.CONFIRMED)
        order.record_payment_pending("pay-001", "credit_card")
        assert order.status == OrderStatus.PAYMENT_PENDING.value

    def test_payment_pending_to_paid(self):
        order = _order_at_state(OrderStatus.PAYMENT_PENDING)
        order.record_payment_success("pay-001", 50.0, "credit_card")
        assert order.status == OrderStatus.PAID.value

    def test_payment_failure_returns_to_confirmed(self):
        order = _order_at_state(OrderStatus.PAYMENT_PENDING)
        order.record_payment_failure("pay-001", "Card declined")
        assert order.status == OrderStatus.CONFIRMED.value

    def test_paid_to_processing(self):
        order = _order_at_state(OrderStatus.PAID)
        order.mark_processing()
        assert order.status == OrderStatus.PROCESSING.value

    def test_processing_to_shipped(self):
        order = _order_at_state(OrderStatus.PROCESSING)
        order.record_shipment("ship-001", "FedEx", "TRACK-001")
        assert order.status == OrderStatus.SHIPPED.value

    def test_processing_to_partially_shipped(self):
        order = _order_at_state(OrderStatus.PROCESSING)
        item_id = str(order.items[0].id)
        order.record_partial_shipment("ship-001", "FedEx", "TRACK-001", [item_id])
        assert order.status == OrderStatus.PARTIALLY_SHIPPED.value

    def test_partially_shipped_to_shipped(self):
        order = _order_at_state(OrderStatus.PROCESSING)
        item_id = str(order.items[0].id)
        order.record_partial_shipment("ship-001", "FedEx", "TRACK-P", [item_id])
        order._events.clear()
        order.record_shipment("ship-002", "FedEx", "TRACK-F")
        assert order.status == OrderStatus.SHIPPED.value

    def test_shipped_to_delivered(self):
        order = _order_at_state(OrderStatus.SHIPPED)
        order.record_delivery()
        assert order.status == OrderStatus.DELIVERED.value

    def test_delivered_to_completed(self):
        order = _order_at_state(OrderStatus.DELIVERED)
        order.complete()
        assert order.status == OrderStatus.COMPLETED.value

    def test_delivered_to_return_requested(self):
        order = _order_at_state(OrderStatus.DELIVERED)
        order.request_return("Defective product")
        assert order.status == OrderStatus.RETURN_REQUESTED.value

    def test_return_requested_to_return_approved(self):
        order = _order_at_state(OrderStatus.RETURN_REQUESTED)
        order.approve_return()
        assert order.status == OrderStatus.RETURN_APPROVED.value

    def test_return_approved_to_returned(self):
        order = _order_at_state(OrderStatus.RETURN_APPROVED)
        order.record_return()
        assert order.status == OrderStatus.RETURNED.value

    def test_returned_to_refunded(self):
        order = _order_at_state(OrderStatus.RETURNED)
        order.refund()
        assert order.status == OrderStatus.REFUNDED.value

    def test_cancelled_to_refunded(self):
        order = _order_at_state(OrderStatus.CANCELLED)
        order.refund()
        assert order.status == OrderStatus.REFUNDED.value


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
        order = _order_at_state(state)
        order.cancel("Customer request", "Customer")
        assert order.status == OrderStatus.CANCELLED.value

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
        order = _order_at_state(state)
        with pytest.raises(ValidationError):
            order.cancel("Too late", "Customer")


# ---------------------------------------------------------------
# Invalid transitions
# ---------------------------------------------------------------
class TestInvalidTransitions:
    def test_cannot_confirm_confirmed_order(self):
        order = _order_at_state(OrderStatus.CONFIRMED)
        with pytest.raises(ValidationError):
            order.confirm()

    def test_cannot_ship_created_order(self):
        order = _order_at_state(OrderStatus.CREATED)
        with pytest.raises(ValidationError):
            order.record_shipment("s", "c", "t")

    def test_cannot_deliver_created_order(self):
        order = _order_at_state(OrderStatus.CREATED)
        with pytest.raises(ValidationError):
            order.record_delivery()

    def test_cannot_complete_created_order(self):
        order = _order_at_state(OrderStatus.CREATED)
        with pytest.raises(ValidationError):
            order.complete()

    def test_cannot_request_return_from_created(self):
        order = _order_at_state(OrderStatus.CREATED)
        with pytest.raises(ValidationError):
            order.request_return("reason")

    def test_cannot_refund_paid_order(self):
        order = _order_at_state(OrderStatus.PAID)
        with pytest.raises(ValidationError):
            order.refund()

    def test_cannot_mark_processing_created_order(self):
        order = _order_at_state(OrderStatus.CREATED)
        with pytest.raises(ValidationError):
            order.mark_processing()

    def test_cannot_payment_pending_from_paid(self):
        order = _order_at_state(OrderStatus.PAID)
        with pytest.raises(ValidationError):
            order.record_payment_pending("pay-002", "debit")

    def test_completed_is_terminal(self):
        order = _order_at_state(OrderStatus.COMPLETED)
        with pytest.raises(ValidationError):
            order.request_return("Too late")

    def test_refunded_is_terminal(self):
        order = _order_at_state(OrderStatus.REFUNDED)
        with pytest.raises(ValidationError):
            order.refund()
