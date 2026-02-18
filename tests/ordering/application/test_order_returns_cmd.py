"""Application tests for order return flow."""

import json

from ordering.order.cancellation import RefundOrder
from ordering.order.confirmation import ConfirmOrder
from ordering.order.creation import CreateOrder
from ordering.order.fulfillment import (
    MarkProcessing,
    RecordDelivery,
    RecordShipment,
)
from ordering.order.order import Order, OrderStatus
from ordering.order.payment import RecordPaymentPending, RecordPaymentSuccess
from ordering.order.returns import ApproveReturn, RecordReturn, RequestReturn
from protean import current_domain


def _create_delivered_order():
    order_id = current_domain.process(
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
    current_domain.process(ConfirmOrder(order_id=order_id), asynchronous=False)
    current_domain.process(
        RecordPaymentPending(order_id=order_id, payment_id="pay-001", payment_method="card"),
        asynchronous=False,
    )
    current_domain.process(
        RecordPaymentSuccess(order_id=order_id, payment_id="pay-001", amount=110.0, payment_method="card"),
        asynchronous=False,
    )
    current_domain.process(MarkProcessing(order_id=order_id), asynchronous=False)
    current_domain.process(
        RecordShipment(
            order_id=order_id,
            shipment_id="ship-001",
            carrier="UPS",
            tracking_number="TRACK-001",
        ),
        asynchronous=False,
    )
    current_domain.process(RecordDelivery(order_id=order_id), asynchronous=False)
    return order_id


class TestFullReturnFlow:
    def test_return_flow_to_refund(self):
        order_id = _create_delivered_order()
        repo = current_domain.repository_for(Order)

        # Request return
        current_domain.process(
            RequestReturn(order_id=order_id, reason="Defective"),
            asynchronous=False,
        )
        order = repo.get(order_id)
        assert order.status == OrderStatus.RETURN_REQUESTED.value

        # Approve return
        current_domain.process(
            ApproveReturn(order_id=order_id),
            asynchronous=False,
        )
        order = repo.get(order_id)
        assert order.status == OrderStatus.RETURN_APPROVED.value

        # Record return
        item_ids = json.dumps([str(order.items[0].id)])
        current_domain.process(
            RecordReturn(order_id=order_id, returned_item_ids=item_ids),
            asynchronous=False,
        )
        order = repo.get(order_id)
        assert order.status == OrderStatus.RETURNED.value

        # Refund
        current_domain.process(
            RefundOrder(order_id=order_id),
            asynchronous=False,
        )
        order = repo.get(order_id)
        assert order.status == OrderStatus.REFUNDED.value
