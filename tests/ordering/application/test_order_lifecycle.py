"""Application tests for full order lifecycle through event store.

Tests the complete happy path: create → confirm → payment → processing →
ship → deliver → complete, verifying state is correctly persisted and
reconstructed from the event store at each step.
"""

import json

from ordering.order.cancellation import CancelOrder
from ordering.order.completion import CompleteOrder
from ordering.order.confirmation import ConfirmOrder
from ordering.order.creation import CreateOrder
from ordering.order.fulfillment import MarkProcessing, RecordDelivery, RecordShipment
from ordering.order.order import Order, OrderStatus
from ordering.order.payment import RecordPaymentPending, RecordPaymentSuccess
from protean import current_domain


def _create_order():
    command = CreateOrder(
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
    )
    return current_domain.process(command, asynchronous=False)


class TestFullOrderLifecycle:
    def test_happy_path_to_completion(self):
        """Create → Confirm → PaymentPending → Paid → Processing → Shipped → Delivered → Completed."""
        repo = current_domain.repository_for(Order)

        # 1. Create
        order_id = _create_order()
        order = repo.get(order_id)
        assert order.status == OrderStatus.CREATED.value

        # 2. Confirm
        current_domain.process(ConfirmOrder(order_id=order_id), asynchronous=False)
        order = repo.get(order_id)
        assert order.status == OrderStatus.CONFIRMED.value

        # 3. Payment pending
        current_domain.process(
            RecordPaymentPending(
                order_id=order_id,
                payment_id="pay-001",
                payment_method="credit_card",
            ),
            asynchronous=False,
        )
        order = repo.get(order_id)
        assert order.status == OrderStatus.PAYMENT_PENDING.value
        assert order.payment_id == "pay-001"

        # 4. Payment success
        current_domain.process(
            RecordPaymentSuccess(
                order_id=order_id,
                payment_id="pay-001",
                amount=55.0,
                payment_method="credit_card",
            ),
            asynchronous=False,
        )
        order = repo.get(order_id)
        assert order.status == OrderStatus.PAID.value

        # 5. Processing
        current_domain.process(MarkProcessing(order_id=order_id), asynchronous=False)
        order = repo.get(order_id)
        assert order.status == OrderStatus.PROCESSING.value

        # 6. Shipped
        current_domain.process(
            RecordShipment(
                order_id=order_id,
                shipment_id="ship-001",
                carrier="FedEx",
                tracking_number="TRACK-001",
            ),
            asynchronous=False,
        )
        order = repo.get(order_id)
        assert order.status == OrderStatus.SHIPPED.value
        assert order.carrier == "FedEx"

        # 7. Delivered
        current_domain.process(RecordDelivery(order_id=order_id), asynchronous=False)
        order = repo.get(order_id)
        assert order.status == OrderStatus.DELIVERED.value

        # 8. Completed
        current_domain.process(CompleteOrder(order_id=order_id), asynchronous=False)
        order = repo.get(order_id)
        assert order.status == OrderStatus.COMPLETED.value

    def test_cancel_from_created(self):
        order_id = _create_order()
        current_domain.process(
            CancelOrder(
                order_id=order_id,
                reason="Changed my mind",
                cancelled_by="Customer",
            ),
            asynchronous=False,
        )
        order = current_domain.repository_for(Order).get(order_id)
        assert order.status == OrderStatus.CANCELLED.value
        assert order.cancellation_reason == "Changed my mind"
