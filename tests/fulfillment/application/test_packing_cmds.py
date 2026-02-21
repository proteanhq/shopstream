"""Application tests for packing commands via domain.process()."""

import json

import pytest
from fulfillment.fulfillment.creation import CreateFulfillment
from fulfillment.fulfillment.fulfillment import (
    Fulfillment,
    FulfillmentItemStatus,
    FulfillmentStatus,
)
from fulfillment.fulfillment.packing import GenerateShippingLabel, RecordPacking
from fulfillment.fulfillment.picking import AssignPicker, CompletePickList, RecordItemPicked
from protean import current_domain
from protean.exceptions import ValidationError


def _create_and_pick(item_count=1):
    """Create a fulfillment, pick all items, complete pick list → PACKING state."""
    items = [
        {"order_item_id": f"oi-{i}", "product_id": f"prod-{i}", "sku": f"SKU-{i:03d}", "quantity": 1}
        for i in range(1, item_count + 1)
    ]
    ff_id = current_domain.process(
        CreateFulfillment(order_id="ord-001", customer_id="cust-001", items=json.dumps(items)),
        asynchronous=False,
    )
    current_domain.process(AssignPicker(fulfillment_id=ff_id, picker_name="Alice"), asynchronous=False)
    ff = current_domain.repository_for(Fulfillment).get(ff_id)
    for item in ff.items:
        current_domain.process(
            RecordItemPicked(fulfillment_id=ff_id, item_id=str(item.id), pick_location="A-1-1"),
            asynchronous=False,
        )
    current_domain.process(CompletePickList(fulfillment_id=ff_id), asynchronous=False)
    return ff_id


class TestRecordPacking:
    def test_record_packing_creates_packages(self):
        ff_id = _create_and_pick()
        packages = [{"weight": 1.5}]
        current_domain.process(
            RecordPacking(fulfillment_id=ff_id, packed_by="Bob", packages=json.dumps(packages)),
            asynchronous=False,
        )
        ff = current_domain.repository_for(Fulfillment).get(ff_id)
        assert len(ff.packages) == 1

    def test_record_packing_sets_packing_info(self):
        ff_id = _create_and_pick()
        packages = [{"weight": 2.0}]
        current_domain.process(
            RecordPacking(fulfillment_id=ff_id, packed_by="Bob", packages=json.dumps(packages)),
            asynchronous=False,
        )
        ff = current_domain.repository_for(Fulfillment).get(ff_id)
        assert ff.packing_info.packed_by == "Bob"
        assert ff.packing_info.packed_at is not None

    def test_record_packing_marks_items_packed(self):
        ff_id = _create_and_pick(item_count=2)
        packages = [{"weight": 3.0}]
        current_domain.process(
            RecordPacking(fulfillment_id=ff_id, packed_by="Bob", packages=json.dumps(packages)),
            asynchronous=False,
        )
        ff = current_domain.repository_for(Fulfillment).get(ff_id)
        for item in ff.items:
            assert item.status == FulfillmentItemStatus.PACKED.value

    def test_record_packing_fails_when_not_in_packing_phase(self):
        items = json.dumps([{"order_item_id": "oi-1", "product_id": "prod-1", "sku": "SKU-001", "quantity": 1}])
        ff_id = current_domain.process(
            CreateFulfillment(order_id="ord-001", customer_id="cust-001", items=items),
            asynchronous=False,
        )
        with pytest.raises(ValidationError):
            current_domain.process(
                RecordPacking(fulfillment_id=ff_id, packed_by="Bob", packages=json.dumps([{"weight": 1.0}])),
                asynchronous=False,
            )


class TestGenerateShippingLabel:
    def test_generate_label_transitions_to_ready_to_ship(self):
        ff_id = _create_and_pick()
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
        ff = current_domain.repository_for(Fulfillment).get(ff_id)
        assert ff.status == FulfillmentStatus.READY_TO_SHIP.value

    def test_generate_label_sets_shipment_info(self):
        ff_id = _create_and_pick()
        current_domain.process(
            RecordPacking(fulfillment_id=ff_id, packed_by="Bob", packages=json.dumps([{"weight": 1.0}])),
            asynchronous=False,
        )
        current_domain.process(
            GenerateShippingLabel(
                fulfillment_id=ff_id,
                label_url="https://labels.example.com/abc.pdf",
                carrier="FakeCarrier",
                service_level="Express",
            ),
            asynchronous=False,
        )
        ff = current_domain.repository_for(Fulfillment).get(ff_id)
        assert ff.shipment.carrier == "FakeCarrier"
        assert ff.shipment.service_level == "Express"
        assert ff.packing_info.shipping_label_url == "https://labels.example.com/abc.pdf"

    def test_generate_label_fails_without_packing(self):
        ff_id = _create_and_pick()
        with pytest.raises(ValidationError):
            current_domain.process(
                GenerateShippingLabel(
                    fulfillment_id=ff_id,
                    label_url="https://labels.example.com/abc.pdf",
                    carrier="FakeCarrier",
                    service_level="Standard",
                ),
                asynchronous=False,
            )

    def test_generate_label_fails_when_not_in_packing_phase(self):
        items = json.dumps([{"order_item_id": "oi-1", "product_id": "prod-1", "sku": "SKU-001", "quantity": 1}])
        ff_id = current_domain.process(
            CreateFulfillment(order_id="ord-001", customer_id="cust-001", items=items),
            asynchronous=False,
        )
        with pytest.raises(ValidationError):
            current_domain.process(
                GenerateShippingLabel(
                    fulfillment_id=ff_id,
                    label_url="https://labels.example.com/abc.pdf",
                    carrier="FakeCarrier",
                    service_level="Standard",
                ),
                asynchronous=False,
            )
