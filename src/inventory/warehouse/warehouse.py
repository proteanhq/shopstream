"""Warehouse aggregate (CQRS) — physical location where inventory is stored.

Warehouses contain zones (regular, cold storage, hazmat) and track capacity.
This is a standard CQRS aggregate (not event sourced).
"""

import json
from datetime import UTC, datetime
from enum import Enum
from uuid import uuid4

from protean.exceptions import ValidationError
from protean.fields import Boolean, DateTime, HasMany, Integer, String, ValueObject

from inventory.domain import inventory
from inventory.warehouse.events import (
    WarehouseCreated,
    WarehouseDeactivated,
    WarehouseUpdated,
    ZoneAdded,
    ZoneRemoved,
)


class ZoneType(Enum):
    REGULAR = "Regular"
    COLD = "Cold"
    HAZMAT = "Hazmat"


@inventory.value_object(part_of="Warehouse")
class WarehouseAddress:
    """Physical address of a warehouse."""

    street = String(required=True, max_length=255)
    city = String(required=True, max_length=100)
    state = String(max_length=100)
    postal_code = String(required=True, max_length=20)
    country = String(required=True, max_length=100)


@inventory.entity(part_of="Warehouse")
class Zone:
    """A logical area within a warehouse (e.g., cold storage, hazmat)."""

    zone_name = String(required=True, max_length=100)
    zone_type = String(
        choices=ZoneType,
        default=ZoneType.REGULAR.value,
    )


@inventory.aggregate
class Warehouse:
    """A physical location where inventory is stored."""

    name = String(required=True, max_length=255)
    address = ValueObject(WarehouseAddress)
    capacity = Integer(default=0)
    is_active = Boolean(default=True)
    zones = HasMany(Zone)
    created_at = DateTime()
    updated_at = DateTime()

    @classmethod
    def create(cls, name, address, capacity=0):
        """Create a new warehouse."""
        now = datetime.now(UTC)
        warehouse = cls(
            name=name,
            address=WarehouseAddress(**address) if isinstance(address, dict) else address,
            capacity=capacity,
            created_at=now,
            updated_at=now,
        )
        warehouse.raise_(
            WarehouseCreated(
                warehouse_id=str(warehouse.id),
                name=name,
                address=json.dumps(address if isinstance(address, dict) else address.to_dict()),
                capacity=str(capacity),
                created_at=now,
            )
        )
        return warehouse

    def update_details(self, name=None, capacity=None):
        """Update warehouse name and/or capacity."""
        if name is not None:
            self.name = name
        if capacity is not None:
            self.capacity = capacity
        self.updated_at = datetime.now(UTC)
        self.raise_(
            WarehouseUpdated(
                warehouse_id=str(self.id),
                name=self.name,
                capacity=str(self.capacity),
                updated_at=self.updated_at,
            )
        )

    def add_zone(self, zone_name, zone_type=ZoneType.REGULAR.value):
        """Add a zone to the warehouse."""
        zone_id = str(uuid4())
        zone = Zone(id=zone_id, zone_name=zone_name, zone_type=zone_type)
        self.add_zones(zone)
        self.updated_at = datetime.now(UTC)
        self.raise_(
            ZoneAdded(
                warehouse_id=str(self.id),
                zone_id=zone_id,
                zone_name=zone_name,
                zone_type=zone_type,
                added_at=self.updated_at,
            )
        )

    def remove_zone(self, zone_id):
        """Remove a zone from the warehouse."""
        zone = next(
            (z for z in (self.zones or []) if str(z.id) == str(zone_id)),
            None,
        )
        if zone is None:
            raise ValidationError({"zone_id": ["Zone not found"]})
        self.remove_zones(zone)
        self.updated_at = datetime.now(UTC)
        self.raise_(
            ZoneRemoved(
                warehouse_id=str(self.id),
                zone_id=str(zone_id),
                removed_at=self.updated_at,
            )
        )

    def deactivate(self):
        """Deactivate the warehouse."""
        if not self.is_active:
            raise ValidationError({"warehouse": ["Warehouse is already inactive"]})
        self.is_active = False
        self.updated_at = datetime.now(UTC)
        self.raise_(
            WarehouseDeactivated(
                warehouse_id=str(self.id),
                deactivated_at=self.updated_at,
            )
        )
