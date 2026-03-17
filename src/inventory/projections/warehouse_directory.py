"""Warehouse directory — a listing of all warehouses with their details."""

from protean.core.projector import on
from protean.fields import Boolean, DateTime, Identifier, Integer, String
from protean.utils.globals import current_domain

from inventory.domain import inventory
from inventory.warehouse.events import (
    WarehouseCreated,
    WarehouseDeactivated,
    WarehouseUpdated,
    ZoneAdded,
    ZoneRemoved,
)
from inventory.warehouse.warehouse import Warehouse


@inventory.projection
class WarehouseDirectory:
    warehouse_id = Identifier(identifier=True, required=True)
    name = String(required=True)
    city = String()
    country = String()
    capacity = Integer(default=0)
    zone_count = Integer(default=0)
    is_active = Boolean(default=True)
    created_at = DateTime()
    updated_at = DateTime()


@inventory.projector(projector_for=WarehouseDirectory, aggregates=[Warehouse])
class WarehouseDirectoryProjector:
    @on(WarehouseCreated)
    def on_warehouse_created(self, event):
        address = event.address or {}
        current_domain.repository_for(WarehouseDirectory).add(
            WarehouseDirectory(
                warehouse_id=event.warehouse_id,
                name=event.name,
                city=address.get("city", ""),
                country=address.get("country", ""),
                capacity=int(event.capacity) if event.capacity else 0,
                zone_count=0,
                is_active=True,
                created_at=event.created_at,
                updated_at=event.created_at,
            )
        )

    @on(WarehouseUpdated)
    def on_warehouse_updated(self, event):
        repo = current_domain.repository_for(WarehouseDirectory)
        view = repo.get(event.warehouse_id)
        view.name = event.name
        view.capacity = int(event.capacity) if event.capacity else view.capacity
        view.updated_at = event.updated_at
        repo.add(view)

    @on(ZoneAdded)
    def on_zone_added(self, event):
        repo = current_domain.repository_for(WarehouseDirectory)
        view = repo.get(event.warehouse_id)
        view.zone_count = (view.zone_count or 0) + 1
        view.updated_at = event.added_at
        repo.add(view)

    @on(ZoneRemoved)
    def on_zone_removed(self, event):
        repo = current_domain.repository_for(WarehouseDirectory)
        view = repo.get(event.warehouse_id)
        view.zone_count = max((view.zone_count or 0) - 1, 0)
        view.updated_at = event.removed_at
        repo.add(view)

    @on(WarehouseDeactivated)
    def on_warehouse_deactivated(self, event):
        repo = current_domain.repository_for(WarehouseDirectory)
        view = repo.get(event.warehouse_id)
        view.is_active = False
        view.updated_at = event.deactivated_at
        repo.add(view)
