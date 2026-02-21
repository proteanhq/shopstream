"""Integration tests for DeliveryPerformanceView projection.

Covers:
- New record creation on first ShipmentHandedOff (lines 47-48 exception path)
- Existing record update on subsequent ShipmentHandedOff
- DeliveryConfirmed updates delivered_count
- DeliveryException updates exception_count
"""

import json

from fulfillment.fulfillment.creation import CreateFulfillment
from fulfillment.fulfillment.delivery import RecordDeliveryConfirmation, RecordDeliveryException
from fulfillment.fulfillment.fulfillment import Fulfillment
from fulfillment.fulfillment.packing import GenerateShippingLabel, RecordPacking
from fulfillment.fulfillment.picking import AssignPicker, CompletePickList, RecordItemPicked
from fulfillment.fulfillment.shipping import RecordHandoff
from fulfillment.fulfillment.tracking import UpdateTrackingEvent
from fulfillment.projections.delivery_performance import DeliveryPerformanceView
from protean import current_domain


def _single_item_json():
    return json.dumps([{"order_item_id": "oi-1", "product_id": "prod-1", "sku": "SKU-001", "quantity": 1}])


def _create_fulfillment(order_id="ord-perf-001"):
    return current_domain.process(
        CreateFulfillment(order_id=order_id, customer_id="cust-perf-001", items=_single_item_json()),
        asynchronous=False,
    )


def _walk_to_shipped(ff_id, tracking_number="TRACK-PERF-001"):
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
        RecordHandoff(fulfillment_id=ff_id, tracking_number=tracking_number),
        asynchronous=False,
    )


def _walk_to_in_transit(ff_id, tracking_number="TRACK-PERF-001"):
    _walk_to_shipped(ff_id, tracking_number=tracking_number)
    current_domain.process(
        UpdateTrackingEvent(fulfillment_id=ff_id, status="in_transit", location="Hub"),
        asynchronous=False,
    )


class TestDeliveryPerformanceProjection:
    def test_new_record_created_on_first_handoff(self):
        """First handoff for a carrier+date creates a new DeliveryPerformanceView record."""
        ff_id = _create_fulfillment(order_id="ord-perf-new")
        _walk_to_shipped(ff_id)

        # Query for the projection
        results = current_domain.repository_for(DeliveryPerformanceView)._dao.query.all()
        assert results and len(results.items) > 0

        view = results.first
        assert view.carrier == "FakeCarrier"
        assert view.total_shipments >= 1
        assert view.delivered_count == 0
        assert view.exception_count == 0

    def test_existing_record_incremented_on_second_handoff(self):
        """Second handoff for same carrier+date increments total_shipments."""
        ff_id1 = _create_fulfillment(order_id="ord-perf-inc1")
        _walk_to_shipped(ff_id1, tracking_number="TRACK-INC-001")

        ff_id2 = _create_fulfillment(order_id="ord-perf-inc2")
        _walk_to_shipped(ff_id2, tracking_number="TRACK-INC-002")

        results = current_domain.repository_for(DeliveryPerformanceView)._dao.query.all()
        assert results and len(results.items) > 0
        view = results.first
        assert view.total_shipments >= 2

    def test_delivery_confirmed_updates_count(self):
        """DeliveryConfirmed event should increment delivered_count."""
        ff_id = _create_fulfillment(order_id="ord-perf-del")
        _walk_to_in_transit(ff_id)

        # Record delivery
        current_domain.process(RecordDeliveryConfirmation(fulfillment_id=ff_id), asynchronous=False)

        results = current_domain.repository_for(DeliveryPerformanceView)._dao.query.all()
        assert results and len(results.items) > 0
        view = results.first
        assert view.delivered_count >= 1

    def test_delivery_exception_updates_count(self):
        """DeliveryException event should increment exception_count."""
        ff_id = _create_fulfillment(order_id="ord-perf-exc")
        _walk_to_in_transit(ff_id)

        # Record exception
        current_domain.process(
            RecordDeliveryException(fulfillment_id=ff_id, reason="Nobody home", location="Front door"),
            asynchronous=False,
        )

        results = current_domain.repository_for(DeliveryPerformanceView)._dao.query.all()
        assert results and len(results.items) > 0
        view = results.first
        assert view.exception_count >= 1
