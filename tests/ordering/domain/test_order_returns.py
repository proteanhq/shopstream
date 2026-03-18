"""Tests for order return lifecycle."""

from protean.testing import given

from ordering.order.cancellation import RefundOrder
from ordering.order.confirmation import ConfirmOrder
from ordering.order.creation import CreateOrder
from ordering.order.events import OrderReturned, ReturnApproved, ReturnRequested
from ordering.order.fulfillment import RecordDelivery, RecordShipment
from ordering.order.order import ItemStatus, Order, OrderStatus
from ordering.order.payment import RecordPaymentPending, RecordPaymentSuccess
from ordering.order.returns import ApproveReturn, RecordReturn, RequestReturn

CREATE_ORDER_ARGS = {
    "customer_id": "cust-001",
    "items": [
        {"product_id": "p1", "variant_id": "v1", "sku": "S1", "title": "P1", "quantity": 1, "unit_price": 30.0},
        {"product_id": "p2", "variant_id": "v2", "sku": "S2", "title": "P2", "quantity": 1, "unit_price": 20.0},
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


def _delivered_result():
    result = given(Order).process(CreateOrder(**CREATE_ORDER_ARGS))
    order_id = str(result.aggregate.id)
    result = (
        result.process(ConfirmOrder(order_id=order_id))
        .process(RecordPaymentPending(order_id=order_id, payment_id="pay-001", payment_method="cc"))
        .process(RecordPaymentSuccess(order_id=order_id, payment_id="pay-001", amount=50.0, payment_method="cc"))
        .process(
            RecordShipment(order_id=order_id, shipment_id="ship-001", carrier="FedEx", tracking_number="TRACK-001")
        )
        .process(RecordDelivery(order_id=order_id))
    )
    return result, order_id


class TestRequestReturn:
    def test_transitions_to_return_requested(self):
        result, order_id = _delivered_result()
        result = result.process(RequestReturn(order_id=order_id, reason="Defective product"))
        assert result.status == OrderStatus.RETURN_REQUESTED.value

    def test_raises_event(self):
        result, order_id = _delivered_result()
        result = result.process(RequestReturn(order_id=order_id, reason="Wrong size"))
        assert len(result.events) == 1
        assert ReturnRequested in result.events
        event = result.events[ReturnRequested]
        assert event.reason == "Wrong size"

    def test_cannot_return_from_created(self):
        result = given(Order).process(
            CreateOrder(
                customer_id="c",
                items=[
                    {"product_id": "p", "variant_id": "v", "sku": "S", "title": "T", "quantity": 1, "unit_price": 10.0}
                ],
                shipping_address={"street": "1 St", "city": "C", "postal_code": "00000", "country": "US"},
                billing_address={"street": "1 St", "city": "C", "postal_code": "00000", "country": "US"},
                subtotal=10.0,
                shipping_cost=0.0,
                tax_total=0.0,
                discount_total=0.0,
                grand_total=10.0,
                currency="USD",
            )
        )
        order_id = str(result.aggregate.id)
        result = result.process(RequestReturn(order_id=order_id, reason="reason"))
        assert result.rejected


class TestApproveReturn:
    def test_transitions_to_return_approved(self):
        result, order_id = _delivered_result()
        result = result.process(RequestReturn(order_id=order_id, reason="Defective")).process(
            ApproveReturn(order_id=order_id)
        )
        assert result.status == OrderStatus.RETURN_APPROVED.value

    def test_raises_event(self):
        result, order_id = _delivered_result()
        result = result.process(RequestReturn(order_id=order_id, reason="Defective")).process(
            ApproveReturn(order_id=order_id)
        )
        assert len(result.events) == 1
        assert ReturnApproved in result.events


class TestRecordReturn:
    def test_transitions_to_returned(self):
        result, order_id = _delivered_result()
        result = (
            result.process(RequestReturn(order_id=order_id, reason="Defective"))
            .process(ApproveReturn(order_id=order_id))
            .process(RecordReturn(order_id=order_id))
        )
        assert result.status == OrderStatus.RETURNED.value

    def test_marks_items_as_returned(self):
        result, order_id = _delivered_result()
        result = (
            result.process(RequestReturn(order_id=order_id, reason="Defective"))
            .process(ApproveReturn(order_id=order_id))
            .process(RecordReturn(order_id=order_id))
        )
        for item in result.aggregate.items:
            assert item.item_status == ItemStatus.RETURNED.value

    def test_partial_return(self):
        result, order_id = _delivered_result()
        result = result.process(RequestReturn(order_id=order_id, reason="Defective")).process(
            ApproveReturn(order_id=order_id)
        )
        item_id = str(result.aggregate.items[0].id)
        result = result.process(RecordReturn(order_id=order_id, returned_item_ids=[item_id]))
        assert result.aggregate.items[0].item_status == ItemStatus.RETURNED.value
        assert result.aggregate.items[1].item_status == ItemStatus.DELIVERED.value

    def test_raises_event(self):
        result, order_id = _delivered_result()
        result = (
            result.process(RequestReturn(order_id=order_id, reason="Defective"))
            .process(ApproveReturn(order_id=order_id))
            .process(RecordReturn(order_id=order_id))
        )
        assert len(result.events) == 1
        assert OrderReturned in result.events


class TestFullReturnLifecycle:
    def test_delivered_to_return_to_refunded(self):
        result, order_id = _delivered_result()
        result = (
            result.process(RequestReturn(order_id=order_id, reason="Defective"))
            .process(ApproveReturn(order_id=order_id))
            .process(RecordReturn(order_id=order_id))
            .process(RefundOrder(order_id=order_id))
        )
        assert result.status == OrderStatus.REFUNDED.value
