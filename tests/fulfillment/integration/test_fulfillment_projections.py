"""Integration tests for fulfillment projections."""

import json

from fulfillment.fulfillment.cancellation import CancelFulfillment
from fulfillment.fulfillment.creation import CreateFulfillment
from fulfillment.fulfillment.delivery import RecordDeliveryConfirmation, RecordDeliveryException
from fulfillment.fulfillment.fulfillment import Fulfillment
from fulfillment.fulfillment.packing import GenerateShippingLabel, RecordPacking
from fulfillment.fulfillment.picking import AssignPicker, CompletePickList, RecordItemPicked
from fulfillment.fulfillment.shipping import RecordHandoff
from fulfillment.fulfillment.tracking import UpdateTrackingEvent
from fulfillment.projections.fulfillment_status import FulfillmentStatusView
from fulfillment.projections.shipment_tracking import ShipmentTrackingView
from fulfillment.projections.warehouse_queue import WarehouseQueueView
from protean import current_domain


def _single_item_json():
    return json.dumps([{"order_item_id": "oi-1", "product_id": "prod-1", "sku": "SKU-001", "quantity": 1}])


def _create_fulfillment():
    return current_domain.process(
        CreateFulfillment(order_id="ord-proj-001", customer_id="cust-proj-001", items=_single_item_json()),
        asynchronous=False,
    )


def _walk_to_shipped(ff_id):
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
        RecordHandoff(fulfillment_id=ff_id, tracking_number="TRACK-PROJ-001"),
        asynchronous=False,
    )


class TestFulfillmentStatusProjection:
    def test_projection_created_on_fulfillment_created(self):
        ff_id = _create_fulfillment()
        view = current_domain.repository_for(FulfillmentStatusView).get(ff_id)
        assert view.status == "Pending"
        assert str(view.order_id) == "ord-proj-001"
        assert view.item_count == 1

    def test_projection_updated_on_picker_assigned(self):
        ff_id = _create_fulfillment()
        current_domain.process(AssignPicker(fulfillment_id=ff_id, picker_name="Alice"), asynchronous=False)
        view = current_domain.repository_for(FulfillmentStatusView).get(ff_id)
        assert view.status == "Picking"
        assert view.assigned_to == "Alice"

    def test_projection_updated_on_picking_completed(self):
        ff_id = _create_fulfillment()
        current_domain.process(AssignPicker(fulfillment_id=ff_id, picker_name="Alice"), asynchronous=False)
        ff = current_domain.repository_for(Fulfillment).get(ff_id)
        current_domain.process(
            RecordItemPicked(fulfillment_id=ff_id, item_id=str(ff.items[0].id), pick_location="A-1"),
            asynchronous=False,
        )
        current_domain.process(CompletePickList(fulfillment_id=ff_id), asynchronous=False)
        view = current_domain.repository_for(FulfillmentStatusView).get(ff_id)
        assert view.status == "Packing"

    def test_projection_updated_on_label_generated(self):
        ff_id = _create_fulfillment()
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
        view = current_domain.repository_for(FulfillmentStatusView).get(ff_id)
        assert view.status == "Ready_To_Ship"
        assert view.carrier == "FakeCarrier"

    def test_projection_updated_on_shipment(self):
        ff_id = _create_fulfillment()
        _walk_to_shipped(ff_id)
        view = current_domain.repository_for(FulfillmentStatusView).get(ff_id)
        assert view.status == "Shipped"
        assert view.tracking_number == "TRACK-PROJ-001"

    def test_projection_updated_on_delivery(self):
        ff_id = _create_fulfillment()
        _walk_to_shipped(ff_id)
        current_domain.process(
            UpdateTrackingEvent(fulfillment_id=ff_id, status="in_transit", location="Hub"),
            asynchronous=False,
        )
        current_domain.process(RecordDeliveryConfirmation(fulfillment_id=ff_id), asynchronous=False)
        view = current_domain.repository_for(FulfillmentStatusView).get(ff_id)
        assert view.status == "Delivered"

    def test_projection_updated_on_exception(self):
        ff_id = _create_fulfillment()
        _walk_to_shipped(ff_id)
        current_domain.process(
            UpdateTrackingEvent(fulfillment_id=ff_id, status="in_transit", location="Hub"),
            asynchronous=False,
        )
        current_domain.process(
            RecordDeliveryException(fulfillment_id=ff_id, reason="Address not found", location="Dest"),
            asynchronous=False,
        )
        view = current_domain.repository_for(FulfillmentStatusView).get(ff_id)
        assert view.status == "Exception"

    def test_projection_updated_on_cancellation(self):
        ff_id = _create_fulfillment()
        current_domain.process(
            CancelFulfillment(fulfillment_id=ff_id, reason="Customer cancelled"),
            asynchronous=False,
        )
        view = current_domain.repository_for(FulfillmentStatusView).get(ff_id)
        assert view.status == "Cancelled"


