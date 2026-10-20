"""Domain events for the Warehouse aggregate."""

from datetime import datetime
from typing import Any

from protean.fields import DateTime, Dict, Identifier, Integer, String

from inventory.domain import inventory


@inventory.event(part_of="Warehouse")
class WarehouseCreated:
    """A new warehouse was created."""

    warehouse_id: str = Identifier(required=True)
    name: str = String(required=True)
    address: dict[str, Any] = Dict(required=True)
    capacity: int = Integer(required=True)
    created_at: datetime = DateTime(required=True)


@inventory.event(part_of="Warehouse")
class WarehouseUpdated:
    """Warehouse details were updated."""

    warehouse_id: str = Identifier(required=True)
    name: str = String(required=True)
    capacity: int = Integer(required=True)
    updated_at: datetime = DateTime(required=True)


@inventory.event(part_of="Warehouse")
class ZoneAdded:
    """A zone was added to a warehouse."""

    warehouse_id: str = Identifier(required=True)
    zone_id: str = Identifier(required=True)
    zone_name: str = String(required=True)
    zone_type: str = String(required=True)
    added_at: datetime = DateTime(required=True)


@inventory.event(part_of="Warehouse")
class ZoneRemoved:
    """A zone was removed from a warehouse."""

    warehouse_id: str = Identifier(required=True)
    zone_id: str = Identifier(required=True)
    removed_at: datetime = DateTime(required=True)


@inventory.event(part_of="Warehouse")
class WarehouseDeactivated:
    """A warehouse was deactivated."""

    warehouse_id: str = Identifier(required=True)
    deactivated_at: datetime = DateTime(required=True)
