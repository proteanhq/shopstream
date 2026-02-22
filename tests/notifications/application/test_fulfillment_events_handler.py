"""Application tests for Fulfillment cross-domain event handlers.

The fulfillment handlers currently just log (they lack customer_id on the shared events).
These tests verify the handlers run without errors and log appropriately.
"""

from datetime import UTC, datetime

from notifications.notification.fulfillment_events import FulfillmentEventsHandler
from shared.events.fulfillment import (
    DeliveryConfirmed,
    DeliveryException,
    ShipmentHandedOff,
)


def _make_shipment_handed_off(**overrides):
    defaults = {
        "fulfillment_id": "ful-001",
        "order_id": "ord-001",
        "carrier": "FedEx",
        "tracking_number": "TRACK123",
        "shipped_at": datetime.now(UTC),
    }
    defaults.update(overrides)
    return ShipmentHandedOff(**defaults)


def _make_delivery_confirmed(**overrides):
    defaults = {
        "fulfillment_id": "ful-002",
        "order_id": "ord-002",
        "actual_delivery": datetime.now(UTC),
        "delivered_at": datetime.now(UTC),
    }
    defaults.update(overrides)
    return DeliveryConfirmed(**defaults)


def _make_delivery_exception(**overrides):
    defaults = {
        "fulfillment_id": "ful-003",
        "order_id": "ord-003",
        "reason": "Package damaged in transit",
        "occurred_at": datetime.now(UTC),
    }
    defaults.update(overrides)
    return DeliveryException(**defaults)


class TestShipmentHandedOffHandler:
    def test_handles_shipment_without_error(self):
        event = _make_shipment_handed_off()
        handler = FulfillmentEventsHandler()
        # Should log and not raise
        handler.on_shipment_handed_off(event)

    def test_handles_with_all_fields(self):
        event = _make_shipment_handed_off(
            carrier="UPS",
            tracking_number="1Z999AA10123456784",
        )
        handler = FulfillmentEventsHandler()
        handler.on_shipment_handed_off(event)


class TestDeliveryConfirmedHandler:
    def test_handles_delivery_confirmed_without_error(self):
        event = _make_delivery_confirmed()
        handler = FulfillmentEventsHandler()
        handler.on_delivery_confirmed(event)

    def test_handles_with_specific_order(self):
        event = _make_delivery_confirmed(order_id="ord-specific")
        handler = FulfillmentEventsHandler()
        handler.on_delivery_confirmed(event)


class TestDeliveryExceptionHandler:
    def test_handles_delivery_exception_without_error(self):
        event = _make_delivery_exception()
        handler = FulfillmentEventsHandler()
        handler.on_delivery_exception(event)

    def test_handles_with_reason(self):
        event = _make_delivery_exception(
            reason="Address not found",
            order_id="ord-bad-addr",
        )
        handler = FulfillmentEventsHandler()
        handler.on_delivery_exception(event)
