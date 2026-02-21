"""Application tests for tracking event command via domain.process()."""

import json

import pytest
from fulfillment.fulfillment.creation import CreateFulfillment
from fulfillment.fulfillment.fulfillment import Fulfillment, FulfillmentStatus
from fulfillment.fulfillment.packing import GenerateShippingLabel, RecordPacking
from fulfillment.fulfillment.picking import AssignPicker, CompletePickList, RecordItemPicked
from fulfillment.fulfillment.shipping import RecordHandoff
from fulfillment.fulfillment.tracking import UpdateTrackingEvent
from protean import current_domain
from protean.exceptions import ValidationError


def _create_shipped():
    """Create a fulfillment in SHIPPED state."""
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
    current_domain.process(
        RecordHandoff(fulfillment_id=ff_id, tracking_number="TRACK-001"),
        asynchronous=False,
    )
    return ff_id


class TestUpdateTrackingEvent:
    def test_tracking_event_transitions_to_in_transit(self):
        ff_id = _create_shipped()
        current_domain.process(
            UpdateTrackingEvent(
                fulfillment_id=ff_id,
                status="in_transit",
                location="Distribution Center, NY",
                description="Package in transit",
            ),
            asynchronous=False,
        )
        ff = current_domain.repository_for(Fulfillment).get(ff_id)
        assert ff.status == FulfillmentStatus.IN_TRANSIT.value

    def test_tracking_event_adds_to_tracking_events(self):
        ff_id = _create_shipped()
        current_domain.process(
            UpdateTrackingEvent(
                fulfillment_id=ff_id,
                status="in_transit",
                location="Hub, TX",
                description="Arrived at hub",
            ),
            asynchronous=False,
        )
        ff = current_domain.repository_for(Fulfillment).get(ff_id)
        assert len(ff.tracking_events) == 1
        assert ff.tracking_events[0].status == "in_transit"
        assert ff.tracking_events[0].location == "Hub, TX"

    def test_multiple_tracking_events(self):
        ff_id = _create_shipped()
        current_domain.process(
            UpdateTrackingEvent(fulfillment_id=ff_id, status="in_transit", location="Hub A"),
            asynchronous=False,
        )
        current_domain.process(
            UpdateTrackingEvent(fulfillment_id=ff_id, status="in_transit", location="Hub B"),
            asynchronous=False,
        )
        ff = current_domain.repository_for(Fulfillment).get(ff_id)
        assert len(ff.tracking_events) == 2

    def test_tracking_event_fails_from_pending(self):
        items = json.dumps([{"order_item_id": "oi-1", "product_id": "prod-1", "sku": "SKU-001", "quantity": 1}])
        ff_id = current_domain.process(
            CreateFulfillment(order_id="ord-001", customer_id="cust-001", items=items),
            asynchronous=False,
        )
        with pytest.raises(ValidationError):
            current_domain.process(
                UpdateTrackingEvent(fulfillment_id=ff_id, status="in_transit", location="Somewhere"),
                asynchronous=False,
            )
