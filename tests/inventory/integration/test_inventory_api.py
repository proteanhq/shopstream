"""Integration tests for Inventory API endpoints via TestClient."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from inventory.api.routes import inventory_router
from inventory.stock.stock import InventoryItem
from protean import current_domain


@pytest.fixture()
def client():
    app = FastAPI()
    app.include_router(inventory_router)
    return TestClient(app)


def _initialize_stock(client, **overrides):
    """Helper: POST /inventory and return the inventory_item_id."""
    defaults = {
        "product_id": "prod-001",
        "variant_id": "var-001",
        "warehouse_id": "wh-001",
        "sku": "TSHIRT-BLK-M",
        "initial_quantity": 100,
        "reorder_point": 10,
        "reorder_quantity": 50,
    }
    defaults.update(overrides)
    response = client.post("/inventory", json=defaults)
    assert response.status_code == 201
    return response.json()["inventory_item_id"]


def _reserve(client, item_id, order_id="ord-001", quantity=10):
    """Helper: POST /inventory/{id}/reserve and return reservation_id."""
    response = client.post(
        f"/inventory/{item_id}/reserve",
        json={"order_id": order_id, "quantity": quantity},
    )
    assert response.status_code == 201
    # Get reservation_id from aggregate
    item = current_domain.repository_for(InventoryItem).get(item_id)
    return str(item.reservations[-1].id)


class TestInitializeStockEndpoint:
    def test_initialize_stock(self, client):
        item_id = _initialize_stock(client)
        assert item_id is not None

        item = current_domain.repository_for(InventoryItem).get(item_id)
        assert item.product_id == "prod-001"
        assert item.sku == "TSHIRT-BLK-M"

    def test_response_format(self, client):
        response = client.post(
            "/inventory",
            json={
                "product_id": "prod-002",
                "variant_id": "var-002",
                "warehouse_id": "wh-002",
                "sku": "SKU-002",
                "initial_quantity": 50,
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert "inventory_item_id" in data


class TestReceiveStockEndpoint:
    def test_receive_stock(self, client):
        item_id = _initialize_stock(client, initial_quantity=100)
        response = client.put(
            f"/inventory/{item_id}/receive",
            json={"quantity": 20},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

        item = current_domain.repository_for(InventoryItem).get(item_id)
        assert item.levels.on_hand == 120

    def test_receive_with_reference(self, client):
        item_id = _initialize_stock(client, initial_quantity=100)
        response = client.put(
            f"/inventory/{item_id}/receive",
            json={"quantity": 10, "reference": "PO-12345"},
        )
        assert response.status_code == 200


class TestReserveStockEndpoint:
    def test_reserve_stock(self, client):
        item_id = _initialize_stock(client, initial_quantity=100)
        response = client.post(
            f"/inventory/{item_id}/reserve",
            json={"order_id": "ord-001", "quantity": 10},
        )
        assert response.status_code == 201

        item = current_domain.repository_for(InventoryItem).get(item_id)
        assert item.levels.reserved == 10
        assert item.levels.available == 90


class TestReleaseReservationEndpoint:
    def test_release_reservation(self, client):
        item_id = _initialize_stock(client, initial_quantity=100)
        reservation_id = _reserve(client, item_id, quantity=10)

        response = client.put(
            f"/inventory/{item_id}/reservations/{reservation_id}/release",
            json={"reason": "Customer cancelled"},
        )
        assert response.status_code == 200

        item = current_domain.repository_for(InventoryItem).get(item_id)
        assert item.levels.reserved == 0
        assert item.levels.available == 100


class TestConfirmReservationEndpoint:
    def test_confirm_reservation(self, client):
        item_id = _initialize_stock(client, initial_quantity=100)
        reservation_id = _reserve(client, item_id, quantity=10)

        response = client.put(
            f"/inventory/{item_id}/reservations/{reservation_id}/confirm",
        )
        assert response.status_code == 200


class TestCommitStockEndpoint:
    def test_commit_stock(self, client):
        item_id = _initialize_stock(client, initial_quantity=100)
        reservation_id = _reserve(client, item_id, quantity=10)

        # Confirm first
        client.put(f"/inventory/{item_id}/reservations/{reservation_id}/confirm")

        response = client.put(f"/inventory/{item_id}/commit/{reservation_id}")
        assert response.status_code == 200

        item = current_domain.repository_for(InventoryItem).get(item_id)
        assert item.levels.on_hand == 90
        assert item.levels.reserved == 0


class TestAdjustStockEndpoint:
    def test_adjust_stock(self, client):
        item_id = _initialize_stock(client, initial_quantity=100)
        response = client.put(
            f"/inventory/{item_id}/adjust",
            json={
                "quantity_change": -10,
                "adjustment_type": "Shrinkage",
                "reason": "Inventory shrinkage",
                "adjusted_by": "manager-001",
            },
        )
        assert response.status_code == 200

        item = current_domain.repository_for(InventoryItem).get(item_id)
        assert item.levels.on_hand == 90


class TestMarkDamagedEndpoint:
    def test_mark_damaged(self, client):
        item_id = _initialize_stock(client, initial_quantity=100)
        response = client.put(
            f"/inventory/{item_id}/damage",
            json={"quantity": 5, "reason": "Water damage"},
        )
        assert response.status_code == 200

        item = current_domain.repository_for(InventoryItem).get(item_id)
        assert item.levels.damaged == 5


class TestWriteOffDamagedEndpoint:
    def test_write_off_damaged(self, client):
        item_id = _initialize_stock(client, initial_quantity=100)
        client.put(
            f"/inventory/{item_id}/damage",
            json={"quantity": 10, "reason": "Flood"},
        )
        response = client.put(
            f"/inventory/{item_id}/damage/write-off",
            json={"quantity": 5, "approved_by": "manager-001"},
        )
        assert response.status_code == 200

        item = current_domain.repository_for(InventoryItem).get(item_id)
        assert item.levels.damaged == 5


class TestReturnToStockEndpoint:
    def test_return_to_stock(self, client):
        item_id = _initialize_stock(client, initial_quantity=100)
        response = client.put(
            f"/inventory/{item_id}/return",
            json={"quantity": 10, "order_id": "ord-001"},
        )
        assert response.status_code == 200

        item = current_domain.repository_for(InventoryItem).get(item_id)
        assert item.levels.on_hand == 110


class TestStockCheckEndpoint:
    def test_stock_check(self, client):
        item_id = _initialize_stock(client, initial_quantity=100)
        response = client.put(
            f"/inventory/{item_id}/stock-check",
            json={"counted_quantity": 95, "checked_by": "checker-001"},
        )
        assert response.status_code == 200

        item = current_domain.repository_for(InventoryItem).get(item_id)
        assert item.levels.on_hand == 95
        assert item.last_stock_check is not None


class TestFullLifecycleViaApi:
    def test_init_receive_reserve_confirm_commit(self, client):
        """Full lifecycle test through the API."""
        item_id = _initialize_stock(client, initial_quantity=100)

        # Receive
        client.put(f"/inventory/{item_id}/receive", json={"quantity": 50})

        # Reserve
        reservation_id = _reserve(client, item_id, order_id="ord-full", quantity=30)

        # Confirm
        client.put(f"/inventory/{item_id}/reservations/{reservation_id}/confirm")

        # Commit
        client.put(f"/inventory/{item_id}/commit/{reservation_id}")

        item = current_domain.repository_for(InventoryItem).get(item_id)
        assert item.levels.on_hand == 120  # 100 + 50 - 30
        assert item.levels.reserved == 0
        assert item.levels.available == 120
