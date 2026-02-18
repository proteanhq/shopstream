"""Application tests for order cancellation and refund commands."""

import json

from ordering.order.cancellation import CancelOrder, RefundOrder
from ordering.order.confirmation import ConfirmOrder
from ordering.order.creation import CreateOrder
from ordering.order.order import Order, OrderStatus
from ordering.order.payment import RecordPaymentPending, RecordPaymentSuccess
from protean import current_domain


def _create_order():
    return current_domain.process(
        CreateOrder(
            customer_id="cust-001",
            items=json.dumps(
                [
                    {
                        "product_id": "p1",
                        "variant_id": "v1",
                        "sku": "S1",
                        "title": "Item",
                        "quantity": 1,
                        "unit_price": 100.0,
                    }
                ]
            ),
            shipping_address=json.dumps(
                {"street": "1 St", "city": "C", "state": "S", "postal_code": "00000", "country": "US"}
            ),
            billing_address=json.dumps(
                {"street": "1 St", "city": "C", "state": "S", "postal_code": "00000", "country": "US"}
            ),
            subtotal=100.0,
            grand_total=110.0,
        ),
        asynchronous=False,
    )


def _create_paid_order():
    order_id = _create_order()
    current_domain.process(ConfirmOrder(order_id=order_id), asynchronous=False)
    current_domain.process(
        RecordPaymentPending(order_id=order_id, payment_id="pay-001", payment_method="card"),
        asynchronous=False,
    )
    current_domain.process(
        RecordPaymentSuccess(order_id=order_id, payment_id="pay-001", amount=110.0, payment_method="card"),
        asynchronous=False,
    )
    return order_id


class TestCancelOrderCommand:
    def test_cancel_persists(self):
        order_id = _create_order()
        current_domain.process(
            CancelOrder(order_id=order_id, reason="Not needed", cancelled_by="Customer"),
            asynchronous=False,
        )
        order = current_domain.repository_for(Order).get(order_id)
        assert order.status == OrderStatus.CANCELLED.value
        assert order.cancellation_reason == "Not needed"

    def test_cancel_paid_order(self):
        order_id = _create_paid_order()
        current_domain.process(
            CancelOrder(order_id=order_id, reason="Found cheaper", cancelled_by="Customer"),
            asynchronous=False,
        )
        order = current_domain.repository_for(Order).get(order_id)
        assert order.status == OrderStatus.CANCELLED.value


class TestRefundOrderCommand:
    def test_refund_after_cancel(self):
        order_id = _create_paid_order()
        current_domain.process(
            CancelOrder(order_id=order_id, reason="Mistake", cancelled_by="System"),
            asynchronous=False,
        )
        current_domain.process(
            RefundOrder(order_id=order_id),
            asynchronous=False,
        )
        order = current_domain.repository_for(Order).get(order_id)
        assert order.status == OrderStatus.REFUNDED.value
