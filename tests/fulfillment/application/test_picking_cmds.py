"""Application tests for picking commands via domain.process()."""

import json

import pytest
from fulfillment.fulfillment.creation import CreateFulfillment
from fulfillment.fulfillment.fulfillment import Fulfillment, FulfillmentItemStatus, FulfillmentStatus
from fulfillment.fulfillment.picking import AssignPicker, CompletePickList, RecordItemPicked
from protean import current_domain
from protean.exceptions import ValidationError


def _create_fulfillment(item_count=2):
    items = [
        {"order_item_id": f"oi-{i}", "product_id": f"prod-{i}", "sku": f"SKU-{i:03d}", "quantity": 1}
        for i in range(1, item_count + 1)
    ]
    return current_domain.process(
        CreateFulfillment(
            order_id="ord-001",
            customer_id="cust-001",
            items=json.dumps(items),
        ),
        asynchronous=False,
    )


class TestAssignPicker:
    def test_assign_picker_transitions_to_picking(self):
        ff_id = _create_fulfillment()
        current_domain.process(
            AssignPicker(fulfillment_id=ff_id, picker_name="John"),
            asynchronous=False,
        )
        ff = current_domain.repository_for(Fulfillment).get(ff_id)
        assert ff.status == FulfillmentStatus.PICKING.value

    def test_assign_picker_sets_pick_list(self):
        ff_id = _create_fulfillment()
        current_domain.process(
            AssignPicker(fulfillment_id=ff_id, picker_name="John"),
            asynchronous=False,
        )
        ff = current_domain.repository_for(Fulfillment).get(ff_id)
        assert ff.pick_list.assigned_to == "John"
        assert ff.pick_list.assigned_at is not None


class TestRecordItemPicked:
    def test_record_item_picked_updates_item_status(self):
        ff_id = _create_fulfillment(item_count=1)
        current_domain.process(
            AssignPicker(fulfillment_id=ff_id, picker_name="John"),
            asynchronous=False,
        )
        ff = current_domain.repository_for(Fulfillment).get(ff_id)
        item_id = str(ff.items[0].id)

        current_domain.process(
            RecordItemPicked(fulfillment_id=ff_id, item_id=item_id, pick_location="A-1-1"),
            asynchronous=False,
        )
        ff = current_domain.repository_for(Fulfillment).get(ff_id)
        assert ff.items[0].status == FulfillmentItemStatus.PICKED.value
        assert ff.items[0].pick_location == "A-1-1"


class TestCompletePickList:
    def test_complete_pick_list_transitions_to_packing(self):
        ff_id = _create_fulfillment(item_count=1)
        current_domain.process(
            AssignPicker(fulfillment_id=ff_id, picker_name="John"),
            asynchronous=False,
        )
        ff = current_domain.repository_for(Fulfillment).get(ff_id)
        item_id = str(ff.items[0].id)
        current_domain.process(
            RecordItemPicked(fulfillment_id=ff_id, item_id=item_id, pick_location="A-1-1"),
            asynchronous=False,
        )
        current_domain.process(
            CompletePickList(fulfillment_id=ff_id),
            asynchronous=False,
        )
        ff = current_domain.repository_for(Fulfillment).get(ff_id)
        assert ff.status == FulfillmentStatus.PACKING.value

    def test_complete_pick_list_fails_with_unpicked_items(self):
        ff_id = _create_fulfillment(item_count=2)
        current_domain.process(
            AssignPicker(fulfillment_id=ff_id, picker_name="John"),
            asynchronous=False,
        )
        with pytest.raises(ValidationError):
            current_domain.process(
                CompletePickList(fulfillment_id=ff_id),
                asynchronous=False,
            )
