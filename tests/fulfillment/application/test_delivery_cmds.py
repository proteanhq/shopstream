"""Application tests for delivery commands via domain.process()."""

import json

import pytest
from fulfillment.fulfillment.creation import CreateFulfillment
from fulfillment.fulfillment.delivery import RecordDeliveryConfirmation, RecordDeliveryException
from fulfillment.fulfillment.fulfillment import Fulfillment, FulfillmentStatus
from fulfillment.fulfillment.packing import GenerateShippingLabel, RecordPacking
from fulfillment.fulfillment.picking import AssignPicker, CompletePickList, RecordItemPicked
from fulfillment.fulfillment.shipping import RecordHandoff
from fulfillment.fulfillment.tracking import UpdateTrackingEvent
from protean import current_domain
from protean.exceptions import ValidationError


def _create_in_transit():
    """Create a fulfillment in IN_TRANSIT state."""
    items = json.dumps([{"order_item_id": "oi-1", "product_id": "prod-1", "sku": "SKU-001", "quantity": 1}])
    ff_id = current_domain.process(
        CreateFulfillment(order_id="ord-001", customer_id="cust-001", items=items),
        asynchronous=False,
    )
    current_domain.process(AssignPicker(fulfillment_id=ff_id, picker_name="Alice"), asynchronous=False)
    ff = current_domain.repository_for(Fulfillment).get(ff_id)
    current_domain.process(
        RecordItemPicked(fulfillment_id=ff_id, item_id=str(ff.items[0].id), pick_location="A-1"),
        asynchronous=False,
    )
    current_domain.process(CompletePickList(fulfillment_id=ff_id), asynchronous=False)
    current_domain.process(
        RecordPacking(fulfillment_id=ff_id, packed_by="Bob", packages=json.dumps([{"weight": 1.5}])),
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
    current_domain.process(
        UpdateTrackingEvent(fulfillment_id=ff_id, status="in_transit", location="Hub, TX"),
        asynchronous=False,
    )
    return ff_id


class TestRecordDeliveryConfirmation:
    def test_delivery_transitions_to_delivered(self):
        ff_id = _create_in_transit()
        current_domain.process(
            RecordDeliveryConfirmation(fulfillment_id=ff_id),
            asynchronous=False,
        )
        ff = current_domain.repository_for(Fulfillment).get(ff_id)
        assert ff.status == FulfillmentStatus.DELIVERED.value

    def test_delivery_sets_actual_delivery(self):
        ff_id = _create_in_transit()
        current_domain.process(
            RecordDeliveryConfirmation(fulfillment_id=ff_id),
            asynchronous=False,
        )
        ff = current_domain.repository_for(Fulfillment).get(ff_id)
        assert ff.shipment.actual_delivery is not None

    def test_delivery_fails_from_pending(self):
        items = json.dumps([{"order_item_id": "oi-1", "product_id": "prod-1", "sku": "SKU-001", "quantity": 1}])
        ff_id = current_domain.process(
            CreateFulfillment(order_id="ord-001", customer_id="cust-001", items=items),
            asynchronous=False,
        )
        with pytest.raises(ValidationError):
            current_domain.process(
                RecordDeliveryConfirmation(fulfillment_id=ff_id),
                asynchronous=False,
            )


class TestRecordDeliveryException:
    def test_exception_transitions_to_exception_state(self):
        ff_id = _create_in_transit()
        current_domain.process(
            RecordDeliveryException(fulfillment_id=ff_id, reason="Address not found", location="Dest City"),
            asynchronous=False,
        )
        ff = current_domain.repository_for(Fulfillment).get(ff_id)
        assert ff.status == FulfillmentStatus.EXCEPTION.value

    def test_exception_adds_tracking_event(self):
        ff_id = _create_in_transit()
        current_domain.process(
            RecordDeliveryException(fulfillment_id=ff_id, reason="Address not found", location="Dest City"),
            asynchronous=False,
        )
        ff = current_domain.repository_for(Fulfillment).get(ff_id)
        exception_events = [e for e in ff.tracking_events if e.status == "EXCEPTION"]
        assert len(exception_events) >= 1

    def test_exception_recovery_back_to_in_transit(self):
        """After an exception, a tracking event should recover to IN_TRANSIT."""
        ff_id = _create_in_transit()
        current_domain.process(
            RecordDeliveryException(fulfillment_id=ff_id, reason="Address not found", location="Dest City"),
            asynchronous=False,
        )
        # Carrier reports movement again — should recover to IN_TRANSIT
        current_domain.process(
            UpdateTrackingEvent(fulfillment_id=ff_id, status="in_transit", location="Local Hub"),
            asynchronous=False,
        )
        ff = current_domain.repository_for(Fulfillment).get(ff_id)
        assert ff.status == FulfillmentStatus.IN_TRANSIT.value

    def test_delivery_after_exception(self):
        """A fulfillment can be delivered after recovering from an exception."""
        ff_id = _create_in_transit()
        current_domain.process(
            RecordDeliveryException(fulfillment_id=ff_id, reason="No one home", location="Dest City"),
            asynchronous=False,
        )
        # Deliver directly from EXCEPTION (allowed by state machine)
        current_domain.process(
            RecordDeliveryConfirmation(fulfillment_id=ff_id),
            asynchronous=False,
        )
        ff = current_domain.repository_for(Fulfillment).get(ff_id)
        assert ff.status == FulfillmentStatus.DELIVERED.value

    def test_exception_fails_from_pending(self):
        items = json.dumps([{"order_item_id": "oi-1", "product_id": "prod-1", "sku": "SKU-001", "quantity": 1}])
        ff_id = current_domain.process(
            CreateFulfillment(order_id="ord-001", customer_id="cust-001", items=items),
            asynchronous=False,
        )
        with pytest.raises(ValidationError):
            current_domain.process(
                RecordDeliveryException(fulfillment_id=ff_id, reason="Something wrong"),
                asynchronous=False,
            )
