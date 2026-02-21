"""Tests for Fulfillment domain events — each method raises correct event."""

from fulfillment.fulfillment.events import (
    DeliveryConfirmed,
    DeliveryException,
    FulfillmentCancelled,
    FulfillmentCreated,
    ItemPicked,
    PackingCompleted,
    PickerAssigned,
    PickingCompleted,
    ShipmentHandedOff,
    ShippingLabelGenerated,
    TrackingEventReceived,
)
from fulfillment.fulfillment.fulfillment import Fulfillment


def _make_items():
    return [
        {"order_item_id": "oi-1", "product_id": "prod-1", "sku": "SKU-001", "quantity": 1},
    ]


def _make_fulfillment():
    return Fulfillment.create(
        order_id="ord-001",
        customer_id="cust-001",
        items_data=_make_items(),
    )


def _to_shipped(ff):
    ff.assign_picker("Picker-1")
    for item in ff.items:
        ff.record_item_picked(str(item.id), "A-1-1")
    ff.complete_pick_list()
    ff.record_packing("Packer-1", [{"weight": 1.0}])
    ff.generate_shipping_label("https://label.pdf", "FedEx", "Standard")
    ff.record_handoff("TRACK-001")
    return ff


class TestFulfillmentCreatedEvent:
    def test_raises_event(self):
        ff = _make_fulfillment()
        assert len(ff._events) == 1
        assert isinstance(ff._events[0], FulfillmentCreated)

    def test_event_has_order_id(self):
        ff = _make_fulfillment()
        assert ff._events[0].order_id == "ord-001"

    def test_event_has_item_count(self):
        ff = _make_fulfillment()
        assert ff._events[0].item_count == 1


class TestPickerAssignedEvent:
    def test_assign_picker_raises_event(self):
        ff = _make_fulfillment()
        ff.assign_picker("John")
        events = [e for e in ff._events if isinstance(e, PickerAssigned)]
        assert len(events) == 1
        assert events[0].assigned_to == "John"


class TestItemPickedEvent:
    def test_record_item_picked_raises_event(self):
        ff = _make_fulfillment()
        ff.assign_picker("John")
        item_id = str(ff.items[0].id)
        ff.record_item_picked(item_id, "A-1-1")
        events = [e for e in ff._events if isinstance(e, ItemPicked)]
        assert len(events) == 1
        assert events[0].item_id == item_id
        assert events[0].pick_location == "A-1-1"


class TestPickingCompletedEvent:
    def test_complete_pick_list_raises_event(self):
        ff = _make_fulfillment()
        ff.assign_picker("John")
        ff.record_item_picked(str(ff.items[0].id), "A-1-1")
        ff.complete_pick_list()
        events = [e for e in ff._events if isinstance(e, PickingCompleted)]
        assert len(events) == 1


class TestPackingCompletedEvent:
    def test_record_packing_raises_event(self):
        ff = _make_fulfillment()
        ff.assign_picker("John")
        ff.record_item_picked(str(ff.items[0].id), "A-1-1")
        ff.complete_pick_list()
        ff.record_packing("Jane", [{"weight": 1.0}])
        events = [e for e in ff._events if isinstance(e, PackingCompleted)]
        assert len(events) == 1
        assert events[0].packed_by == "Jane"
        assert events[0].package_count == 1


class TestShippingLabelGeneratedEvent:
    def test_generate_label_raises_event(self):
        ff = _make_fulfillment()
        ff.assign_picker("John")
        ff.record_item_picked(str(ff.items[0].id), "A-1-1")
        ff.complete_pick_list()
        ff.record_packing("Jane", [{"weight": 1.0}])
        ff.generate_shipping_label("https://label.pdf", "FedEx", "Standard")
        events = [e for e in ff._events if isinstance(e, ShippingLabelGenerated)]
        assert len(events) == 1
        assert events[0].carrier == "FedEx"
        assert events[0].service_level == "Standard"


class TestShipmentHandedOffEvent:
    def test_record_handoff_raises_event(self):
        ff = _make_fulfillment()
        _to_shipped(ff)
        events = [e for e in ff._events if isinstance(e, ShipmentHandedOff)]
        assert len(events) == 1
        assert events[0].tracking_number == "TRACK-001"
        assert events[0].order_id == "ord-001"


class TestTrackingEventReceivedEvent:
    def test_add_tracking_event_raises_event(self):
        ff = _make_fulfillment()
        _to_shipped(ff)
        ff.add_tracking_event("in_transit", "New York", "Package in transit")
        events = [e for e in ff._events if isinstance(e, TrackingEventReceived)]
        assert len(events) == 1
        assert events[0].status == "in_transit"
        assert events[0].location == "New York"


class TestDeliveryConfirmedEvent:
    def test_record_delivery_raises_event(self):
        ff = _make_fulfillment()
        _to_shipped(ff)
        ff.add_tracking_event("in_transit", "NYC")
        ff.record_delivery()
        events = [e for e in ff._events if isinstance(e, DeliveryConfirmed)]
        assert len(events) == 1
        assert events[0].order_id == "ord-001"


class TestDeliveryExceptionEvent:
    def test_record_exception_raises_event(self):
        ff = _make_fulfillment()
        _to_shipped(ff)
        ff.add_tracking_event("in_transit", "NYC")
        ff.record_exception("Address not found", "Brooklyn")
        events = [e for e in ff._events if isinstance(e, DeliveryException)]
        assert len(events) == 1
        assert events[0].reason == "Address not found"
        assert events[0].location == "Brooklyn"


class TestFulfillmentCancelledEvent:
    def test_cancel_raises_event(self):
        ff = _make_fulfillment()
        ff.cancel("Customer requested")
        events = [e for e in ff._events if isinstance(e, FulfillmentCancelled)]
        assert len(events) == 1
        assert events[0].reason == "Customer requested"
        assert events[0].order_id == "ord-001"
