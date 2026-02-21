"""Application tests for OrderEventHandler — Fulfillment reacts to Ordering events.

Covers:
- on_order_cancelled: cancels in-progress fulfillment
- on_order_cancelled: skips when no fulfillment found
- on_order_cancelled: skips when fulfillment already shipped
"""

import json
from datetime import UTC, datetime

from fulfillment.fulfillment.creation import CreateFulfillment
from fulfillment.fulfillment.fulfillment import Fulfillment, FulfillmentStatus
from fulfillment.fulfillment.order_events import OrderEventHandler
from fulfillment.fulfillment.packing import GenerateShippingLabel, RecordPacking
from fulfillment.fulfillment.picking import AssignPicker, CompletePickList, RecordItemPicked
from fulfillment.fulfillment.shipping import RecordHandoff
from protean import current_domain
from shared.events.ordering import OrderCancelled


def _single_item_json():
    return json.dumps([{"order_item_id": "oi-1", "product_id": "prod-1", "sku": "SKU-001", "quantity": 1}])


def _create_fulfillment(order_id="ord-cancel-001"):
    return current_domain.process(
        CreateFulfillment(order_id=order_id, customer_id="cust-001", items=_single_item_json()),
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
        RecordPacking(fulfillment_id=ff_id, packed_by="Bob", packages=json.dumps([{"weight": 1.0}])),
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


class TestOrderCancelledHandler:
    def test_cancels_pending_fulfillment(self):
        """Fulfillment in PENDING state should be cancelled when order is cancelled."""
        order_id = "ord-cancel-pending"
        ff_id = _create_fulfillment(order_id=order_id)

        # Verify it's in PENDING state
        ff = current_domain.repository_for(Fulfillment).get(ff_id)
        assert ff.status == FulfillmentStatus.PENDING.value

        # Simulate the event handler receiving OrderCancelled
        handler = OrderEventHandler()
        handler.on_order_cancelled(
            OrderCancelled(
                order_id=order_id,
                reason="Customer changed mind",
                cancelled_by="Customer",
                cancelled_at=datetime.now(UTC),
            )
        )

        # Verify fulfillment was cancelled
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

        handler = OrderEventHandler()
        handler.on_order_cancelled(
            OrderCancelled(
                order_id=order_id,
                reason="Out of stock",
                cancelled_by="System",
                cancelled_at=datetime.now(UTC),
            )
        )

        ff = current_domain.repository_for(Fulfillment).get(ff_id)
        assert ff.status == FulfillmentStatus.CANCELLED.value

    def test_no_fulfillment_found_is_noop(self):
        """If no fulfillment exists for the order, handler returns without error."""
        handler = OrderEventHandler()
        # Should not raise — just logs and returns
        handler.on_order_cancelled(
            OrderCancelled(
                order_id="ord-nonexistent",
                reason="Test cancellation",
                cancelled_by="Customer",
                cancelled_at=datetime.now(UTC),
            )
        )

    def test_shipped_fulfillment_not_cancelled(self):
        """Fulfillment in SHIPPED state should NOT be cancelled."""
        order_id = "ord-cancel-shipped"
        ff_id = _create_fulfillment(order_id=order_id)
        _walk_to_shipped(ff_id)

        ff = current_domain.repository_for(Fulfillment).get(ff_id)
        assert ff.status == FulfillmentStatus.SHIPPED.value

        handler = OrderEventHandler()
        handler.on_order_cancelled(
            OrderCancelled(
                order_id=order_id,
                reason="Too late to cancel",
                cancelled_by="Customer",
                cancelled_at=datetime.now(UTC),
            )
        )

        # Fulfillment should still be SHIPPED
        ff = current_domain.repository_for(Fulfillment).get(ff_id)
        assert ff.status == FulfillmentStatus.SHIPPED.value