class TestWarehouseQueueProjection:
    def test_queue_entry_created(self):
        ff_id = _create_fulfillment()
        view = current_domain.repository_for(WarehouseQueueView).get(ff_id)
        assert view.status == "Pending"
        assert view.item_count == 1

    def test_queue_updated_on_picker_assigned(self):
        ff_id = _create_fulfillment()
        current_domain.process(AssignPicker(fulfillment_id=ff_id, picker_name="Alice"), asynchronous=False)
        view = current_domain.repository_for(WarehouseQueueView).get(ff_id)
        assert view.status == "Picking"
        assert view.assigned_to == "Alice"

    def test_queue_updated_on_shipment(self):
        ff_id = _create_fulfillment()
        _walk_to_shipped(ff_id)
        view = current_domain.repository_for(WarehouseQueueView).get(ff_id)
        assert view.status == "Shipped"

    def test_queue_updated_on_cancellation(self):
        ff_id = _create_fulfillment()
        current_domain.process(
            CancelFulfillment(fulfillment_id=ff_id, reason="Customer cancelled"),
            asynchronous=False,
        )
        view = current_domain.repository_for(WarehouseQueueView).get(ff_id)
        assert view.status == "Cancelled"


class TestShipmentTrackingProjection:
    def test_tracking_view_created_on_handoff(self):
        ff_id = _create_fulfillment()
        _walk_to_shipped(ff_id)
        view = current_domain.repository_for(ShipmentTrackingView).get(ff_id)
        assert view.current_status == "Shipped"
        assert view.carrier == "FakeCarrier"
        assert view.tracking_number == "TRACK-PROJ-001"

    def test_tracking_view_updated_on_tracking_event(self):
        ff_id = _create_fulfillment()
        _walk_to_shipped(ff_id)
        current_domain.process(
            UpdateTrackingEvent(
                fulfillment_id=ff_id,
                status="in_transit",
                location="Distribution Center, NY",
                description="Package in transit",
            ),
            asynchronous=False,
        )
        view = current_domain.repository_for(ShipmentTrackingView).get(ff_id)
        assert view.current_status == "in_transit"
        assert view.current_location == "Distribution Center, NY"
        events = json.loads(view.events_json)
        assert len(events) == 1
        assert events[0]["status"] == "in_transit"

    def test_tracking_view_updated_on_delivery(self):
        ff_id = _create_fulfillment()
        _walk_to_shipped(ff_id)
        current_domain.process(
            UpdateTrackingEvent(fulfillment_id=ff_id, status="in_transit", location="Hub"),
            asynchronous=False,
        )
        current_domain.process(RecordDeliveryConfirmation(fulfillment_id=ff_id), asynchronous=False)
        view = current_domain.repository_for(ShipmentTrackingView).get(ff_id)
        assert view.current_status == "Delivered"
        assert view.delivered_at is not None
        events = json.loads(view.events_json)
        assert len(events) == 2  # tracking event + delivery

    def test_tracking_view_updated_on_exception(self):
        ff_id = _create_fulfillment()
        _walk_to_shipped(ff_id)
        current_domain.process(
            UpdateTrackingEvent(fulfillment_id=ff_id, status="in_transit", location="Hub"),
            asynchronous=False,
        )
        current_domain.process(
            RecordDeliveryException(fulfillment_id=ff_id, reason="No one home", location="Front door"),
            asynchronous=False,
        )
        view = current_domain.repository_for(ShipmentTrackingView).get(ff_id)
        assert view.current_status == "Exception"
        events = json.loads(view.events_json)
        assert len(events) == 2
        assert events[-1]["status"] == "Exception"
