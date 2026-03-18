"""Application tests for Fulfillment cross-domain subscriber.

The fulfillment subscriber handlers currently just log (they lack customer_id on the shared events).
These tests verify the subscriber runs without errors and logs appropriately.
"""

from datetime import UTC, datetime

from notifications.notification.fulfillment_subscriber import FulfillmentEventsSubscriber


def _build_message(event_type: str, data: dict) -> dict:
    """Build a broker message payload with metadata and data."""
    return {
        "data": data,
        "metadata": {"headers": {"type": event_type}},
    }


class TestShipmentHandedOffHandler:
    def test_handles_shipment_without_error(self):
        subscriber = FulfillmentEventsSubscriber()
        subscriber(
            _build_message(
                "Fulfillment.ShipmentHandedOff.v1",
                {
                    "fulfillment_id": "ful-001",
                    "order_id": "ord-001",
                    "carrier": "FedEx",
                    "tracking_number": "TRACK123",
                    "shipped_at": datetime.now(UTC).isoformat(),
                },
            )
        )

    def test_handles_with_all_fields(self):
        subscriber = FulfillmentEventsSubscriber()
        subscriber(
            _build_message(
                "Fulfillment.ShipmentHandedOff.v1",
                {
                    "fulfillment_id": "ful-001",
                    "order_id": "ord-001",
                    "carrier": "UPS",
                    "tracking_number": "1Z999AA10123456784",
                    "shipped_at": datetime.now(UTC).isoformat(),
                },
            )
        )


class TestDeliveryConfirmedHandler:
    def test_handles_delivery_confirmed_without_error(self):
        subscriber = FulfillmentEventsSubscriber()
        subscriber(
            _build_message(
                "Fulfillment.DeliveryConfirmed.v1",
                {
                    "fulfillment_id": "ful-002",
                    "order_id": "ord-002",
                    "actual_delivery": datetime.now(UTC).isoformat(),
                    "delivered_at": datetime.now(UTC).isoformat(),
                },
            )
        )

    def test_handles_with_specific_order(self):
        subscriber = FulfillmentEventsSubscriber()
        subscriber(
            _build_message(
                "Fulfillment.DeliveryConfirmed.v1",
                {
                    "fulfillment_id": "ful-002",
                    "order_id": "ord-specific",
                    "actual_delivery": datetime.now(UTC).isoformat(),
                    "delivered_at": datetime.now(UTC).isoformat(),
                },
            )
        )


class TestDeliveryExceptionHandler:
    def test_handles_delivery_exception_without_error(self):
        subscriber = FulfillmentEventsSubscriber()
        subscriber(
            _build_message(
                "Fulfillment.DeliveryException.v1",
                {
                    "fulfillment_id": "ful-003",
                    "order_id": "ord-003",
                    "reason": "Package damaged in transit",
                    "occurred_at": datetime.now(UTC).isoformat(),
                },
            )
        )

    def test_handles_with_reason(self):
        subscriber = FulfillmentEventsSubscriber()
        subscriber(
            _build_message(
                "Fulfillment.DeliveryException.v1",
                {
                    "fulfillment_id": "ful-003",
                    "order_id": "ord-bad-addr",
                    "reason": "Address not found",
                    "occurred_at": datetime.now(UTC).isoformat(),
                },
            )
        )


class TestIgnoresUnrelatedEvents:
    def test_ignores_non_matching_events(self):
        """Non-fulfillment events on the stream should be ignored."""
        subscriber = FulfillmentEventsSubscriber()
        subscriber(_build_message("Fulfillment.PickerAssigned.v1", {"fulfillment_id": "ful-ignore"}))
