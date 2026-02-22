"""Shared BDD fixtures and step definitions for the Fulfillment domain."""

import pytest
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
from protean.exceptions import ValidationError
from pytest_bdd import given, parsers, then

_FULFILLMENT_EVENT_CLASSES = {
    "FulfillmentCreated": FulfillmentCreated,
    "PickerAssigned": PickerAssigned,
    "ItemPicked": ItemPicked,
    "PickingCompleted": PickingCompleted,
    "PackingCompleted": PackingCompleted,
    "ShippingLabelGenerated": ShippingLabelGenerated,
    "ShipmentHandedOff": ShipmentHandedOff,
    "TrackingEventReceived": TrackingEventReceived,
    "DeliveryConfirmed": DeliveryConfirmed,
    "DeliveryException": DeliveryException,
    "FulfillmentCancelled": FulfillmentCancelled,
}

_DEFAULT_ITEMS = [
    {
        "order_item_id": "oi-1",
        "product_id": "prod-kb",
        "sku": "KB-MECH-001",
        "quantity": 1,
    },
    {
        "order_item_id": "oi-2",
        "product_id": "prod-mp",
        "sku": "MP-XL-BLK",
        "quantity": 1,
    },
]


@pytest.fixture()
def error():
    """Container for captured validation errors."""
    return {"exc": None}


# ---------------------------------------------------------------------------
# Given steps
# ---------------------------------------------------------------------------
@given("a pending fulfillment", target_fixture="ff")
def pending_fulfillment():
    ff = Fulfillment.create(
        order_id="ord-bdd-001",
        customer_id="cust-bdd",
        items_data=_DEFAULT_ITEMS,
    )
    ff._events.clear()
    return ff


@given("a fulfillment in picking state", target_fixture="ff")
def picking_fulfillment():
    ff = Fulfillment.create(
        order_id="ord-bdd-002",
        customer_id="cust-bdd",
        items_data=_DEFAULT_ITEMS,
    )
    ff.assign_picker("Alice")
    ff._events.clear()
    return ff


@given("a fulfillment with all items picked", target_fixture="ff")
def all_items_picked_fulfillment():
    ff = Fulfillment.create(
        order_id="ord-bdd-003",
        customer_id="cust-bdd",
        items_data=_DEFAULT_ITEMS,
    )
    ff.assign_picker("Alice")
    for item in ff.items:
        ff.record_item_picked(str(item.id), "A-12")
    ff.complete_pick_list()
    ff._events.clear()
    return ff


@given("a fulfillment in packing state", target_fixture="ff")
def packing_fulfillment():
    ff = Fulfillment.create(
        order_id="ord-bdd-004",
        customer_id="cust-bdd",
        items_data=_DEFAULT_ITEMS,
    )
    ff.assign_picker("Alice")
    for item in ff.items:
        ff.record_item_picked(str(item.id), "A-12")
    ff.complete_pick_list()
    ff._events.clear()
    return ff


@given("a packed fulfillment with shipping label", target_fixture="ff")
def ready_to_ship_fulfillment():
    ff = Fulfillment.create(
        order_id="ord-bdd-005",
        customer_id="cust-bdd",
        items_data=_DEFAULT_ITEMS,
    )
    ff.assign_picker("Alice")
    for item in ff.items:
        ff.record_item_picked(str(item.id), "A-12")
    ff.complete_pick_list()
    ff.record_packing("Bob", [{"weight": 1.5}])
    ff.generate_shipping_label(
        "https://carrier.example.com/labels/lbl-123",
        "FedEx",
        "Standard",
    )
    ff._events.clear()
    return ff


@given("a shipped fulfillment", target_fixture="ff")
def shipped_fulfillment():
    ff = Fulfillment.create(
        order_id="ord-bdd-006",
        customer_id="cust-bdd",
        items_data=_DEFAULT_ITEMS,
    )
    ff.assign_picker("Alice")
    for item in ff.items:
        ff.record_item_picked(str(item.id), "A-12")
    ff.complete_pick_list()
    ff.record_packing("Bob", [{"weight": 1.5}])
    ff.generate_shipping_label(
        "https://carrier.example.com/labels/lbl-123",
        "FedEx",
        "Standard",
    )
    ff.record_handoff("FDX-789456123")
    ff._events.clear()
    return ff


