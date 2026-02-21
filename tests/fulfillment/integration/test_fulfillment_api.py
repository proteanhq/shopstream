"""Integration tests for Fulfillment API endpoints via TestClient."""

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


def _create_fulfillment(client, **overrides):
    defaults = {
        "order_id": "ord-api-001",
        "customer_id": "cust-api-001",
        "items": [{"order_item_id": "oi-1", "product_id": "prod-1", "sku": "SKU-001", "quantity": 1}],
    }
    defaults.update(overrides)
    response = client.post("/fulfillments", json=defaults)
    assert response.status_code == 201
    return response.json()["fulfillment_id"]


def _walk_to_shipped(client, ff_id):
    """Walk a fulfillment through the lifecycle to SHIPPED state."""
    # Assign picker
    client.put(f"/fulfillments/{ff_id}/assign-picker", json={"picker_name": "Alice"})

    # Pick item
    ff = current_domain.repository_for(Fulfillment).get(ff_id)
    item_id = str(ff.items[0].id)
    client.put(
        f"/fulfillments/{ff_id}/items/{item_id}/pick",
        json={"pick_location": "A-1-1"},
    )

    # Complete pick list
    client.put(f"/fulfillments/{ff_id}/pick-list/complete")

    # Pack
    client.put(
        f"/fulfillments/{ff_id}/pack",
        json={"packed_by": "Bob", "packages": [{"weight": 1.5}]},
    )

    # Label
    client.put(
        f"/fulfillments/{ff_id}/label",
        json={
            "label_url": "https://labels.example.com/abc.pdf",
            "carrier": "FakeCarrier",
            "service_level": "Standard",
        },
    )

    # Handoff
    client.put(
        f"/fulfillments/{ff_id}/handoff",
        json={"tracking_number": "TRACK-API-001"},
    )


class TestCreateFulfillmentAPI:
    def test_create_returns_201(self, client):
        response = client.post(
            "/fulfillments",
            json={
                "order_id": "ord-001",
                "customer_id": "cust-001",
                "items": [
                    {
                        "order_item_id": "oi-1",
                        "product_id": "prod-1",
                        "sku": "SKU-001",
                        "quantity": 1,
                    }
                ],
            },
        )
        assert response.status_code == 201
        assert "fulfillment_id" in response.json()

    def test_create_persists(self, client):
        ff_id = _create_fulfillment(client)
        ff = current_domain.repository_for(Fulfillment).get(ff_id)
        assert ff.status == FulfillmentStatus.PENDING.value


