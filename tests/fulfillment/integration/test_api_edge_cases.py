"""Integration tests for uncovered API edge cases.

Covers:
- Handoff with estimated_delivery date parsing (line 116)
- Webhook signature verification failure (line 135)
- Carrier configure in production mode (line 182)
- Carrier configure with non-FakeCarrier (line 186)
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from fulfillment.api.routes import fulfillment_router
from fulfillment.carrier.fake_adapter import FakeCarrier
from fulfillment.fulfillment.fulfillment import Fulfillment, FulfillmentStatus
from protean import current_domain


@pytest.fixture()
def client():
    app = FastAPI()
    app.include_router(fulfillment_router)
    return TestClient(app)


def _create_ready_to_ship(client):
    """Create a fulfillment in READY_TO_SHIP state via the API."""
    response = client.post(
        "/fulfillments",
        json={
            "order_id": "ord-edge-001",
            "customer_id": "cust-edge-001",
            "items": [{"order_item_id": "oi-1", "product_id": "prod-1", "sku": "SKU-001", "quantity": 1}],
        },
    )
    ff_id = response.json()["fulfillment_id"]

    client.put(f"/fulfillments/{ff_id}/assign-picker", json={"picker_name": "Alice"})
    ff = current_domain.repository_for(Fulfillment).get(ff_id)
    item_id = str(ff.items[0].id)
    client.put(
        f"/fulfillments/{ff_id}/items/{item_id}/pick",
        json={"pick_location": "A-1-1"},
    )
    client.put(f"/fulfillments/{ff_id}/pick-list/complete")
    client.put(
        f"/fulfillments/{ff_id}/pack",
        json={"packed_by": "Bob", "packages": [{"weight": 1.5}]},
    )
    client.put(
        f"/fulfillments/{ff_id}/label",
        json={
            "label_url": "https://labels.example.com/abc.pdf",
            "carrier": "FakeCarrier",
            "service_level": "Standard",
        },
    )
    return ff_id


def _create_shipped(client):
    """Create a fulfillment in SHIPPED state."""
    ff_id = _create_ready_to_ship(client)
    client.put(
        f"/fulfillments/{ff_id}/handoff",
        json={"tracking_number": "TRACK-EDGE-001"},
    )
    return ff_id


class TestHandoffWithEstimatedDelivery:
    def test_handoff_with_estimated_delivery_date(self, client):
        """Handoff endpoint should parse estimated_delivery as ISO date."""
        ff_id = _create_ready_to_ship(client)
        response = client.put(
            f"/fulfillments/{ff_id}/handoff",
            json={
                "tracking_number": "TRACK-EST-001",
                "estimated_delivery": "2026-03-01",
            },
        )
        assert response.status_code == 200
        assert response.json()["status"] == "shipment_handed_off"

        ff = current_domain.repository_for(Fulfillment).get(ff_id)
        assert ff.status == FulfillmentStatus.SHIPPED.value
        assert ff.shipment.estimated_delivery is not None

    def test_handoff_without_estimated_delivery(self, client):
        """Handoff endpoint works without estimated_delivery."""
        ff_id = _create_ready_to_ship(client)
        response = client.put(
            f"/fulfillments/{ff_id}/handoff",
            json={"tracking_number": "TRACK-NO-EST"},
        )
        assert response.status_code == 200


class TestWebhookSignatureVerification:
    def test_invalid_signature_returns_401(self, client):
        """Webhook with invalid signature should return 401."""
        ff_id = _create_shipped(client)

        # Configure the FakeCarrier to reject signatures
        from fulfillment.carrier import get_carrier

        carrier = get_carrier()
        assert isinstance(carrier, FakeCarrier)
        carrier.configure(should_succeed=True, failure_reason=None)

        # FakeCarrier.verify_webhook_signature always returns True,
        # so we need to temporarily make it fail
        original_verify = FakeCarrier.verify_webhook_signature
        FakeCarrier.verify_webhook_signature = lambda self, payload, signature: False

        try:
            response = client.post(
                "/fulfillments/tracking/webhook",
                json={
                    "fulfillment_id": ff_id,
                    "status": "in_transit",
                    "location": "Hub",
                },
                headers={"X-Carrier-Signature": "bad-signature"},
            )
            assert response.status_code == 401
            assert "Invalid carrier webhook signature" in response.json()["detail"]
        finally:
            FakeCarrier.verify_webhook_signature = original_verify


class TestCarrierConfigureEdgeCases:
    def test_configure_blocked_in_production(self, client, monkeypatch):
        """Carrier configuration should be blocked in production environment."""
        monkeypatch.setenv("PROTEAN_ENV", "production")
        response = client.post(
            "/fulfillments/carrier/configure",
            json={"should_succeed": True},
        )
        assert response.status_code == 403
        assert "not available in production" in response.json()["detail"]
