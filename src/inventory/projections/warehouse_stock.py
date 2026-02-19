"""Warehouse stock — per-warehouse summary for dashboard."""

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
class WarehouseStock:
    entry_id = Identifier(identifier=True, required=True)  # Same as inventory_item_id
    warehouse_id = Identifier(required=True)
    product_id = Identifier(required=True)
    variant_id = Identifier(required=True)
    sku = String(required=True)
    on_hand = Integer(default=0)
    reserved = Integer(default=0)
    available = Integer(default=0)
    damaged = Integer(default=0)
    updated_at = DateTime()


@inventory.projector(projector_for=WarehouseStock, aggregates=[InventoryItem])
class WarehouseStockProjector:
    @on(StockInitialized)
    def on_stock_initialized(self, event):
        current_domain.repository_for(WarehouseStock).add(
            WarehouseStock(
                entry_id=event.inventory_item_id,
                warehouse_id=event.warehouse_id,
                product_id=event.product_id,
                variant_id=event.variant_id,
                sku=event.sku,
                on_hand=event.initial_quantity,
                reserved=0,
                available=event.initial_quantity,
                damaged=0,
                updated_at=event.initialized_at,
            )
        )

    @on(StockReceived)
    def on_stock_received(self, event):
        repo = current_domain.repository_for(WarehouseStock)
        ws = repo.get(event.inventory_item_id)
        ws.on_hand = event.new_on_hand
        ws.available = event.new_available
        ws.updated_at = event.received_at
        repo.add(ws)

    @on(StockReserved)
    def on_stock_reserved(self, event):
        repo = current_domain.repository_for(WarehouseStock)
        ws = repo.get(event.inventory_item_id)
        ws.reserved = ws.reserved + event.quantity
        ws.available = event.new_available
        ws.updated_at = event.reserved_at
        repo.add(ws)

    @on(ReservationReleased)
    def on_reservation_released(self, event):
        repo = current_domain.repository_for(WarehouseStock)
        ws = repo.get(event.inventory_item_id)
        ws.reserved = ws.reserved - event.quantity
        ws.available = event.new_available
        ws.updated_at = event.released_at
        repo.add(ws)

    @on(StockCommitted)
    def on_stock_committed(self, event):
        repo = current_domain.repository_for(WarehouseStock)
        ws = repo.get(event.inventory_item_id)
        ws.on_hand = event.new_on_hand
        ws.reserved = event.new_reserved
        ws.available = event.new_on_hand - event.new_reserved
        ws.updated_at = event.committed_at
        repo.add(ws)

    @on(StockAdjusted)
    def on_stock_adjusted(self, event):
        repo = current_domain.repository_for(WarehouseStock)
        ws = repo.get(event.inventory_item_id)
        ws.on_hand = event.new_on_hand
        ws.available = event.new_available
        ws.updated_at = event.adjusted_at
        repo.add(ws)

    @on(StockMarkedDamaged)
    def on_stock_marked_damaged(self, event):
        repo = current_domain.repository_for(WarehouseStock)
        ws = repo.get(event.inventory_item_id)
        ws.on_hand = event.new_on_hand
        ws.available = event.new_available
        ws.damaged = event.new_damaged
        ws.updated_at = event.marked_at
        repo.add(ws)

    @on(DamagedStockWrittenOff)
    def on_damaged_stock_written_off(self, event):
        repo = current_domain.repository_for(WarehouseStock)
        ws = repo.get(event.inventory_item_id)
        ws.damaged = event.new_damaged
        ws.updated_at = event.written_off_at
        repo.add(ws)

    @on(StockReturned)
    def on_stock_returned(self, event):
        repo = current_domain.repository_for(WarehouseStock)
        ws = repo.get(event.inventory_item_id)
        ws.on_hand = event.new_on_hand
        ws.available = event.new_available
        ws.updated_at = event.returned_at
        repo.add(ws)
