"""Fake carrier adapter — deterministic carrier for testing and development.

Generates mock tracking numbers, labels, and tracking events.
Configurable success/failure behavior for integration testing.
"""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fulfillment.carrier.port import CarrierPort


class FakeCarrier(CarrierPort):
    """Fake carrier that always succeeds by default."""

    def __init__(self):
        self.should_succeed = True
        self.failure_reason = "Carrier unavailable"

    def configure(self, should_succeed: bool = True, failure_reason: str = "Carrier unavailable"):
        """Configure the fake carrier behavior for testing."""
        self.should_succeed = should_succeed
        self.failure_reason = failure_reason

    def create_shipment(
        self,
        _order_id: str,
        _carrier: str,
        service_level: str,
        _weight: float | None = None,
        _dimensions: dict | None = None,
    ) -> dict:
        if not self.should_succeed:
            return {
                "shipment_id": None,
                "tracking_number": None,
                "label_url": None,
                "estimated_delivery": None,
                "error": self.failure_reason,
            }

        tracking_number = f"FAKE-{uuid4().hex[:12].upper()}"
        shipment_id = f"ship-{uuid4().hex[:8]}"

        # Estimate delivery based on service level
        days = {"Standard": 5, "Express": 2, "Overnight": 1}.get(service_level, 5)
        estimated_delivery = datetime.now(UTC) + timedelta(days=days)

        return {
            "shipment_id": shipment_id,
            "tracking_number": tracking_number,
            "label_url": f"https://fake-carrier.example.com/labels/{shipment_id}.pdf",
            "estimated_delivery": estimated_delivery.isoformat(),
        }

    def get_tracking(self, _tracking_number: str) -> dict:
        if not self.should_succeed:
            return {
                "status": "unknown",
                "location": None,
                "events": [],
                "error": self.failure_reason,
            }

        return {
            "status": "in_transit",
            "location": "Distribution Center, NY",
            "events": [
                {
                    "status": "picked_up",
                    "location": "Warehouse, CA",
                    "description": "Package picked up by carrier",
                    "occurred_at": datetime.now(UTC).isoformat(),
                },
                {
                    "status": "in_transit",
                    "location": "Distribution Center, NY",
                    "description": "Package in transit",
                    "occurred_at": datetime.now(UTC).isoformat(),
                },
            ],
        }

    def cancel_shipment(self, _tracking_number: str) -> dict:
        if not self.should_succeed:
            return {"cancelled": False, "reason": self.failure_reason}
        return {"cancelled": True, "reason": "Shipment cancelled successfully"}

    def verify_webhook_signature(self, _payload: str, _signature: str) -> bool:
        # FakeCarrier accepts any signature (or empty signature) for testing
        return True
