"""Integration tests for Order projections — verify projectors update read models."""

import json

from ordering.order.cancellation import CancelOrder
from ordering.order.completion import CompleteOrder
from ordering.order.confirmation import ConfirmOrder
from ordering.order.creation import CreateOrder
from ordering.order.fulfillment import MarkProcessing, RecordDelivery, RecordShipment
from ordering.order.payment import RecordPaymentPending, RecordPaymentSuccess
from ordering.order.returns import ApproveReturn, RequestReturn
from ordering.projections.customer_orders import CustomerOrders
from ordering.projections.order_detail import OrderDetail
from ordering.projections.order_summary import OrderSummary
from ordering.projections.order_timeline import OrderTimeline
from ordering.projections.orders_by_status import OrdersByStatus
from protean import current_domain


def _create_order(customer_id="cust-proj-001"):
    return current_domain.process(
        CreateOrder(
            customer_id=customer_id,
            items=json.dumps(
                [
                    {
                        "product_id": "prod-001",
                        "variant_id": "var-001",
                        "sku": "SKU-001",
                        "title": "Widget",
                        "quantity": 2,
                        "unit_price": 25.0,
                    }
                ]
            ),
            shipping_address=json.dumps(
                {"street": "123 Main", "city": "Town", "state": "CA", "postal_code": "90210", "country": "US"}
            ),
            billing_address=json.dumps(
                {"street": "123 Main", "city": "Town", "state": "CA", "postal_code": "90210", "country": "US"}
            ),
            subtotal=50.0,
            grand_total=55.0,
        ),
        asynchronous=False,
    )


def _advance_to_paid(order_id):
    current_domain.process(ConfirmOrder(order_id=order_id), asynchronous=False)
    current_domain.process(
        RecordPaymentPending(order_id=order_id, payment_id="pay-001", payment_method="card"),
        asynchronous=False,
    )
    current_domain.process(
        RecordPaymentSuccess(order_id=order_id, payment_id="pay-001", amount=55.0, payment_method="card"),
        asynchronous=False,
    )


def _advance_to_delivered(order_id):
    current_domain.process(MarkProcessing(order_id=order_id), asynchronous=False)
    current_domain.process(
        RecordShipment(
            order_id=order_id,
            shipment_id="ship-001",
            carrier="FedEx",
            tracking_number="TRACK-001",
        ),
        asynchronous=False,
    )
    current_domain.process(RecordDelivery(order_id=order_id), asynchronous=False)


class TestOrderDetailProjection:
    def test_created_on_order_creation(self):
        order_id = _create_order()
        detail = current_domain.repository_for(OrderDetail).get(order_id)

        assert detail.order_id == order_id
        assert detail.customer_id == "cust-proj-001"
        assert detail.status == "Created"
        assert detail.grand_total == 55.0

    def test_updated_through_lifecycle(self):
        order_id = _create_order()
        _advance_to_paid(order_id)

        detail = current_domain.repository_for(OrderDetail).get(order_id)
        assert detail.status == "Paid"
        assert detail.payment_id == "pay-001"
        assert detail.payment_method == "card"
        assert detail.payment_status == "succeeded"

    def test_cancellation_updates_detail(self):
        order_id = _create_order()
        current_domain.process(
            CancelOrder(order_id=order_id, reason="Changed mind", cancelled_by="Customer"),
            asynchronous=False,
        )

        detail = current_domain.repository_for(OrderDetail).get(order_id)
        assert detail.status == "Cancelled"
        assert detail.cancellation_reason == "Changed mind"
        assert detail.cancelled_by == "Customer"

    def test_shipment_updates_detail(self):
        order_id = _create_order()
        _advance_to_paid(order_id)
        current_domain.process(MarkProcessing(order_id=order_id), asynchronous=False)
        current_domain.process(
            RecordShipment(
                order_id=order_id,
                shipment_id="ship-001",
                carrier="UPS",
                tracking_number="1Z999",
            ),
            asynchronous=False,
        )

        detail = current_domain.repository_for(OrderDetail).get(order_id)
        assert detail.status == "Shipped"
        assert detail.carrier == "UPS"
        assert detail.tracking_number == "1Z999"


class TestOrderSummaryProjection:
    def test_created_on_order_creation(self):
        order_id = _create_order()
        summary = current_domain.repository_for(OrderSummary).get(order_id)

        assert summary.order_id == order_id
        assert summary.customer_id == "cust-proj-001"
        assert summary.status == "Created"
        assert summary.item_count == 1
        assert summary.grand_total == 55.0

    def test_status_updated_through_lifecycle(self):
        order_id = _create_order()
        _advance_to_paid(order_id)

        summary = current_domain.repository_for(OrderSummary).get(order_id)
        assert summary.status == "Paid"


class TestOrderTimelineProjection:
    def test_entries_created_for_lifecycle_events(self):
        order_id = _create_order()
        current_domain.process(ConfirmOrder(order_id=order_id), asynchronous=False)

        repo = current_domain.repository_for(OrderTimeline)
        entries = repo._dao.query.filter(order_id=order_id).all().items

        assert len(entries) >= 2
        event_types = [e.event_type for e in entries]
        assert "OrderCreated" in event_types
        assert "OrderConfirmed" in event_types

    def test_timeline_grows_with_events(self):
        order_id = _create_order()
        _advance_to_paid(order_id)

        repo = current_domain.repository_for(OrderTimeline)
        entries = repo._dao.query.filter(order_id=order_id).all().items

        # OrderCreated + OrderConfirmed + PaymentPending + PaymentSucceeded = 4
        assert len(entries) >= 4


class TestCustomerOrdersProjection:
    def test_created_on_order_creation(self):
        order_id = _create_order()
        record = current_domain.repository_for(CustomerOrders).get(order_id)

        assert record.customer_id == "cust-proj-001"
        assert record.status == "Created"

    def test_status_tracks_lifecycle(self):
        order_id = _create_order()
        _advance_to_paid(order_id)
        _advance_to_delivered(order_id)
        current_domain.process(CompleteOrder(order_id=order_id), asynchronous=False)

        record = current_domain.repository_for(CustomerOrders).get(order_id)
        assert record.status == "Completed"


class TestOrdersByStatusProjection:
    def test_created_on_order_creation(self):
        order_id = _create_order()
        record = current_domain.repository_for(OrdersByStatus).get(order_id)

        assert record.status == "Created"
        assert record.customer_id == "cust-proj-001"

    def test_status_updates(self):
        order_id = _create_order()
        current_domain.process(ConfirmOrder(order_id=order_id), asynchronous=False)

        record = current_domain.repository_for(OrdersByStatus).get(order_id)
        assert record.status == "Confirmed"

    def test_return_flow_updates_status(self):
        order_id = _create_order()
        _advance_to_paid(order_id)
        _advance_to_delivered(order_id)

        current_domain.process(RequestReturn(order_id=order_id, reason="Wrong item"), asynchronous=False)
        record = current_domain.repository_for(OrdersByStatus).get(order_id)
        assert record.status == "Return_Requested"

        current_domain.process(ApproveReturn(order_id=order_id), asynchronous=False)
        record = current_domain.repository_for(OrdersByStatus).get(order_id)
        assert record.status == "Return_Approved"
