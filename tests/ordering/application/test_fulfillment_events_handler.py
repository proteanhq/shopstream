"""Application tests for FulfillmentEventsSubscriber — Ordering reacts to Fulfillment events.

Tests the subscriber ACL pattern: raw dict payloads are filtered by event type
and translated into domain commands (RecordShipment, RecordDelivery).
"""

from datetime import UTC, datetime

from protean import current_domain

from ordering.order.confirmation import ConfirmOrder
from ordering.order.creation import CreateOrder
from ordering.order.fulfillment import MarkProcessing, RecordShipment
from ordering.order.fulfillment_subscriber import FulfillmentEventsSubscriber
from ordering.order.order import Order, OrderStatus
from ordering.order.payment import RecordPaymentPending, RecordPaymentSuccess


def _build_message(event_type: str, data: dict) -> dict:
    """Build a broker message payload with metadata and data."""
    return {
        "data": data,
        "metadata": {"headers": {"type": event_type}},
    }


def _create_paid_order():
    """Create an order and walk it through to PAID state."""
    order_id = current_domain.process(
        CreateOrder(
            customer_id="cust-001",
            items=[
                {
                    "product_id": "prod-001",
                    "variant_id": "var-001",
                    "sku": "SKU-001",
                    "title": "Widget",
                    "quantity": 2,
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
            subtotal=50.0,
            grand_total=55.0,
        ),
        asynchronous=False,
    )
    current_domain.process(ConfirmOrder(order_id=order_id), asynchronous=False)
    current_domain.process(
        RecordPaymentPending(order_id=order_id, payment_id="pay-001", payment_method="credit_card"),
        asynchronous=False,
    )
    current_domain.process(
        RecordPaymentSuccess(order_id=order_id, payment_id="pay-001", amount=55.0, payment_method="credit_card"),
        asynchronous=False,
    )
    return order_id


def _create_processing_order():
    """Create an order in PROCESSING state."""
    order_id = _create_paid_order()
    current_domain.process(MarkProcessing(order_id=order_id), asynchronous=False)
    return order_id


class TestShipmentHandedOffSubscriber:
    def test_records_shipment_on_order(self):
        """ShipmentHandedOff event should transition order to SHIPPED."""
        order_id = _create_processing_order()

        subscriber = FulfillmentEventsSubscriber()
        subscriber(
            _build_message(
                "Fulfillment.ShipmentHandedOff.v1",
                {
                    "fulfillment_id": "ff-001",
                    "order_id": order_id,
                    "carrier": "FedEx",
                    "tracking_number": "TRACK-SHIP-001",
                    "shipped_item_ids": ["item-1", "item-2"],
                    "shipped_at": datetime.now(UTC).isoformat(),
                },
            )
        )

        order = current_domain.repository_for(Order).get(order_id)
        assert order.status == OrderStatus.SHIPPED.value
        assert order.carrier == "FedEx"
        assert order.tracking_number == "TRACK-SHIP-001"


class TestDeliveryConfirmedSubscriber:
    def test_records_delivery_on_order(self):
        """DeliveryConfirmed event should transition order to DELIVERED."""
        order_id = _create_processing_order()

        # First ship the order
        current_domain.process(
            RecordShipment(
                order_id=order_id,
                shipment_id="ship-001",
                carrier="FedEx",
                tracking_number="TRACK-001",
            ),
            asynchronous=False,
        )

        order = current_domain.repository_for(Order).get(order_id)
        assert order.status == OrderStatus.SHIPPED.value

        # Now handle delivery confirmation via subscriber
        subscriber = FulfillmentEventsSubscriber()
        subscriber(
            _build_message(
                "Fulfillment.DeliveryConfirmed.v1",
                {
                    "fulfillment_id": "ff-001",
                    "order_id": order_id,
                    "actual_delivery": datetime.now(UTC).isoformat(),
                    "delivered_at": datetime.now(UTC).isoformat(),
                },
            )
        )

        order = current_domain.repository_for(Order).get(order_id)
        assert order.status == OrderStatus.DELIVERED.value


class TestDeliveryExceptionSubscriber:
    def test_logs_delivery_exception(self):
        """DeliveryException should be logged without changing order state."""
        order_id = _create_processing_order()

        # Ship the order first
        current_domain.process(
            RecordShipment(
                order_id=order_id,
                shipment_id="ship-001",
                carrier="FedEx",
                tracking_number="TRACK-001",
            ),
            asynchronous=False,
        )

        subscriber = FulfillmentEventsSubscriber()
        subscriber(
            _build_message(
                "Fulfillment.DeliveryException.v1",
                {
                    "fulfillment_id": "ff-001",
                    "order_id": order_id,
                    "reason": "Failed delivery attempt",
                    "location": "Front door",
                },
            )
        )

        # Order should still be SHIPPED (exception doesn't change state)
        order = current_domain.repository_for(Order).get(order_id)
        assert order.status == OrderStatus.SHIPPED.value


class TestIgnoresUnrelatedEvents:
    def test_ignores_non_fulfillment_events(self):
        """Non-fulfillment events on the stream should be ignored."""
        subscriber = FulfillmentEventsSubscriber()
        subscriber(_build_message("Fulfillment.PickerAssigned.v1", {"fulfillment_id": "ff-ignore"}))
