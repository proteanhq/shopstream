"""Warehouse aggregate (CQRS) — physical location where inventory is stored.

Warehouses contain zones (regular, cold storage, hazmat) and track capacity.
This is a standard CQRS aggregate (not event sourced).
"""

from datetime import UTC, datetime
from enum import Enum
from typing import Any
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

    street: str = String(required=True, max_length=255)
    city: str = String(required=True, max_length=100)
    state: str | None = String(max_length=100)
    postal_code: str = String(required=True, max_length=20)
    country: str = String(required=True, max_length=100)


@inventory.entity(part_of="Warehouse")
class Zone:
    """A logical area within a warehouse (e.g., cold storage, hazmat)."""

    zone_name: str = String(required=True, max_length=100)
    zone_type: str = String(
        choices=ZoneType,
        default=ZoneType.REGULAR.value,
    )


@inventory.aggregate
class Warehouse:
    """A physical location where inventory is stored."""

    name: str = String(required=True, max_length=255)
    address: WarehouseAddress | None = ValueObject(WarehouseAddress)
    capacity: int = Integer(default=0)
    is_active: bool = Boolean(default=True)
    zones: list[Zone] = HasMany(Zone)
    created_at: datetime | None = DateTime()
    updated_at: datetime | None = DateTime()

    @classmethod
    def create(cls, name: str, address: dict[str, Any] | WarehouseAddress, capacity: int = 0) -> "Warehouse":
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
                address=address if isinstance(address, dict) else address.to_dict(),
                capacity=capacity,
                created_at=now,
            )
        )
        return warehouse

    def update_details(self, name: str | None = None, capacity: int | None = None) -> None:
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
                capacity=self.capacity,
                updated_at=self.updated_at,
            )
        )

    def add_zone(self, zone_name: str, zone_type: str = ZoneType.REGULAR.value) -> None:
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

    def remove_zone(self, zone_id: str) -> None:
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

    def deactivate(self) -> None:
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
