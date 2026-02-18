"""Tests for order return lifecycle."""

import pytest
from ordering.order.events import OrderReturned, ReturnApproved, ReturnRequested
from ordering.order.order import ItemStatus, Order, OrderStatus
from protean.exceptions import ValidationError


def _make_delivered_order():
    order = Order.create(
        customer_id="cust-001",
        items_data=[
            {"product_id": "p1", "variant_id": "v1", "sku": "S1", "title": "P1", "quantity": 1, "unit_price": 30.0},
            {"product_id": "p2", "variant_id": "v2", "sku": "S2", "title": "P2", "quantity": 1, "unit_price": 20.0},
        ],
        shipping_address={"street": "1 St", "city": "C", "postal_code": "00000", "country": "US"},
        billing_address={"street": "1 St", "city": "C", "postal_code": "00000", "country": "US"},
        pricing={"subtotal": 50.0, "grand_total": 50.0},
    )
    order.confirm()
    order.record_payment_pending("pay-001", "cc")
    order.record_payment_success("pay-001", 50.0, "cc")
    order.record_shipment("ship-001", "FedEx", "TRACK-001")
    order.record_delivery()
    order._events.clear()
    return order


class TestRequestReturn:
    def test_transitions_to_return_requested(self):
        order = _make_delivered_order()
        order.request_return("Defective product")
        assert order.status == OrderStatus.RETURN_REQUESTED.value

    def test_raises_event(self):
        order = _make_delivered_order()
        order.request_return("Wrong size")
        assert len(order._events) == 1
        event = order._events[0]
        assert isinstance(event, ReturnRequested)
        assert event.reason == "Wrong size"

    def test_cannot_return_from_created(self):
        order = Order.create(
            customer_id="c",
            items_data=[
                {"product_id": "p", "variant_id": "v", "sku": "S", "title": "T", "quantity": 1, "unit_price": 10.0}
            ],
            shipping_address={"street": "1 St", "city": "C", "postal_code": "00000", "country": "US"},
            billing_address={"street": "1 St", "city": "C", "postal_code": "00000", "country": "US"},
            pricing={"subtotal": 10.0, "grand_total": 10.0},
        )
        with pytest.raises(ValidationError):
            order.request_return("reason")


class TestApproveReturn:
    def test_transitions_to_return_approved(self):
        order = _make_delivered_order()
        order.request_return("Defective")
        order._events.clear()
        order.approve_return()
        assert order.status == OrderStatus.RETURN_APPROVED.value

    def test_raises_event(self):
        order = _make_delivered_order()
        order.request_return("Defective")
        order._events.clear()
        order.approve_return()
        assert len(order._events) == 1
        assert isinstance(order._events[0], ReturnApproved)


class TestRecordReturn:
    def test_transitions_to_returned(self):
        order = _make_delivered_order()
        order.request_return("Defective")
        order.approve_return()
        order._events.clear()
        order.record_return()
        assert order.status == OrderStatus.RETURNED.value

    def test_marks_items_as_returned(self):
        order = _make_delivered_order()
        order.request_return("Defective")
        order.approve_return()
        order._events.clear()
        order.record_return()
        for item in order.items:
            assert item.item_status == ItemStatus.RETURNED.value

    def test_partial_return(self):
        order = _make_delivered_order()
        order.request_return("Defective")
        order.approve_return()
        order._events.clear()
        item_id = str(order.items[0].id)
        order.record_return(returned_item_ids=[item_id])
        assert order.items[0].item_status == ItemStatus.RETURNED.value
        assert order.items[1].item_status == ItemStatus.DELIVERED.value

    def test_raises_event(self):
        order = _make_delivered_order()
        order.request_return("Defective")
        order.approve_return()
        order._events.clear()
        order.record_return()
        assert len(order._events) == 1
        assert isinstance(order._events[0], OrderReturned)


class TestFullReturnLifecycle:
    def test_delivered_to_return_to_refunded(self):
        order = _make_delivered_order()
        order.request_return("Defective")
        order.approve_return()
        order.record_return()
        order.refund()
        assert order.status == OrderStatus.REFUNDED.value
