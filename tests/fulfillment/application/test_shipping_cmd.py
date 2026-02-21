"""Application tests for shipping handoff command via domain.process()."""

import json
from datetime import UTC, datetime, timedelta

import pytest
from fulfillment.fulfillment.creation import CreateFulfillment
from fulfillment.fulfillment.fulfillment import Fulfillment, FulfillmentStatus
from fulfillment.fulfillment.packing import GenerateShippingLabel, RecordPacking
from fulfillment.fulfillment.picking import AssignPicker, CompletePickList, RecordItemPicked
from fulfillment.fulfillment.shipping import RecordHandoff
from protean import current_domain
from protean.exceptions import ValidationError


def _create_ready_to_ship():
    """Create a fulfillment in READY_TO_SHIP state."""
    items = json.dumps([{"order_item_id": "oi-1", "product_id": "prod-1", "sku": "SKU-001", "quantity": 1}])
    ff_id = current_domain.process(
        CreateFulfillment(order_id="ord-001", customer_id="cust-001", items=items),
        asynchronous=False,
    )
    current_domain.process(AssignPicker(fulfillment_id=ff_id, picker_name="Alice"), asynchronous=False)
    ff = current_domain.repository_for(Fulfillment).get(ff_id)
    current_domain.process(
        RecordItemPicked(fulfillment_id=ff_id, item_id=str(ff.items[0].id), pick_location="A-1"),
        asynchronous=False,
    )
    current_domain.process(CompletePickList(fulfillment_id=ff_id), asynchronous=False)
    current_domain.process(
        RecordPacking(fulfillment_id=ff_id, packed_by="Bob", packages=json.dumps([{"weight": 1.5}])),
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
    return ff_id


class TestRecordHandoff:
    def test_handoff_transitions_to_shipped(self):
        ff_id = _create_ready_to_ship()
        current_domain.process(
            RecordHandoff(fulfillment_id=ff_id, tracking_number="TRACK-001"),
            asynchronous=False,
        )
        ff = current_domain.repository_for(Fulfillment).get(ff_id)
        assert ff.status == FulfillmentStatus.SHIPPED.value

    def test_handoff_sets_tracking_number(self):
        ff_id = _create_ready_to_ship()
        current_domain.process(
            RecordHandoff(fulfillment_id=ff_id, tracking_number="TRACK-123"),
            asynchronous=False,
        )
        ff = current_domain.repository_for(Fulfillment).get(ff_id)
        assert ff.shipment.tracking_number == "TRACK-123"

    def test_handoff_preserves_carrier_info(self):
        ff_id = _create_ready_to_ship()
        current_domain.process(
            RecordHandoff(fulfillment_id=ff_id, tracking_number="TRACK-001"),
            asynchronous=False,
        )
        ff = current_domain.repository_for(Fulfillment).get(ff_id)
        assert ff.shipment.carrier == "FakeCarrier"

    def test_handoff_with_estimated_delivery(self):
        ff_id = _create_ready_to_ship()
        est = datetime.now(UTC) + timedelta(days=3)
        current_domain.process(
            RecordHandoff(fulfillment_id=ff_id, tracking_number="TRACK-001", estimated_delivery=est),
            asynchronous=False,
        )
        ff = current_domain.repository_for(Fulfillment).get(ff_id)
        assert ff.shipment.estimated_delivery is not None

    def test_handoff_fails_from_pending(self):
        items = json.dumps([{"order_item_id": "oi-1", "product_id": "prod-1", "sku": "SKU-001", "quantity": 1}])
        ff_id = current_domain.process(
            CreateFulfillment(order_id="ord-001", customer_id="cust-001", items=items),
            asynchronous=False,
        )
        with pytest.raises(ValidationError):
            current_domain.process(
                RecordHandoff(fulfillment_id=ff_id, tracking_number="TRACK-001"),
                asynchronous=False,
            )
