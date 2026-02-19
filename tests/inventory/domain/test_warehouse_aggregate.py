"""Tests for Warehouse aggregate."""

import pytest
from inventory.warehouse.events import (
    WarehouseCreated,
    WarehouseDeactivated,
    WarehouseUpdated,
    ZoneAdded,
    ZoneRemoved,
)
from inventory.warehouse.warehouse import Warehouse, WarehouseAddress, ZoneType
from protean.exceptions import ValidationError


def _make_warehouse(**overrides):
    defaults = {
        "name": "Main Warehouse",
        "address": {
            "street": "100 Industrial Blvd",
            "city": "Chicago",
            "state": "IL",
            "postal_code": "60601",
            "country": "US",
        },
        "capacity": 10000,
    }
    defaults.update(overrides)
    return Warehouse.create(**defaults)


class TestWarehouseCreation:
    def test_create_sets_name(self):
        wh = _make_warehouse()
        assert wh.name == "Main Warehouse"

    def test_create_sets_address(self):
        wh = _make_warehouse()
        assert wh.address.street == "100 Industrial Blvd"
        assert wh.address.city == "Chicago"
        assert wh.address.state == "IL"
        assert wh.address.postal_code == "60601"
        assert wh.address.country == "US"

    def test_create_sets_capacity(self):
        wh = _make_warehouse(capacity=5000)
        assert wh.capacity == 5000

    def test_create_is_active_by_default(self):
        wh = _make_warehouse()
        assert wh.is_active is True

    def test_create_generates_id(self):
        wh = _make_warehouse()
        assert wh.id is not None

    def test_create_sets_timestamps(self):
        wh = _make_warehouse()
        assert wh.created_at is not None
        assert wh.updated_at is not None

    def test_create_raises_warehouse_created_event(self):
        wh = _make_warehouse()
        created_events = [e for e in wh._events if isinstance(e, WarehouseCreated)]
        assert len(created_events) == 1
        event = created_events[0]
        assert event.warehouse_id == str(wh.id)
        assert event.name == "Main Warehouse"


class TestWarehouseUpdate:
    def test_update_details(self):
        wh = _make_warehouse()
        wh.update_details(name="Updated Warehouse", capacity=20000)
        assert wh.name == "Updated Warehouse"
        assert wh.capacity == 20000

    def test_update_name_only(self):
        wh = _make_warehouse(capacity=5000)
        wh.update_details(name="New Name")
        assert wh.name == "New Name"
        assert wh.capacity == 5000

    def test_update_capacity_only(self):
        wh = _make_warehouse()
        wh.update_details(capacity=20000)
        assert wh.capacity == 20000

    def test_update_raises_event(self):
        wh = _make_warehouse()
        wh.update_details(name="Updated")
        updated_events = [e for e in wh._events if isinstance(e, WarehouseUpdated)]
        assert len(updated_events) == 1


class TestZoneManagement:
    def test_add_zone(self):
        wh = _make_warehouse()
        wh.add_zone(zone_name="Cold Storage")
        assert len(wh.zones) == 1
        assert wh.zones[0].zone_name == "Cold Storage"
        assert wh.zones[0].zone_type == ZoneType.REGULAR.value

    def test_add_zone_with_type(self):
        wh = _make_warehouse()
        wh.add_zone(zone_name="Freezer", zone_type=ZoneType.COLD.value)
        assert wh.zones[0].zone_type == ZoneType.COLD.value

    def test_add_zone_raises_event(self):
        wh = _make_warehouse()
        wh.add_zone(zone_name="Hazmat Area", zone_type=ZoneType.HAZMAT.value)
        zone_events = [e for e in wh._events if isinstance(e, ZoneAdded)]
        assert len(zone_events) == 1
        event = zone_events[0]
        assert event.zone_name == "Hazmat Area"
        assert event.zone_type == ZoneType.HAZMAT.value

    def test_add_multiple_zones(self):
        wh = _make_warehouse()
        wh.add_zone(zone_name="Zone A")
        wh.add_zone(zone_name="Zone B", zone_type=ZoneType.COLD.value)
        assert len(wh.zones) == 2

    def test_remove_zone(self):
        wh = _make_warehouse()
        wh.add_zone(zone_name="Zone A")
        zone_id = wh.zones[0].id
        wh.remove_zone(zone_id=zone_id)
        assert len(wh.zones) == 0

    def test_remove_zone_raises_event(self):
        wh = _make_warehouse()
        wh.add_zone(zone_name="Zone A")
        zone_id = wh.zones[0].id
        wh.remove_zone(zone_id=zone_id)
        remove_events = [e for e in wh._events if isinstance(e, ZoneRemoved)]
        assert len(remove_events) == 1

    def test_remove_nonexistent_zone_fails(self):
        wh = _make_warehouse()
        with pytest.raises(ValidationError) as exc_info:
            wh.remove_zone(zone_id="fake-id")
        assert "zone_id" in exc_info.value.messages


class TestWarehouseDeactivation:
    def test_deactivate(self):
        wh = _make_warehouse()
        wh.deactivate()
        assert wh.is_active is False

    def test_deactivate_raises_event(self):
        wh = _make_warehouse()
        wh.deactivate()
        deactivated_events = [e for e in wh._events if isinstance(e, WarehouseDeactivated)]
        assert len(deactivated_events) == 1

    def test_deactivate_already_inactive_fails(self):
        wh = _make_warehouse()
        wh.deactivate()
        with pytest.raises(ValidationError) as exc_info:
            wh.deactivate()
        assert "warehouse" in exc_info.value.messages


class TestWarehouseAddressVO:
    def test_construction(self):
        addr = WarehouseAddress(
            street="100 Industrial Blvd",
            city="Chicago",
            state="IL",
            postal_code="60601",
            country="US",
        )
        assert addr.street == "100 Industrial Blvd"
        assert addr.city == "Chicago"

    def test_requires_street(self):
        with pytest.raises(ValidationError):
            WarehouseAddress(
                city="Chicago",
                postal_code="60601",
                country="US",
            )

    def test_state_is_optional(self):
        addr = WarehouseAddress(
            street="100 Industrial Blvd",
            city="Chicago",
            postal_code="60601",
            country="US",
        )
        assert addr.state is None


class TestWarehouseEvents:
    def test_warehouse_created_event_fields(self):
        wh = _make_warehouse()
        event = next(e for e in wh._events if isinstance(e, WarehouseCreated))
        assert event.warehouse_id == str(wh.id)
        assert event.name == "Main Warehouse"
        assert event.created_at is not None

    def test_zone_added_event_fields(self):
        wh = _make_warehouse()
        wh.add_zone(zone_name="Zone A", zone_type=ZoneType.COLD.value)
        event = next(e for e in wh._events if isinstance(e, ZoneAdded))
        assert event.warehouse_id == str(wh.id)
        assert event.zone_name == "Zone A"
        assert event.zone_type == ZoneType.COLD.value

    def test_warehouse_deactivated_event_fields(self):
        wh = _make_warehouse()
        wh.deactivate()
        event = next(e for e in wh._events if isinstance(e, WarehouseDeactivated))
        assert event.warehouse_id == str(wh.id)
        assert event.deactivated_at is not None
