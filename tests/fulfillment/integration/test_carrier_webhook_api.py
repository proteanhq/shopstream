"""Integration tests for carrier webhook endpoint."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from fulfillment.api.routes import fulfillment_router
from fulfillment.fulfillment.fulfillment import Fulfillment, FulfillmentStatus
from protean import current_domain


@pytest.fixture()
def client():
    app = FastAPI()
    app.include_router(fulfillment_router)
    return TestClient(app)


def _create_shipped_fulfillment(client):
    """Create a fulfillment in SHIPPED state via the API."""
    response = client.post(
        "/fulfillments",
        json={
            "order_id": "ord-wh-001",
            "customer_id": "cust-wh-001",
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
    client.put(
        f"/fulfillments/{ff_id}/handoff",
        json={"tracking_number": "TRACK-WH-001"},
    )
    return ff_id


class TestTrackingWebhook:
    def test_webhook_returns_200(self, client):
        ff_id = _create_shipped_fulfillment(client)
        response = client.post(
            "/fulfillments/tracking/webhook",
            json={
                "fulfillment_id": ff_id,
                "status": "in_transit",
                "location": "Distribution Center, NY",
                "description": "Package in transit",
            },
            headers={"X-Carrier-Signature": "valid-sig"},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "tracking_updated"

    def test_webhook_updates_fulfillment_status(self, client):
        ff_id = _create_shipped_fulfillment(client)
        client.post(
            "/fulfillments/tracking/webhook",
            json={
                "fulfillment_id": ff_id,
                "status": "in_transit",
                "location": "Hub, TX",
            },
            headers={"X-Carrier-Signature": "valid-sig"},
        )
        ff = current_domain.repository_for(Fulfillment).get(ff_id)
        assert ff.status == FulfillmentStatus.IN_TRANSIT.value

    def test_webhook_adds_tracking_event(self, client):
        ff_id = _create_shipped_fulfillment(client)
        client.post(
            "/fulfillments/tracking/webhook",
            json={
                "fulfillment_id": ff_id,
                "status": "in_transit",
                "location": "Hub, TX",
                "description": "Arrived at hub",
            },
            headers={"X-Carrier-Signature": "valid-sig"},
        )
        ff = current_domain.repository_for(Fulfillment).get(ff_id)
        assert len(ff.tracking_events) == 1
        assert ff.tracking_events[0].location == "Hub, TX"

    def test_multiple_webhook_events(self, client):
        ff_id = _create_shipped_fulfillment(client)
        client.post(
            "/fulfillments/tracking/webhook",
            json={
                "fulfillment_id": ff_id,
                "status": "in_transit",
                "location": "Hub A",
            },
            headers={"X-Carrier-Signature": "sig1"},
        )
        client.post(
            "/fulfillments/tracking/webhook",
            json={
                "fulfillment_id": ff_id,
                "status": "out_for_delivery",
                "location": "Local Office",
            },
            headers={"X-Carrier-Signature": "sig2"},
        )
        ff = current_domain.repository_for(Fulfillment).get(ff_id)
        assert len(ff.tracking_events) == 2