class TestAssignPickerAPI:
    def test_assign_picker_returns_200(self, client):
        ff_id = _create_fulfillment(client)
        response = client.put(
            f"/fulfillments/{ff_id}/assign-picker",
            json={"picker_name": "Alice"},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "picker_assigned"

    def test_assign_picker_updates_state(self, client):
        ff_id = _create_fulfillment(client)
        client.put(f"/fulfillments/{ff_id}/assign-picker", json={"picker_name": "Alice"})
        ff = current_domain.repository_for(Fulfillment).get(ff_id)
        assert ff.status == FulfillmentStatus.PICKING.value


class TestRecordItemPickedAPI:
    def test_pick_item_returns_200(self, client):
        ff_id = _create_fulfillment(client)
        client.put(f"/fulfillments/{ff_id}/assign-picker", json={"picker_name": "Alice"})
        ff = current_domain.repository_for(Fulfillment).get(ff_id)
        item_id = str(ff.items[0].id)
        response = client.put(
            f"/fulfillments/{ff_id}/items/{item_id}/pick",
            json={"pick_location": "A-1-1"},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "item_picked"


class TestCompletePickListAPI:
    def test_complete_pick_list_returns_200(self, client):
        ff_id = _create_fulfillment(client)
        client.put(f"/fulfillments/{ff_id}/assign-picker", json={"picker_name": "Alice"})
        ff = current_domain.repository_for(Fulfillment).get(ff_id)
        item_id = str(ff.items[0].id)
        client.put(
            f"/fulfillments/{ff_id}/items/{item_id}/pick",
            json={"pick_location": "A-1-1"},
        )
        response = client.put(f"/fulfillments/{ff_id}/pick-list/complete")
        assert response.status_code == 200
        assert response.json()["status"] == "picking_completed"


class TestRecordPackingAPI:
    def test_pack_returns_200(self, client):
        ff_id = _create_fulfillment(client)
        client.put(f"/fulfillments/{ff_id}/assign-picker", json={"picker_name": "Alice"})
        ff = current_domain.repository_for(Fulfillment).get(ff_id)
        item_id = str(ff.items[0].id)
        client.put(
            f"/fulfillments/{ff_id}/items/{item_id}/pick",
            json={"pick_location": "A-1-1"},
        )
        client.put(f"/fulfillments/{ff_id}/pick-list/complete")
        response = client.put(
            f"/fulfillments/{ff_id}/pack",
            json={"packed_by": "Bob", "packages": [{"weight": 1.5}]},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "packing_completed"


class TestGenerateShippingLabelAPI:
    def test_label_returns_200(self, client):
        ff_id = _create_fulfillment(client)
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
        response = client.put(
            f"/fulfillments/{ff_id}/label",
            json={
                "label_url": "https://labels.example.com/abc.pdf",
                "carrier": "FakeCarrier",
                "service_level": "Standard",
            },
        )
        assert response.status_code == 200
        assert response.json()["status"] == "label_generated"


class TestRecordHandoffAPI:
    def test_handoff_returns_200(self, client):
        ff_id = _create_fulfillment(client)
        _walk_to_shipped(client, ff_id)
        ff = current_domain.repository_for(Fulfillment).get(ff_id)
        assert ff.status == FulfillmentStatus.SHIPPED.value


class TestRecordDeliveryAPI:
    def test_deliver_returns_200(self, client):
        ff_id = _create_fulfillment(client)
        _walk_to_shipped(client, ff_id)
        # Add tracking event to get to IN_TRANSIT
        response = client.post(
            "/fulfillments/tracking/webhook",
            json={
                "fulfillment_id": ff_id,
                "status": "in_transit",
                "location": "Hub",
            },
            headers={"X-Carrier-Signature": "test"},
        )
        assert response.status_code == 200
        response = client.put(f"/fulfillments/{ff_id}/deliver")
        assert response.status_code == 200
        assert response.json()["status"] == "delivery_confirmed"


class TestRecordExceptionAPI:
    def test_exception_returns_200(self, client):
        ff_id = _create_fulfillment(client)
        _walk_to_shipped(client, ff_id)
        client.post(
            "/fulfillments/tracking/webhook",
            json={
                "fulfillment_id": ff_id,
                "status": "in_transit",
                "location": "Hub",
            },
            headers={"X-Carrier-Signature": "test"},
        )
        response = client.put(
            f"/fulfillments/{ff_id}/exception",
            json={"reason": "Address not found", "location": "Dest City"},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "exception_recorded"


class TestCancelFulfillmentAPI:
    def test_cancel_returns_200(self, client):
        ff_id = _create_fulfillment(client)
        response = client.put(
            f"/fulfillments/{ff_id}/cancel",
            json={"reason": "Customer cancelled"},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "cancelled"

    def test_cancel_persists(self, client):
        ff_id = _create_fulfillment(client)
        client.put(
            f"/fulfillments/{ff_id}/cancel",
            json={"reason": "Customer cancelled"},
        )
        ff = current_domain.repository_for(Fulfillment).get(ff_id)
        assert ff.status == FulfillmentStatus.CANCELLED.value


class TestCarrierConfigureAPI:
    def test_configure_returns_200(self, client):
        response = client.post(
            "/fulfillments/carrier/configure",
            json={"should_succeed": False, "failure_reason": "Test failure"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["carrier"] == "FakeCarrier"
        assert data["should_succeed"] is False
        assert data["failure_reason"] == "Test failure"
