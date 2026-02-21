"""Tests for Fulfillment business rule invariants."""

import pytest
from fulfillment.fulfillment.fulfillment import Fulfillment, FulfillmentItemStatus
from protean.exceptions import ValidationError


def _make_items(count=2):
    return [
        {"order_item_id": f"oi-{i}", "product_id": f"prod-{i}", "sku": f"SKU-{i:03d}", "quantity": 1}
        for i in range(1, count + 1)
    ]


def _make_fulfillment(item_count=2):
    return Fulfillment.create(
        order_id="ord-001",
        customer_id="cust-001",
        items_data=_make_items(item_count),
    )


class TestPickingInvariants:
    def test_cannot_complete_pick_list_with_unpicked_items(self):
        ff = _make_fulfillment(item_count=2)
        ff.assign_picker("Picker-1")
        # Only pick first item
        ff.record_item_picked(str(ff.items[0].id), "A-1-1")
        with pytest.raises(ValidationError) as exc:
            ff.complete_pick_list()
        assert "not been picked" in str(exc.value)

    def test_can_complete_pick_list_when_all_items_picked(self):
        ff = _make_fulfillment(item_count=2)
        ff.assign_picker("Picker-1")
        for item in ff.items:
            ff.record_item_picked(str(item.id), "A-1-1")
        ff.complete_pick_list()  # Should not raise

    def test_cannot_pick_already_picked_item(self):
        ff = _make_fulfillment()
        ff.assign_picker("Picker-1")
        item_id = str(ff.items[0].id)
        ff.record_item_picked(item_id, "A-1-1")
        with pytest.raises(ValidationError) as exc:
            ff.record_item_picked(item_id, "A-1-1")
        assert "already been picked" in str(exc.value)

    def test_cannot_pick_nonexistent_item(self):
        ff = _make_fulfillment()
        ff.assign_picker("Picker-1")
        with pytest.raises(ValidationError) as exc:
            ff.record_item_picked("nonexistent-id", "A-1-1")
        assert "not found" in str(exc.value)

    def test_items_not_pickable_outside_picking_phase(self):
        ff = _make_fulfillment()
        with pytest.raises(ValidationError) as exc:
            ff.record_item_picked(str(ff.items[0].id), "A-1-1")
        assert "PICKING" in str(exc.value)


class TestPackingInvariants:
    def test_cannot_generate_label_without_packing(self):
        ff = _make_fulfillment(item_count=1)
        ff.assign_picker("Picker-1")
        ff.record_item_picked(str(ff.items[0].id), "A-1-1")
        ff.complete_pick_list()
        # Try to generate label without packing first
        with pytest.raises(ValidationError) as exc:
            ff.generate_shipping_label("https://label.pdf", "FedEx", "Standard")
        assert "packed" in str(exc.value)

    def test_packing_marks_all_items_as_packed(self):
        ff = _make_fulfillment(item_count=2)
        ff.assign_picker("Picker-1")
        for item in ff.items:
            ff.record_item_picked(str(item.id), "A-1-1")
        ff.complete_pick_list()
        ff.record_packing("Packer-1", [{"weight": 2.0}])
        for item in ff.items:
            assert item.status == FulfillmentItemStatus.PACKED.value


class TestTrackingInvariants:
    def test_cannot_add_tracking_before_shipment(self):
        ff = _make_fulfillment()
        with pytest.raises(ValidationError):
            ff.add_tracking_event("in_transit", "NYC")

    def test_can_add_tracking_after_shipment(self):
        ff = _make_fulfillment(item_count=1)
        ff.assign_picker("P")
        ff.record_item_picked(str(ff.items[0].id), "A")
        ff.complete_pick_list()
        ff.record_packing("P", [{"weight": 1.0}])
        ff.generate_shipping_label("url", "FedEx", "Standard")
        ff.record_handoff("TRACK-1")
        ff.add_tracking_event("picked_up", "Warehouse")  # Should not raise

    def test_tracking_event_creates_tracking_entry(self):
        ff = _make_fulfillment(item_count=1)
        ff.assign_picker("P")
        ff.record_item_picked(str(ff.items[0].id), "A")
        ff.complete_pick_list()
        ff.record_packing("P", [{"weight": 1.0}])
        ff.generate_shipping_label("url", "FedEx", "Standard")
        ff.record_handoff("TRACK-1")
        ff.add_tracking_event("picked_up", "Warehouse")
        assert len(ff.tracking_events) == 1
        assert ff.tracking_events[0].status == "picked_up"


class TestDeliveryInvariants:
    def test_delivery_sets_actual_delivery_on_shipment(self):
        ff = _make_fulfillment(item_count=1)
        ff.assign_picker("P")
        ff.record_item_picked(str(ff.items[0].id), "A")
        ff.complete_pick_list()
        ff.record_packing("P", [{"weight": 1.0}])
        ff.generate_shipping_label("url", "FedEx", "Standard")
        ff.record_handoff("TRACK-1")
        ff.add_tracking_event("in_transit", "NYC")
        ff.record_delivery()
        assert ff.shipment.actual_delivery is not None

    def test_exception_adds_tracking_event(self):
        ff = _make_fulfillment(item_count=1)
        ff.assign_picker("P")
        ff.record_item_picked(str(ff.items[0].id), "A")
        ff.complete_pick_list()
        ff.record_packing("P", [{"weight": 1.0}])
        ff.generate_shipping_label("url", "FedEx", "Standard")
        ff.record_handoff("TRACK-1")
        ff.add_tracking_event("in_transit", "NYC")
        ff.record_exception("Access denied", "Front door")
        assert len(ff.tracking_events) == 2
        assert ff.tracking_events[-1].status == "EXCEPTION"
