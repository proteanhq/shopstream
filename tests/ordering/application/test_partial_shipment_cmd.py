"""Application tests for RecordPartialShipment command handler.

Covers:
- Partial shipment transitions order to PARTIALLY_SHIPPED
- Partial shipment marks only specified items as shipped
- Subsequent full shipment moves order to SHIPPED
- Partial shipment fails from non-PROCESSING state
- shipped_item_ids parsing from JSON string
"""

import json

import pytest
from ordering.order.confirmation import ConfirmOrder
from ordering.order.creation import CreateOrder
from ordering.order.fulfillment import MarkProcessing, RecordPartialShipment, RecordShipment
from ordering.order.order import ItemStatus, Order, OrderStatus
from ordering.order.payment import RecordPaymentPending, RecordPaymentSuccess
from protean import current_domain
from protean.exceptions import ValidationError


def _create_processing_order():
    """Create an order with 2 items in PROCESSING state."""
    order_id = current_domain.process(
        CreateOrder(
            customer_id="cust-001",
            items=json.dumps(
                [
                    {
                        "product_id": "prod-001",
                        "variant_id": "var-001",
                        "sku": "SKU-001",
                        "title": "Widget A",
                        "quantity": 1,
                        "unit_price": 25.0,
                    },
                    {
                        "product_id": "prod-002",
                        "variant_id": "var-002",
                        "sku": "SKU-002",
                        "title": "Widget B",
                        "quantity": 1,
                        "unit_price": 30.0,
                    },
                ]
            ),
            shipping_address=json.dumps(
                {"street": "123 Main", "city": "Town", "state": "CA", "postal_code": "90210", "country": "US"}
            ),
            billing_address=json.dumps(
                {"street": "123 Main", "city": "Town", "state": "CA", "postal_code": "90210", "country": "US"}
            ),
            subtotal=55.0,
            grand_total=60.0,
        ),
        asynchronous=False,
    )
    current_domain.process(ConfirmOrder(order_id=order_id), asynchronous=False)
    current_domain.process(
        RecordPaymentPending(order_id=order_id, payment_id="pay-001", payment_method="credit_card"),
        asynchronous=False,
    )
    current_domain.process(
        RecordPaymentSuccess(order_id=order_id, payment_id="pay-001", amount=60.0, payment_method="credit_card"),
        asynchronous=False,
    )
    current_domain.process(MarkProcessing(order_id=order_id), asynchronous=False)
    return order_id


class TestRecordPartialShipment:
    def test_partial_shipment_transitions_to_partially_shipped(self):
        order_id = _create_processing_order()
        order = current_domain.repository_for(Order).get(order_id)
        first_item_id = str(order.items[0].id)

        current_domain.process(
            RecordPartialShipment(
                order_id=order_id,
                shipment_id="ship-partial-001",
                carrier="FedEx",
                tracking_number="TRACK-P-001",
                shipped_item_ids=json.dumps([first_item_id]),
            ),
            asynchronous=False,
        )

        order = current_domain.repository_for(Order).get(order_id)
        assert order.status == OrderStatus.PARTIALLY_SHIPPED.value

    def test_partial_shipment_marks_only_specified_items(self):
        order_id = _create_processing_order()
        order = current_domain.repository_for(Order).get(order_id)
        first_item_id = str(order.items[0].id)
        second_item_id = str(order.items[1].id)

        current_domain.process(
            RecordPartialShipment(
                order_id=order_id,
                shipment_id="ship-partial-002",
                carrier="FedEx",
                tracking_number="TRACK-P-002",
                shipped_item_ids=json.dumps([first_item_id]),
            ),
            asynchronous=False,
        )

        order = current_domain.repository_for(Order).get(order_id)
        shipped_item = next(i for i in order.items if str(i.id) == first_item_id)
        pending_item = next(i for i in order.items if str(i.id) == second_item_id)
        assert shipped_item.item_status == ItemStatus.SHIPPED.value
        assert pending_item.item_status == ItemStatus.PENDING.value

    def test_full_shipment_after_partial_moves_to_shipped(self):
        order_id = _create_processing_order()
        order = current_domain.repository_for(Order).get(order_id)
        first_item_id = str(order.items[0].id)

        # Partial shipment first
        current_domain.process(
            RecordPartialShipment(
                order_id=order_id,
                shipment_id="ship-partial-003",
                carrier="FedEx",
                tracking_number="TRACK-P-003",
                shipped_item_ids=json.dumps([first_item_id]),
            ),
            asynchronous=False,
        )

        # Full shipment (remaining items)
        current_domain.process(
            RecordShipment(
                order_id=order_id,
                shipment_id="ship-full-003",
                carrier="FedEx",
                tracking_number="TRACK-F-003",
            ),
            asynchronous=False,
        )

        order = current_domain.repository_for(Order).get(order_id)
        assert order.status == OrderStatus.SHIPPED.value

    def test_partial_shipment_fails_from_paid_state(self):
        """Partial shipment requires PROCESSING state."""
        order_id = current_domain.process(
            CreateOrder(
                customer_id="cust-002",
                items=json.dumps(
                    [
                        {
                            "product_id": "prod-001",
                            "variant_id": "var-001",
                            "sku": "SKU-001",
                            "title": "Widget",
                            "quantity": 1,
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
                subtotal=25.0,
                grand_total=25.0,
            ),
            asynchronous=False,
        )
        current_domain.process(ConfirmOrder(order_id=order_id), asynchronous=False)
        current_domain.process(
            RecordPaymentPending(order_id=order_id, payment_id="pay-002", payment_method="credit_card"),
            asynchronous=False,
        )
        current_domain.process(
            RecordPaymentSuccess(order_id=order_id, payment_id="pay-002", amount=25.0, payment_method="credit_card"),
            asynchronous=False,
        )
        # Order is in PAID state, not PROCESSING

        with pytest.raises(ValidationError):
            current_domain.process(
                RecordPartialShipment(
                    order_id=order_id,
                    shipment_id="ship-fail",
                    carrier="FedEx",
                    tracking_number="TRACK-FAIL",
                    shipped_item_ids=json.dumps(["item-1"]),
                ),
                asynchronous=False,
            )

    def test_shipped_item_ids_json_string_parsing(self):
        """Verify that shipped_item_ids as JSON string is parsed correctly."""
        order_id = _create_processing_order()
        order = current_domain.repository_for(Order).get(order_id)
        first_item_id = str(order.items[0].id)

        # Pass shipped_item_ids as a JSON string
        current_domain.process(
            RecordPartialShipment(
                order_id=order_id,
                shipment_id="ship-json-001",
                carrier="UPS",
                tracking_number="TRACK-JSON-001",
                shipped_item_ids=json.dumps([first_item_id]),
            ),
            asynchronous=False,
        )

        order = current_domain.repository_for(Order).get(order_id)
        assert order.status == OrderStatus.PARTIALLY_SHIPPED.value
        shipped_item = next(i for i in order.items if str(i.id) == first_item_id)
        assert shipped_item.item_status == ItemStatus.SHIPPED.value
