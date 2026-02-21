"""Application tests for FulfillmentOrderEventHandler — Ordering reacts to Fulfillment events.

Covers:
- on_shipment_handed_off: records shipment on order via RecordShipment command
- on_delivery_confirmed: records delivery on order via RecordDelivery command
"""

import json
from datetime import UTC, datetime

from ordering.order.confirmation import ConfirmOrder
from ordering.order.creation import CreateOrder
from ordering.order.fulfillment import MarkProcessing, RecordShipment
from ordering.order.fulfillment_events import FulfillmentOrderEventHandler
from ordering.order.order import Order, OrderStatus
from ordering.order.payment import RecordPaymentPending, RecordPaymentSuccess
from protean import current_domain
from shared.events.fulfillment import DeliveryConfirmed, ShipmentHandedOff


def _create_paid_order():
    """Create an order and walk it through to PAID state."""
    order_id = current_domain.process(
        CreateOrder(
            customer_id="cust-001",
            items=json.dumps(
                [
                    {
                        "product_id": "prod-001",
                        "variant_id": "var-001",
                        "sku": "SKU-001",
                        "title": "Widget",
                        "quantity": 2,
                        "unit_price": 25.0,
                    },
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


class TestShipmentHandedOffHandler:
    def test_records_shipment_on_order(self):
        """ShipmentHandedOff event should transition order to SHIPPED."""
        order_id = _create_processing_order()

        handler = FulfillmentOrderEventHandler()
        handler.on_shipment_handed_off(
            ShipmentHandedOff(
                fulfillment_id="ff-001",
                order_id=order_id,
                carrier="FedEx",
                tracking_number="TRACK-SHIP-001",
                shipped_item_ids=json.dumps(["item-1", "item-2"]),
                shipped_at=datetime.now(UTC),
            )
        )

        order = current_domain.repository_for(Order).get(order_id)
        assert order.status == OrderStatus.SHIPPED.value
        assert order.carrier == "FedEx"
        assert order.tracking_number == "TRACK-SHIP-001"


class TestDeliveryConfirmedHandler:
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

        # Now handle delivery confirmation
        handler = FulfillmentOrderEventHandler()
        handler.on_delivery_confirmed(
            DeliveryConfirmed(
                fulfillment_id="ff-001",
                order_id=order_id,
                actual_delivery=datetime.now(UTC),
                delivered_at=datetime.now(UTC),
            )
        )

        order = current_domain.repository_for(Order).get(order_id)
        assert order.status == OrderStatus.DELIVERED.value
