"""Tests for Fulfillment state machine — valid and invalid transitions."""

import pytest
from fulfillment.fulfillment.fulfillment import (
    Fulfillment,
    FulfillmentStatus,
)
from protean.exceptions import ValidationError


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


def _advance_to_picking(ff):
    ff.assign_picker("Picker-1")
    return ff


def _advance_to_packing(ff):
    _advance_to_picking(ff)
    for item in ff.items:
        ff.record_item_picked(str(item.id), "A-1-1")
    ff.complete_pick_list()
    return ff


def _advance_to_ready_to_ship(ff):
    _advance_to_packing(ff)
    ff.record_packing("Packer-1", [{"weight": 1.0}])
    ff.generate_shipping_label("https://label.pdf", "FedEx", "Standard")
    return ff


def _advance_to_shipped(ff):
    _advance_to_ready_to_ship(ff)
    ff.record_handoff("TRACK-001")
    return ff


def _advance_to_in_transit(ff):
    _advance_to_shipped(ff)
    ff.add_tracking_event("in_transit", "New York")
    return ff


class TestValidTransitions:
    def test_pending_to_picking(self):
        ff = _make_fulfillment()
        ff.assign_picker("Picker-1")
        assert ff.status == FulfillmentStatus.PICKING.value

    def test_picking_to_packing(self):
        ff = _make_fulfillment()
        _advance_to_packing(ff)
        assert ff.status == FulfillmentStatus.PACKING.value

    def test_packing_to_ready_to_ship(self):
        ff = _make_fulfillment()
        _advance_to_ready_to_ship(ff)
        assert ff.status == FulfillmentStatus.READY_TO_SHIP.value

    def test_ready_to_ship_to_shipped(self):
        ff = _make_fulfillment()
        _advance_to_shipped(ff)
        assert ff.status == FulfillmentStatus.SHIPPED.value

    def test_shipped_to_in_transit(self):
        ff = _make_fulfillment()
        _advance_to_in_transit(ff)
        assert ff.status == FulfillmentStatus.IN_TRANSIT.value

    def test_in_transit_to_delivered(self):
        ff = _make_fulfillment()
        _advance_to_in_transit(ff)
        ff.record_delivery()
        assert ff.status == FulfillmentStatus.DELIVERED.value

    def test_in_transit_to_exception(self):
        ff = _make_fulfillment()
        _advance_to_in_transit(ff)
        ff.record_exception("Address not found")
        assert ff.status == FulfillmentStatus.EXCEPTION.value

    def test_exception_to_in_transit(self):
        ff = _make_fulfillment()
        _advance_to_in_transit(ff)
        ff.record_exception("Temporary issue")
        ff.add_tracking_event("back_on_route", "Chicago")
        assert ff.status == FulfillmentStatus.IN_TRANSIT.value

    def test_exception_to_delivered(self):
        ff = _make_fulfillment()
        _advance_to_in_transit(ff)
        ff.record_exception("Delay")
        ff.record_delivery()
        assert ff.status == FulfillmentStatus.DELIVERED.value


class TestCancellation:
    def test_cancel_from_pending(self):
        ff = _make_fulfillment()
        ff.cancel("Customer requested")
        assert ff.status == FulfillmentStatus.CANCELLED.value
        assert ff.cancellation_reason == "Customer requested"

    def test_cancel_from_picking(self):
        ff = _make_fulfillment()
        _advance_to_picking(ff)
        ff.cancel("Out of stock")
        assert ff.status == FulfillmentStatus.CANCELLED.value

    def test_cancel_from_packing(self):
        ff = _make_fulfillment()
        _advance_to_packing(ff)
        ff.cancel("Order cancelled")
        assert ff.status == FulfillmentStatus.CANCELLED.value

    def test_cancel_from_ready_to_ship(self):
        ff = _make_fulfillment()
        _advance_to_ready_to_ship(ff)
        ff.cancel("Last minute cancellation")
        assert ff.status == FulfillmentStatus.CANCELLED.value

    def test_cannot_cancel_after_shipped(self):
        ff = _make_fulfillment()
        _advance_to_shipped(ff)
        with pytest.raises(ValidationError) as exc:
            ff.cancel("Too late")
        assert "Cannot cancel" in str(exc.value)

    def test_cannot_cancel_after_delivered(self):
        ff = _make_fulfillment()
        _advance_to_in_transit(ff)
        ff.record_delivery()
        with pytest.raises(ValidationError) as exc:
            ff.cancel("Too late")
        assert "Cannot cancel" in str(exc.value)

    def test_cannot_cancel_when_already_cancelled(self):
        ff = _make_fulfillment()
        ff.cancel("First cancellation")
        with pytest.raises(ValidationError):
            ff.cancel("Second cancellation")


class TestInvalidTransitions:
    def test_cannot_pick_from_packing(self):
        ff = _make_fulfillment()
        _advance_to_packing(ff)
        with pytest.raises(ValidationError):
            ff.assign_picker("Another picker")

    def test_cannot_complete_pick_list_before_picking(self):
        ff = _make_fulfillment()
        with pytest.raises(ValidationError):
            ff.complete_pick_list()

    def test_cannot_pack_before_picking(self):
        ff = _make_fulfillment()
        with pytest.raises(ValidationError):
            ff.record_packing("Packer", [])

    def test_cannot_generate_label_before_packing(self):
        ff = _make_fulfillment()
        _advance_to_picking(ff)
        with pytest.raises(ValidationError):
            ff.generate_shipping_label("https://label.pdf", "FedEx", "Standard")

    def test_cannot_handoff_from_pending(self):
        ff = _make_fulfillment()
        with pytest.raises(ValidationError):
            ff.record_handoff("TRACK-001")

    def test_cannot_deliver_from_pending(self):
        ff = _make_fulfillment()
        with pytest.raises(ValidationError):
            ff.record_delivery()

    def test_cannot_add_tracking_before_shipment(self):
        ff = _make_fulfillment()
        with pytest.raises(ValidationError):
            ff.add_tracking_event("in_transit", "NYC")

    def test_cannot_record_exception_from_shipped(self):
        ff = _make_fulfillment()
        _advance_to_shipped(ff)
        # Must go through IN_TRANSIT first
        with pytest.raises(ValidationError):
            ff.record_exception("Issue")
