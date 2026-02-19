"""Integration tests for Warehouse API endpoints via TestClient."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from inventory.api.routes import warehouse_router
from inventory.warehouse.warehouse import Warehouse
from protean import current_domain


@pytest.fixture()
def client():
    app = FastAPI()
    app.include_router(warehouse_router)
    return TestClient(app)


def _create_warehouse(client, **overrides):
    """Helper: POST /warehouses and return the warehouse_id."""
    defaults = {
        "name": "Main Warehouse",
        "address": {
            "street": "123 Logistics Way",
            "city": "Dallas",
            "state": "TX",
            "postal_code": "75201",
            "country": "US",
        },
        "capacity": 10000,
    }
    defaults.update(overrides)
    response = client.post("/warehouses", json=defaults)
    assert response.status_code == 201
    return response.json()["warehouse_id"]


class TestCreateWarehouseEndpoint:
    def test_create_warehouse(self, client):
        wh_id = _create_warehouse(client)
        assert wh_id is not None

        wh = current_domain.repository_for(Warehouse).get(wh_id)
        assert wh.name == "Main Warehouse"
        assert wh.capacity == 10000
        assert wh.is_active is True

    def test_response_format(self, client):
        response = client.post(
            "/warehouses",
            json={
                "name": "Secondary",
                "address": {
                    "street": "456 Ave",
                    "city": "Austin",
                    "postal_code": "73301",
                    "country": "US",
                },
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert "warehouse_id" in data


class TestUpdateWarehouseEndpoint:
    def test_update_warehouse(self, client):
        wh_id = _create_warehouse(client)
        response = client.put(
            f"/warehouses/{wh_id}",
            json={"name": "Updated Warehouse", "capacity": 20000},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

        wh = current_domain.repository_for(Warehouse).get(wh_id)
        assert wh.name == "Updated Warehouse"
        assert wh.capacity == 20000


class TestAddZoneEndpoint:
    def test_add_zone(self, client):
        wh_id = _create_warehouse(client)
        response = client.post(
            f"/warehouses/{wh_id}/zones",
            json={"zone_name": "Zone A", "zone_type": "Regular"},
        )
        assert response.status_code == 201

        wh = current_domain.repository_for(Warehouse).get(wh_id)
        assert len(wh.zones) == 1
        assert wh.zones[0].zone_name == "Zone A"

    def test_add_cold_zone(self, client):
        wh_id = _create_warehouse(client)
        response = client.post(
            f"/warehouses/{wh_id}/zones",
            json={"zone_name": "Cold Storage", "zone_type": "Cold"},
        )
        assert response.status_code == 201

        wh = current_domain.repository_for(Warehouse).get(wh_id)
        assert wh.zones[0].zone_type == "Cold"


class TestRemoveZoneEndpoint:
    def test_remove_zone(self, client):
        wh_id = _create_warehouse(client)
        client.post(
            f"/warehouses/{wh_id}/zones",
            json={"zone_name": "Zone A"},
        )

        wh = current_domain.repository_for(Warehouse).get(wh_id)
        zone_id = str(wh.zones[0].id)

        response = client.delete(f"/warehouses/{wh_id}/zones/{zone_id}")
        assert response.status_code == 200

        wh = current_domain.repository_for(Warehouse).get(wh_id)
        assert len(wh.zones) == 0


class TestDeactivateWarehouseEndpoint:
    def test_deactivate_warehouse(self, client):
        wh_id = _create_warehouse(client)
        response = client.put(f"/warehouses/{wh_id}/deactivate")
        assert response.status_code == 200

        wh = current_domain.repository_for(Warehouse).get(wh_id)
        assert wh.is_active is False