@given("an in-transit fulfillment", target_fixture="ff")
def in_transit_fulfillment():
    ff = Fulfillment.create(
        order_id="ord-bdd-007",
        customer_id="cust-bdd",
        items_data=_DEFAULT_ITEMS,
    )
    ff.assign_picker("Alice")
    for item in ff.items:
        ff.record_item_picked(str(item.id), "A-12")
    ff.complete_pick_list()
    ff.record_packing("Bob", [{"weight": 1.5}])
    ff.generate_shipping_label(
        "https://carrier.example.com/labels/lbl-123",
        "FedEx",
        "Standard",
    )
    ff.record_handoff("FDX-789456123")
    ff.add_tracking_event("Departed", "Chicago, IL", "Package departed origin")
    ff._events.clear()
    return ff


@given("a fulfillment with a delivery exception", target_fixture="ff")
def exception_fulfillment():
    ff = Fulfillment.create(
        order_id="ord-bdd-008",
        customer_id="cust-bdd",
        items_data=_DEFAULT_ITEMS,
    )
    ff.assign_picker("Alice")
    for item in ff.items:
        ff.record_item_picked(str(item.id), "A-12")
    ff.complete_pick_list()
    ff.record_packing("Bob", [{"weight": 1.5}])
    ff.generate_shipping_label(
        "https://carrier.example.com/labels/lbl-123",
        "FedEx",
        "Standard",
    )
    ff.record_handoff("FDX-789456123")
    ff.add_tracking_event("Departed", "Chicago, IL", "Package departed origin")
    ff.record_exception("Customer not available", "Columbus, OH")
    ff._events.clear()
    return ff


# ---------------------------------------------------------------------------
# Then steps
# ---------------------------------------------------------------------------
@then(parsers.cfparse('the fulfillment status is "{status}"'))
def fulfillment_status_is(ff, status):
    assert ff.status == status


@then("the fulfillment action fails with a validation error")
def fulfillment_action_fails(error):
    assert error["exc"] is not None, "Expected a validation error but none was raised"
    assert isinstance(error["exc"], ValidationError)


@then(parsers.cfparse("a {event_type} event is raised"))
def fulfillment_event_raised(ff, event_type):
    event_cls = _FULFILLMENT_EVENT_CLASSES[event_type]
    assert any(
        isinstance(e, event_cls) for e in ff._events
    ), f"No {event_type} event found. Events: {[type(e).__name__ for e in ff._events]}"


@then(parsers.cfparse("the fulfillment has {count:d} tracking events"))
def fulfillment_has_n_tracking_events(ff, count):
    assert len(ff.tracking_events) == count


@then(parsers.cfparse('the fulfillment has a pick list assigned to "{picker_name}"'))
def fulfillment_has_pick_list(ff, picker_name):
    assert ff.pick_list is not None
    assert ff.pick_list.assigned_to == picker_name


@then("all items are in Picked status")
def all_items_picked(ff):
    for item in ff.items:
        assert item.status == "Picked"


@then("all items are in Packed status")
def all_items_packed(ff):
    for item in ff.items:
        assert item.status == "Packed"


@then(parsers.cfparse('the shipment carrier is "{carrier}"'))
def shipment_carrier_is(ff, carrier):
    assert ff.shipment is not None
    assert ff.shipment.carrier == carrier


@then(parsers.cfparse('the tracking number is "{tracking_number}"'))
def tracking_number_is(ff, tracking_number):
    assert ff.shipment is not None
    assert ff.shipment.tracking_number == tracking_number


@then(parsers.cfparse('the cancellation reason is "{reason}"'))
def cancellation_reason_is(ff, reason):
    assert ff.cancellation_reason == reason
