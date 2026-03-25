"""Application tests for OrderEventsSubscriber — Fulfillment reacts to Ordering events.

Tests the subscriber ACL pattern: raw dict payloads are filtered by event type
and translated into domain-local side effects.

Covers:
- OrderCancelled: cancels in-progress fulfillment
- OrderCancelled: skips when no fulfillment found
- OrderCancelled: skips when fulfillment already shipped
"""

from datetime import UTC, datetime

from protean import current_domain

from fulfillment.fulfillment.creation import CreateFulfillment
from fulfillment.fulfillment.fulfillment import Fulfillment, FulfillmentStatus
from fulfillment.fulfillment.order_subscriber import OrderEventsSubscriber
from fulfillment.fulfillment.packing import GenerateShippingLabel, RecordPacking
from fulfillment.fulfillment.picking import AssignPicker, CompletePickList, RecordItemPicked
from fulfillment.fulfillment.shipping import RecordHandoff


def _build_message(event_type: str, data: dict) -> dict:
    """Build a broker message payload with metadata and data."""
    return {
        "data": data,
        "metadata": {"headers": {"type": event_type}},
    }


def _single_item():
    return [{"order_item_id": "oi-1", "product_id": "prod-1", "sku": "SKU-001", "quantity": 1}]


def _create_fulfillment(order_id="ord-cancel-001"):
    return current_domain.process(
        CreateFulfillment(order_id=order_id, customer_id="cust-001", items=_single_item()),
        asynchronous=False,
    )


def _walk_to_shipped(ff_id):
    """Walk a fulfillment through the full pipeline to SHIPPED state."""
    current_domain.process(AssignPicker(fulfillment_id=ff_id, picker_name="Alice"), asynchronous=False)
    ff = current_domain.repository_for(Fulfillment).get(ff_id)
    current_domain.process(
        RecordItemPicked(fulfillment_id=ff_id, item_id=str(ff.items[0].id), pick_location="A-1"),
        asynchronous=False,
    )
    current_domain.process(CompletePickList(fulfillment_id=ff_id), asynchronous=False)
    current_domain.process(
        RecordPacking(fulfillment_id=ff_id, packed_by="Bob", packages=[{"weight": 1.0}]),
        asynchronous=False,
    )
    current_domain.process(
        GenerateShippingLabel(
            fulfillment_id=ff_id,
            label_url="https://labels.example.com/abc.pdf",
            carrier="FakeCarrier",
            service_level="Standard",
        ),
        asynchronous=False,
    )
    current_domain.process(
        RecordHandoff(fulfillment_id=ff_id, tracking_number="TRACK-001"),
        asynchronous=False,
    )


class TestOrderCancelledSubscriber:
    def test_cancels_pending_fulfillment(self):
        """Fulfillment in PENDING state should be cancelled when order is cancelled."""
        order_id = "ord-cancel-pending"
        ff_id = _create_fulfillment(order_id=order_id)

        ff = current_domain.repository_for(Fulfillment).get(ff_id)
        assert ff.status == FulfillmentStatus.PENDING.value

        subscriber = OrderEventsSubscriber()
        subscriber(
            _build_message(
                "Ordering.OrderCancelled.v1",
                {
                    "order_id": order_id,
                    "reason": "Customer changed mind",
                    "cancelled_by": "Customer",
                    "cancelled_at": datetime.now(UTC).isoformat(),
                },
            )
        )

        ff = current_domain.repository_for(Fulfillment).get(ff_id)
        assert ff.status == FulfillmentStatus.CANCELLED.value
        assert "Customer changed mind" in ff.cancellation_reason

    def test_cancels_picking_fulfillment(self):
        """Fulfillment in PICKING state should be cancelled when order is cancelled."""
        order_id = "ord-cancel-picking"
        ff_id = _create_fulfillment(order_id=order_id)
        current_domain.process(AssignPicker(fulfillment_id=ff_id, picker_name="Alice"), asynchronous=False)

        ff = current_domain.repository_for(Fulfillment).get(ff_id)
        assert ff.status == FulfillmentStatus.PICKING.value

        subscriber = OrderEventsSubscriber()
        subscriber(
            _build_message(
                "Ordering.OrderCancelled.v1",
                {
                    "order_id": order_id,
                    "reason": "Out of stock",
                    "cancelled_by": "System",
                    "cancelled_at": datetime.now(UTC).isoformat(),
                },
            )
        )

        ff = current_domain.repository_for(Fulfillment).get(ff_id)
        assert ff.status == FulfillmentStatus.CANCELLED.value

    def test_no_fulfillment_found_is_noop(self):
        """If no fulfillment exists for the order, subscriber returns without error."""
        subscriber = OrderEventsSubscriber()
        subscriber(
            _build_message(
                "Ordering.OrderCancelled.v1",
                {
                    "order_id": "ord-nonexistent",
                    "reason": "Test cancellation",
                    "cancelled_by": "Customer",
                    "cancelled_at": datetime.now(UTC).isoformat(),
                },
            )
        )

    def test_shipped_fulfillment_not_cancelled(self):
        """Fulfillment in SHIPPED state should NOT be cancelled."""
        order_id = "ord-cancel-shipped"
        ff_id = _create_fulfillment(order_id=order_id)
        _walk_to_shipped(ff_id)

        ff = current_domain.repository_for(Fulfillment).get(ff_id)
        assert ff.status == FulfillmentStatus.SHIPPED.value

        subscriber = OrderEventsSubscriber()
        subscriber(
            _build_message(
                "Ordering.OrderCancelled.v1",
                {
                    "order_id": order_id,
                    "reason": "Too late to cancel",
                    "cancelled_by": "Customer",
                    "cancelled_at": datetime.now(UTC).isoformat(),
                },
            )
        )

        ff = current_domain.repository_for(Fulfillment).get(ff_id)
        assert ff.status == FulfillmentStatus.SHIPPED.value

    def test_ignores_non_cancelled_events(self):
        """Non-OrderCancelled events on the ordering stream are ignored."""
        subscriber = OrderEventsSubscriber()
        subscriber(
            _build_message(
                "Ordering.OrderCreated.v2",
                {
                    "order_id": "ord-ignore",
                    "customer_id": "cust-001",
                },
            )
        )
