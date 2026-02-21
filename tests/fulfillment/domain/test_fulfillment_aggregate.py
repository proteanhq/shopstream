"""Tests for Fulfillment aggregate creation and structure."""

from fulfillment.fulfillment.events import FulfillmentCreated
from fulfillment.fulfillment.fulfillment import (
    Fulfillment,
    FulfillmentItem,
    FulfillmentItemStatus,
    FulfillmentStatus,
    PackageDimensions,
    PackingInfo,
    PickList,
    ShipmentInfo,
)


def _make_items():
    return [
        {"order_item_id": "oi-1", "product_id": "prod-1", "sku": "SKU-001", "quantity": 2},
        {"order_item_id": "oi-2", "product_id": "prod-2", "sku": "SKU-002", "quantity": 1},
    ]


def _make_fulfillment(**overrides):
    defaults = {
        "order_id": "ord-001",
        "customer_id": "cust-001",
        "items_data": _make_items(),
        "warehouse_id": "wh-001",
    }
    defaults.update(overrides)
    return Fulfillment.create(**defaults)


class TestFulfillmentCreation:
    def test_create_sets_order_id(self):
        ff = _make_fulfillment()
        assert str(ff.order_id) == "ord-001"

    def test_create_sets_customer_id(self):
        ff = _make_fulfillment()
        assert str(ff.customer_id) == "cust-001"

    def test_create_sets_warehouse_id(self):
        ff = _make_fulfillment()
        assert str(ff.warehouse_id) == "wh-001"

    def test_create_sets_status_to_pending(self):
        ff = _make_fulfillment()
        assert ff.status == FulfillmentStatus.PENDING.value

    def test_create_generates_id(self):
        ff = _make_fulfillment()
        assert ff.id is not None

    def test_create_sets_timestamps(self):
        ff = _make_fulfillment()
        assert ff.created_at is not None
        assert ff.updated_at is not None

    def test_create_adds_items(self):
        ff = _make_fulfillment()
        assert len(ff.items) == 2

    def test_create_items_have_pending_status(self):
        ff = _make_fulfillment()
        for item in ff.items:
            assert item.status == FulfillmentItemStatus.PENDING.value

    def test_create_items_have_correct_sku(self):
        ff = _make_fulfillment()
        skus = {item.sku for item in ff.items}
        assert skus == {"SKU-001", "SKU-002"}

    def test_create_with_no_warehouse_id(self):
        ff = _make_fulfillment(warehouse_id=None)
        assert ff.warehouse_id is None or ff.warehouse_id == ""

    def test_create_raises_fulfillment_created_event(self):
        ff = _make_fulfillment()
        assert len(ff._events) == 1
        event = ff._events[0]
        assert isinstance(event, FulfillmentCreated)

    def test_event_contains_fulfillment_id(self):
        ff = _make_fulfillment()
        event = ff._events[0]
        assert event.fulfillment_id == str(ff.id)

    def test_event_contains_order_id(self):
        ff = _make_fulfillment()
        event = ff._events[0]
        assert event.order_id == "ord-001"

    def test_event_contains_item_count(self):
        ff = _make_fulfillment()
        event = ff._events[0]
        assert event.item_count == 2


class TestValueObjects:
    def test_pick_list_construction(self):
        pl = PickList(assigned_to="John")
        assert pl.assigned_to == "John"

    def test_packing_info_construction(self):
        pi = PackingInfo(packed_by="Jane", shipping_label_url="https://example.com/label.pdf")
        assert pi.packed_by == "Jane"
        assert pi.shipping_label_url == "https://example.com/label.pdf"

    def test_shipment_info_construction(self):
        si = ShipmentInfo(carrier="FedEx", service_level="Standard", tracking_number="TRACK-123")
        assert si.carrier == "FedEx"
        assert si.tracking_number == "TRACK-123"

    def test_package_dimensions_construction(self):
        pd = PackageDimensions(weight=2.5, length=10, width=8, height=6)
        assert pd.weight == 2.5
        assert pd.length == 10


class TestFulfillmentItem:
    def test_item_construction(self):
        item = FulfillmentItem(
            order_item_id="oi-1",
            product_id="prod-1",
            sku="SKU-001",
            quantity=3,
        )
        assert item.sku == "SKU-001"
        assert item.quantity == 3
        assert item.status == FulfillmentItemStatus.PENDING.value

    def test_item_default_status(self):
        item = FulfillmentItem(
            order_item_id="oi-1",
            product_id="prod-1",
            sku="SKU-001",
            quantity=1,
        )
        assert item.status == FulfillmentItemStatus.PENDING.value
