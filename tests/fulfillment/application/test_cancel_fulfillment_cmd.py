"""Application tests for fulfillment cancellation via domain.process()."""

import json

import pytest
from fulfillment.fulfillment.cancellation import CancelFulfillment
from fulfillment.fulfillment.creation import CreateFulfillment
from fulfillment.fulfillment.fulfillment import Fulfillment, FulfillmentStatus
from fulfillment.fulfillment.packing import GenerateShippingLabel, RecordPacking
from fulfillment.fulfillment.picking import AssignPicker, CompletePickList, RecordItemPicked
from fulfillment.fulfillment.shipping import RecordHandoff
from fulfillment.fulfillment.tracking import UpdateTrackingEvent
from protean import current_domain
from protean.exceptions import ValidationError


def _single_item_json():
    return json.dumps([{"order_item_id": "oi-1", "product_id": "prod-1", "sku": "SKU-001", "quantity": 1}])


def _create_fulfillment():
    return current_domain.process(
        CreateFulfillment(order_id="ord-001", customer_id="cust-001", items=_single_item_json()),
        asynchronous=False,
    )


def _advance_to_shipped(ff_id):
    """Advance a fulfillment through picking→packing→ready_to_ship→shipped."""
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
        RecordHandoff(fulfillment_id=ff_id, tracking_number="TRACK-001"),
        asynchronous=False,
    )


class TestCancelFulfillmentFromPending:
    def test_cancel_from_pending(self):
        ff_id = _create_fulfillment()
        current_domain.process(
            CancelFulfillment(fulfillment_id=ff_id, reason="Customer changed mind"),
            asynchronous=False,
        )
        ff = current_domain.repository_for(Fulfillment).get(ff_id)
        assert ff.status == FulfillmentStatus.CANCELLED.value

    def test_cancel_sets_reason(self):
        ff_id = _create_fulfillment()
        current_domain.process(
            CancelFulfillment(fulfillment_id=ff_id, reason="Out of stock"),
            asynchronous=False,
        )
        ff = current_domain.repository_for(Fulfillment).get(ff_id)
        assert ff.cancellation_reason == "Out of stock"


class TestCancelFulfillmentFromPicking:
    def test_cancel_from_picking(self):
        ff_id = _create_fulfillment()
        current_domain.process(AssignPicker(fulfillment_id=ff_id, picker_name="Alice"), asynchronous=False)
        current_domain.process(
            CancelFulfillment(fulfillment_id=ff_id, reason="Order cancelled"),
            asynchronous=False,
        )
        ff = current_domain.repository_for(Fulfillment).get(ff_id)
        assert ff.status == FulfillmentStatus.CANCELLED.value


class TestCancelFulfillmentFromPacking:
    def test_cancel_from_packing(self):
        ff_id = _create_fulfillment()
        current_domain.process(AssignPicker(fulfillment_id=ff_id, picker_name="Alice"), asynchronous=False)
        ff = current_domain.repository_for(Fulfillment).get(ff_id)
        current_domain.process(
            RecordItemPicked(fulfillment_id=ff_id, item_id=str(ff.items[0].id), pick_location="A-1"),
            asynchronous=False,
        )
        current_domain.process(CompletePickList(fulfillment_id=ff_id), asynchronous=False)
        current_domain.process(
            CancelFulfillment(fulfillment_id=ff_id, reason="Quality issue"),
            asynchronous=False,
        )
        ff = current_domain.repository_for(Fulfillment).get(ff_id)
        assert ff.status == FulfillmentStatus.CANCELLED.value


class TestCancelFulfillmentFromReadyToShip:
    def test_cancel_from_ready_to_ship(self):
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
        current_domain.process(
            CancelFulfillment(fulfillment_id=ff_id, reason="Carrier issue"),
            asynchronous=False,
        )
        ff = current_domain.repository_for(Fulfillment).get(ff_id)
        assert ff.status == FulfillmentStatus.CANCELLED.value


class TestCancelFulfillmentAfterShipped:
    def test_cancel_fails_after_shipped(self):
        ff_id = _create_fulfillment()
        _advance_to_shipped(ff_id)
        with pytest.raises(ValidationError):
            current_domain.process(
                CancelFulfillment(fulfillment_id=ff_id, reason="Too late"),
                asynchronous=False,
            )

    def test_cancel_fails_after_in_transit(self):
        ff_id = _create_fulfillment()
        _advance_to_shipped(ff_id)
        current_domain.process(
            UpdateTrackingEvent(fulfillment_id=ff_id, status="in_transit", location="Hub"),
            asynchronous=False,
        )
        with pytest.raises(ValidationError):
            current_domain.process(
                CancelFulfillment(fulfillment_id=ff_id, reason="Too late"),
                asynchronous=False,
            )

    def test_cancel_fails_after_delivered(self):
        ff_id = _create_fulfillment()
        _advance_to_shipped(ff_id)
        current_domain.process(
            UpdateTrackingEvent(fulfillment_id=ff_id, status="in_transit", location="Hub"),
            asynchronous=False,
        )
        from fulfillment.fulfillment.delivery import RecordDeliveryConfirmation

        current_domain.process(
            RecordDeliveryConfirmation(fulfillment_id=ff_id),
            asynchronous=False,
        )
        with pytest.raises(ValidationError):
            current_domain.process(
                CancelFulfillment(fulfillment_id=ff_id, reason="Impossible"),
                asynchronous=False,
            )
