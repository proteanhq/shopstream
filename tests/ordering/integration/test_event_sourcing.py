"""Integration tests for Event Sourcing specifics — event store round-trips,
event replay, and aggregate reconstruction.
"""

import json

from ordering.order.confirmation import ConfirmOrder
from ordering.order.creation import CreateOrder
from ordering.order.modification import AddItem, ApplyCoupon
from ordering.order.order import Order, OrderStatus
from ordering.order.payment import RecordPaymentPending, RecordPaymentSuccess
from protean import current_domain


def _create_order():
    return current_domain.process(
        CreateOrder(
            customer_id="cust-es-001",
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
                {"street": "1 St", "city": "C", "state": "S", "postal_code": "00000", "country": "US"}
            ),
            billing_address=json.dumps(
                {"street": "1 St", "city": "C", "state": "S", "postal_code": "00000", "country": "US"}
            ),
            subtotal=50.0,
            grand_total=55.0,
        ),
        asynchronous=False,
    )


class TestEventStorePersistence:
    def test_events_stored_in_event_store(self):
        """Verify that events are persisted in the event store after command processing."""
        order_id = _create_order()

        # Read events from the event store
        messages = current_domain.event_store.store.read(f"ordering::order-{order_id}")
        assert len(messages) >= 1
        assert messages[0].metadata.headers.type == "Ordering.OrderCreated.v1"

    def test_multiple_events_stored(self):
        """Verify multiple events accumulate in the event store."""
        order_id = _create_order()
        current_domain.process(ConfirmOrder(order_id=order_id), asynchronous=False)
        current_domain.process(
            RecordPaymentPending(order_id=order_id, payment_id="pay-001", payment_method="card"),
            asynchronous=False,
        )

        messages = current_domain.event_store.store.read(f"ordering::order-{order_id}")
        assert len(messages) >= 3

        event_types = [m.metadata.headers.type for m in messages]
        assert "Ordering.OrderCreated.v1" in event_types
        assert "Ordering.OrderConfirmed.v1" in event_types
        assert "Ordering.PaymentPending.v1" in event_types


class TestEventReplayRoundTrip:
    def test_aggregate_reconstructed_from_events(self):
        """Verify that loading an aggregate reconstructs correct state from events."""
        order_id = _create_order()

        # Load the aggregate — this triggers event replay via from_events()
        order = current_domain.repository_for(Order).get(order_id)

        assert order.id == order_id
        assert order.customer_id == "cust-es-001"
        assert order.status == OrderStatus.CREATED.value
        assert len(order.items) == 1
        assert order.items[0].product_id == "prod-001"
        assert order.items[0].quantity == 2

    def test_multi_step_replay(self):
        """Verify replay works through multiple state transitions."""
        order_id = _create_order()
        current_domain.process(ConfirmOrder(order_id=order_id), asynchronous=False)
        current_domain.process(
            RecordPaymentPending(order_id=order_id, payment_id="pay-001", payment_method="card"),
            asynchronous=False,
        )
        current_domain.process(
            RecordPaymentSuccess(order_id=order_id, payment_id="pay-001", amount=55.0, payment_method="card"),
            asynchronous=False,
        )

        # Reconstruct from event store
        order = current_domain.repository_for(Order).get(order_id)
        assert order.status == OrderStatus.PAID.value
        assert order.payment_id == "pay-001"
        assert order.payment_method == "card"

    def test_item_modifications_survive_replay(self):
        """Verify add_item events are correctly replayed with deterministic IDs."""
        order_id = _create_order()
        current_domain.process(
            AddItem(
                order_id=order_id,
                product_id="prod-002",
                variant_id="var-002",
                sku="SKU-002",
                title="Gadget",
                quantity=3,
                unit_price=10.0,
            ),
            asynchronous=False,
        )

        # First load
        order1 = current_domain.repository_for(Order).get(order_id)
        assert len(order1.items) == 2
        item_ids_1 = {str(i.id) for i in order1.items}

        # Second load (re-replay from event store)
        order2 = current_domain.repository_for(Order).get(order_id)
        item_ids_2 = {str(i.id) for i in order2.items}

        # IDs must be deterministic across replays
        assert item_ids_1 == item_ids_2

    def test_coupon_survives_replay(self):
        """Verify coupon application is replayed correctly."""
        order_id = _create_order()
        current_domain.process(
            ApplyCoupon(order_id=order_id, coupon_code="VIP50"),
            asynchronous=False,
        )

        order = current_domain.repository_for(Order).get(order_id)
        assert order.coupon_code == "VIP50"


class TestEventStoreStreamNaming:
    def test_stream_name_follows_convention(self):
        """Verify event store streams follow the ordering::order-{id} convention."""
        order_id = _create_order()
        stream_name = f"ordering::order-{order_id}"

        messages = current_domain.event_store.store.read(stream_name)
        assert len(messages) >= 1

    def test_event_version_is_v1(self):
        """Verify all events carry v1 version."""
        order_id = _create_order()
        messages = current_domain.event_store.store.read(f"ordering::order-{order_id}")

        for msg in messages:
            assert msg.metadata.headers.type.endswith(".v1")
