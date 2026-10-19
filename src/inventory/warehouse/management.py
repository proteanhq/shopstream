"""Warehouse management — commands and handler."""

from typing import Any

from protean import handle
from protean.fields import Dict, Identifier, Integer, String
from protean.utils.globals import current_domain

from inventory.domain import inventory
from inventory.warehouse.warehouse import Warehouse


@inventory.command(part_of="Warehouse")
class CreateWarehouse:
    """Create a new warehouse."""

    name: str = String(required=True, max_length=255)
    address: dict[str, Any] = Dict(required=True)
    capacity: int = Integer(default=0)


@inventory.command(part_of="Warehouse")
class UpdateWarehouse:
    """Update warehouse details."""

    warehouse_id: str = Identifier(required=True)
    name: str | None = String(max_length=255)
    capacity: int | None = Integer()


@inventory.command(part_of="Warehouse")
class AddZone:
    """Add a zone to a warehouse."""

    warehouse_id: str = Identifier(required=True)
    zone_name: str = String(required=True, max_length=100)
    zone_type: str | None = String(max_length=50)


@inventory.command(part_of="Warehouse")
class RemoveZone:
    """Remove a zone from a warehouse."""

    warehouse_id: str = Identifier(required=True)
    zone_id: str = Identifier(required=True)


@inventory.command(part_of="Warehouse")
class DeactivateWarehouse:
    """Deactivate a warehouse."""

    warehouse_id: str = Identifier(required=True)


@inventory.command_handler(part_of=Warehouse)
class WarehouseManagementHandler:
    @handle(CreateWarehouse)
    def create_warehouse(self, command: CreateWarehouse) -> str:
        warehouse = Warehouse.create(
            name=command.name,
            address=command.address,
            capacity=command.capacity or 0,
        )
        current_domain.repository_for(Warehouse).add(warehouse)
        return str(warehouse.id)

    @handle(UpdateWarehouse)
    def update_warehouse(self, command: UpdateWarehouse) -> None:
        repo = current_domain.repository_for(Warehouse)
        warehouse = repo.get(command.warehouse_id)
        warehouse.update_details(
            name=command.name,
            capacity=command.capacity,
        )
        repo.add(warehouse)

    @handle(AddZone)
    def add_zone(self, command: AddZone) -> None:
        repo = current_domain.repository_for(Warehouse)
        warehouse = repo.get(command.warehouse_id)
        warehouse.add_zone(
            zone_name=command.zone_name,
            zone_type=command.zone_type or "Regular",
        )
        repo.add(warehouse)

    @handle(RemoveZone)
    def remove_zone(self, command: RemoveZone) -> None:
        repo = current_domain.repository_for(Warehouse)
        warehouse = repo.get(command.warehouse_id)
        warehouse.remove_zone(zone_id=command.zone_id)
        repo.add(warehouse)

    @handle(DeactivateWarehouse)
    def deactivate_warehouse(self, command: DeactivateWarehouse) -> None:
        repo = current_domain.repository_for(Warehouse)
        warehouse = repo.get(command.warehouse_id)
        warehouse.deactivate()
        repo.add(warehouse)
