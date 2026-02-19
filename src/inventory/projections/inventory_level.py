"""Inventory level — per-item stock levels for real-time display."""

from protean.core.projector import on
from protean.fields import DateTime, Identifier, Integer, String
from protean.utils.globals import current_domain

from inventory.domain import inventory
from inventory.stock.events import (
    DamagedStockWrittenOff,
    ReservationReleased,
    StockAdjusted,
    StockCommitted,
    StockInitialized,
    StockMarkedDamaged,
    StockReceived,
    StockReserved,
    StockReturned,
)
from inventory.stock.stock import InventoryItem


@inventory.projection
class InventoryLevel:
    inventory_item_id = Identifier(identifier=True, required=True)
    product_id = Identifier(required=True)
    variant_id = Identifier(required=True)
    warehouse_id = Identifier(required=True)
    sku = String(required=True)
    on_hand = Integer(default=0)
    reserved = Integer(default=0)
    available = Integer(default=0)
    in_transit = Integer(default=0)
    damaged = Integer(default=0)
    reorder_point = Integer(default=10)
    updated_at = DateTime()


@inventory.projector(projector_for=InventoryLevel, aggregates=[InventoryItem])
class InventoryLevelProjector:
    @on(StockInitialized)
    def on_stock_initialized(self, event):
        current_domain.repository_for(InventoryLevel).add(
            InventoryLevel(
                inventory_item_id=event.inventory_item_id,
                product_id=event.product_id,
                variant_id=event.variant_id,
                warehouse_id=event.warehouse_id,
                sku=event.sku,
                on_hand=event.initial_quantity,
                reserved=0,
                available=event.initial_quantity,
                in_transit=0,
                damaged=0,
                reorder_point=event.reorder_point,
                updated_at=event.initialized_at,
            )
        )

    @on(StockReceived)
    def on_stock_received(self, event):
        repo = current_domain.repository_for(InventoryLevel)
        level = repo.get(event.inventory_item_id)
        level.on_hand = event.new_on_hand
        level.available = event.new_available
        level.updated_at = event.received_at
        repo.add(level)

    @on(StockReserved)
    def on_stock_reserved(self, event):
        repo = current_domain.repository_for(InventoryLevel)
        level = repo.get(event.inventory_item_id)
        level.reserved = level.reserved + event.quantity
        level.available = event.new_available
        level.updated_at = event.reserved_at
        repo.add(level)

    @on(ReservationReleased)
    def on_reservation_released(self, event):
        repo = current_domain.repository_for(InventoryLevel)
        level = repo.get(event.inventory_item_id)
        level.reserved = level.reserved - event.quantity
        level.available = event.new_available
        level.updated_at = event.released_at
        repo.add(level)

    @on(StockCommitted)
    def on_stock_committed(self, event):
        repo = current_domain.repository_for(InventoryLevel)
        level = repo.get(event.inventory_item_id)
        level.on_hand = event.new_on_hand
        level.reserved = event.new_reserved
        level.available = event.new_on_hand - event.new_reserved
        level.updated_at = event.committed_at
        repo.add(level)

    @on(StockAdjusted)
    def on_stock_adjusted(self, event):
        repo = current_domain.repository_for(InventoryLevel)
        level = repo.get(event.inventory_item_id)
        level.on_hand = event.new_on_hand
        level.available = event.new_available
        level.updated_at = event.adjusted_at
        repo.add(level)

    @on(StockMarkedDamaged)
    def on_stock_marked_damaged(self, event):
        repo = current_domain.repository_for(InventoryLevel)
        level = repo.get(event.inventory_item_id)
        level.on_hand = event.new_on_hand
        level.available = event.new_available
        level.damaged = event.new_damaged
        level.updated_at = event.marked_at
        repo.add(level)

    @on(DamagedStockWrittenOff)
    def on_damaged_stock_written_off(self, event):
        repo = current_domain.repository_for(InventoryLevel)
        level = repo.get(event.inventory_item_id)
        level.damaged = event.new_damaged
        level.updated_at = event.written_off_at
        repo.add(level)

    @on(StockReturned)
    def on_stock_returned(self, event):
        repo = current_domain.repository_for(InventoryLevel)
        level = repo.get(event.inventory_item_id)
        level.on_hand = event.new_on_hand
        level.available = event.new_available
        level.updated_at = event.returned_at
        repo.add(level)
