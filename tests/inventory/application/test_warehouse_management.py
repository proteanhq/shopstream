"""Application tests for warehouse management commands."""

import json

from inventory.warehouse.management import (
    AddZone,
    CreateWarehouse,
    DeactivateWarehouse,
    UpdateWarehouse,
)
from inventory.warehouse.warehouse import Warehouse
from protean import current_domain


def _create_warehouse(**overrides):
    defaults = {
        "name": "Main Warehouse",
        "address": json.dumps(
            {
                "street": "100 Industrial Blvd",
                "city": "Chicago",
                "state": "IL",
                "postal_code": "60601",
                "country": "US",
            }
        ),
        "capacity": 10000,
    }
    defaults.update(overrides)
    command = CreateWarehouse(**defaults)
    return current_domain.process(command, asynchronous=False)


class TestWarehouseManagement:
    def test_create_warehouse_returns_id(self):
        wh_id = _create_warehouse()
        assert wh_id is not None

    def test_create_warehouse_persists(self):
        wh_id = _create_warehouse()
        warehouse = current_domain.repository_for(Warehouse).get(wh_id)
        assert warehouse.name == "Main Warehouse"
        assert warehouse.address.street == "100 Industrial Blvd"

    def test_update_warehouse(self):
        wh_id = _create_warehouse()
        current_domain.process(
            UpdateWarehouse(
                warehouse_id=wh_id,
                name="Updated Warehouse",
                capacity=20000,
            ),
            asynchronous=False,
        )
        warehouse = current_domain.repository_for(Warehouse).get(wh_id)
        assert warehouse.name == "Updated Warehouse"
        assert warehouse.capacity == 20000

    def test_add_zone_to_warehouse(self):
        wh_id = _create_warehouse()
        current_domain.process(
            AddZone(
                warehouse_id=wh_id,
                zone_name="Cold Storage",
                zone_type="Cold",
            ),
            asynchronous=False,
        )
        warehouse = current_domain.repository_for(Warehouse).get(wh_id)
        assert len(warehouse.zones) == 1
        assert warehouse.zones[0].zone_name == "Cold Storage"

    def test_deactivate_warehouse(self):
        wh_id = _create_warehouse()
        current_domain.process(
            DeactivateWarehouse(warehouse_id=wh_id),
            asynchronous=False,
        )
        warehouse = current_domain.repository_for(Warehouse).get(wh_id)
        assert warehouse.is_active is False
