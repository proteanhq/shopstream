"""Domain events for the Warehouse aggregate."""

from protean.fields import DateTime, Dict, Identifier, String

from inventory.domain import inventory


@inventory.event(part_of="Warehouse")
class WarehouseCreated:
    """A new warehouse was created."""

    warehouse_id = Identifier(required=True)
    name = String(required=True)
    address = Dict(required=True)
    capacity = Identifier(required=True)  # Stored as string to avoid Integer(0) issue
    created_at = DateTime(required=True)


@inventory.event(part_of="Warehouse")
class WarehouseUpdated:
    """Warehouse details were updated."""

    warehouse_id = Identifier(required=True)
    name = String(required=True)
    capacity = Identifier(required=True)
    updated_at = DateTime(required=True)


@inventory.event(part_of="Warehouse")
class ZoneAdded:
    """A zone was added to a warehouse."""

    warehouse_id = Identifier(required=True)
    zone_id = Identifier(required=True)
    zone_name = String(required=True)
    zone_type = String(required=True)
    added_at = DateTime(required=True)


@inventory.event(part_of="Warehouse")
class ZoneRemoved:
    """A zone was removed from a warehouse."""

    warehouse_id = Identifier(required=True)
    zone_id = Identifier(required=True)
    removed_at = DateTime(required=True)


@inventory.event(part_of="Warehouse")
class WarehouseDeactivated:
    """A warehouse was deactivated."""

    warehouse_id = Identifier(required=True)
    deactivated_at = DateTime(required=True)
