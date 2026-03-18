"""Tests for order fulfillment — processing, shipment, delivery."""

from protean.testing import given

from ordering.order.confirmation import ConfirmOrder
from ordering.order.creation import CreateOrder
from ordering.order.events import OrderDelivered, OrderPartiallyShipped, OrderProcessing, OrderShipped
from ordering.order.fulfillment import MarkProcessing, RecordDelivery, RecordPartialShipment, RecordShipment
from ordering.order.order import ItemStatus, Order, OrderStatus
from ordering.order.payment import RecordPaymentPending, RecordPaymentSuccess

CREATE_ORDER_ARGS = {
    "customer_id": "cust-001",
    "items": [
        {"product_id": "p1", "variant_id": "v1", "sku": "S1", "title": "Product 1", "quantity": 1, "unit_price": 25.0},
        {"product_id": "p2", "variant_id": "v2", "sku": "S2", "title": "Product 2", "quantity": 1, "unit_price": 25.0},
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


def _paid_result():
    result = given(Order).process(CreateOrder(**CREATE_ORDER_ARGS))
    order_id = str(result.aggregate.id)
    result = (
        result.process(ConfirmOrder(order_id=order_id))
        .process(RecordPaymentPending(order_id=order_id, payment_id="pay-001", payment_method="cc"))
        .process(RecordPaymentSuccess(order_id=order_id, payment_id="pay-001", amount=50.0, payment_method="cc"))
    )
    return result, order_id


class TestMarkProcessing:
    def test_transitions_to_processing(self):
        result, order_id = _paid_result()
        result = result.process(MarkProcessing(order_id=order_id))
        assert result.status == OrderStatus.PROCESSING.value

    def test_raises_event(self):
        result, order_id = _paid_result()
        result = result.process(MarkProcessing(order_id=order_id))
        assert len(result.events) == 1
        assert OrderProcessing in result.events

    def test_cannot_process_from_created(self):
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
        result = result.process(MarkProcessing(order_id=order_id))
        assert result.rejected


class TestRecordShipment:
    def test_transitions_to_shipped(self):
        result, order_id = _paid_result()
        result = result.process(
            RecordShipment(order_id=order_id, shipment_id="ship-001", carrier="FedEx", tracking_number="TRACK-001")
        )
        assert result.status == OrderStatus.SHIPPED.value

    def test_sets_shipment_info(self):
        result, order_id = _paid_result()
        result = result.process(
            RecordShipment(
                order_id=order_id,
                shipment_id="ship-001",
                carrier="UPS",
                tracking_number="1Z999",
                estimated_delivery="2026-03-01",
            )
        )
        assert result.aggregate.carrier == "UPS"
        assert result.aggregate.tracking_number == "1Z999"
        assert result.aggregate.estimated_delivery == "2026-03-01"

    def test_updates_item_statuses(self):
        result, order_id = _paid_result()
        result = result.process(
            RecordShipment(order_id=order_id, shipment_id="ship-001", carrier="FedEx", tracking_number="TRACK-001")
        )
        for item in result.aggregate.items:
            assert item.item_status == ItemStatus.SHIPPED.value

    def test_raises_event(self):
        result, order_id = _paid_result()
        result = result.process(
            RecordShipment(order_id=order_id, shipment_id="ship-001", carrier="FedEx", tracking_number="TRACK-001")
        )
        assert len(result.events) == 1
        assert OrderShipped in result.events
        event = result.events[OrderShipped]
        assert event.carrier == "FedEx"

    def test_ship_from_processing(self):
        result, order_id = _paid_result()
        result = result.process(MarkProcessing(order_id=order_id)).process(
            RecordShipment(order_id=order_id, shipment_id="ship-001", carrier="FedEx", tracking_number="T")
        )
        assert result.status == OrderStatus.SHIPPED.value


class TestRecordPartialShipment:
    def test_transitions_to_partially_shipped(self):
        result, order_id = _paid_result()
        result = result.process(MarkProcessing(order_id=order_id))
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
        assert result.status == OrderStatus.PARTIALLY_SHIPPED.value

    def test_only_shipped_items_updated(self):
        result, order_id = _paid_result()
        result = result.process(MarkProcessing(order_id=order_id))
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
        assert result.aggregate.items[0].item_status == ItemStatus.SHIPPED.value
        assert result.aggregate.items[1].item_status == ItemStatus.PENDING.value

    def test_raises_event(self):
        result, order_id = _paid_result()
        result = result.process(MarkProcessing(order_id=order_id))
        item_id = str(result.aggregate.items[0].id)
        result = result.process(
            RecordPartialShipment(
                order_id=order_id,
                shipment_id="ship-001",
                carrier="FedEx",
                tracking_number="T",
                shipped_item_ids=[item_id],
            )
        )
        assert len(result.events) == 1
        assert OrderPartiallyShipped in result.events

    def test_cannot_partial_ship_from_paid(self):
        result, order_id = _paid_result()
        result = result.process(
            RecordPartialShipment(
                order_id=order_id, shipment_id="s", carrier="c", tracking_number="t", shipped_item_ids=["id"]
            )
        )
        assert result.rejected


class TestRecordDelivery:
    def test_transitions_to_delivered(self):
        result, order_id = _paid_result()
        result = result.process(
            RecordShipment(order_id=order_id, shipment_id="ship-001", carrier="FedEx", tracking_number="TRACK-001")
        ).process(RecordDelivery(order_id=order_id))
        assert result.status == OrderStatus.DELIVERED.value

    def test_updates_item_statuses(self):
        result, order_id = _paid_result()
        result = result.process(
            RecordShipment(order_id=order_id, shipment_id="ship-001", carrier="FedEx", tracking_number="TRACK-001")
        ).process(RecordDelivery(order_id=order_id))
        for item in result.aggregate.items:
            assert item.item_status == ItemStatus.DELIVERED.value

    def test_raises_event(self):
        result, order_id = _paid_result()
        result = result.process(
            RecordShipment(order_id=order_id, shipment_id="ship-001", carrier="FedEx", tracking_number="TRACK-001")
        ).process(RecordDelivery(order_id=order_id))
        assert len(result.events) == 1
        assert OrderDelivered in result.events
