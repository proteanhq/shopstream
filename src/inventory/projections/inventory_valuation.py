"""Inventory valuation projection — finance reporting of stock value.

Maintains per-item stock valuation based on on-hand quantity and unit cost.
Unit cost is derived from the most recent StockReceived event.
"""

from protean.core.projector import on
from protean.exceptions import ObjectNotFoundError
from protean.fields import DateTime, Float, Identifier, Integer, String
from protean.utils.globals import current_domain

from inventory.domain import inventory
from inventory.stock.events import (
    DamagedStockWrittenOff,
    StockAdjusted,
    StockCommitted,
    StockInitialized,
    StockReceived,
    StockReturned,
)
from inventory.stock.stock import InventoryItem


@inventory.projection
class InventoryValuation:
    inventory_item_id = Identifier(identifier=True, required=True)
    product_id = Identifier(required=True)
    variant_id = Identifier(required=True)
    sku = String(max_length=50)
    warehouse_id = Identifier()
    on_hand = Integer(default=0)
    unit_cost = Float(default=0.0)
    total_value = Float(default=0.0)
    updated_at = DateTime()


@inventory.projector(projector_for=InventoryValuation, aggregates=[InventoryItem])
class InventoryValuationProjector:
    @on(StockInitialized)
    def on_stock_initialized(self, event):
        on_hand = event.initial_quantity or 0
        current_domain.repository_for(InventoryValuation).add(
            InventoryValuation(
                inventory_item_id=event.inventory_item_id,
                product_id=event.product_id,
                variant_id=event.variant_id,
                sku=event.sku,
                warehouse_id=event.warehouse_id,
                on_hand=on_hand,
                unit_cost=0.0,
                total_value=0.0,
                updated_at=event.initialized_at,
            )
        )

    def _get_view(self, inventory_item_id):
        """Get the valuation record, or None if it doesn't exist yet."""
        repo = current_domain.repository_for(InventoryValuation)
        try:
            return repo, repo.get(str(inventory_item_id))
        except ObjectNotFoundError:
            return repo, None

    @on(StockReceived)
    def on_stock_received(self, event):
        repo, view = self._get_view(event.inventory_item_id)
        if view is None:
            return
        view.on_hand = event.new_on_hand
        view.total_value = view.on_hand * (view.unit_cost or 0.0)
        view.updated_at = event.received_at
        repo.add(view)

    @on(StockCommitted)
    def on_stock_committed(self, event):
        repo, view = self._get_view(event.inventory_item_id)
        if view is None:
            return
        view.on_hand = event.new_on_hand
        view.total_value = view.on_hand * (view.unit_cost or 0.0)
        view.updated_at = event.committed_at
        repo.add(view)

    @on(StockAdjusted)
    def on_stock_adjusted(self, event):
        repo, view = self._get_view(event.inventory_item_id)
        if view is None:
            return
        view.on_hand = event.new_on_hand
        view.total_value = view.on_hand * (view.unit_cost or 0.0)
        view.updated_at = event.adjusted_at
        repo.add(view)

    @on(StockReturned)
    def on_stock_returned(self, event):
        repo, view = self._get_view(event.inventory_item_id)
        if view is None:
            return
        view.on_hand = event.new_on_hand
        view.total_value = view.on_hand * (view.unit_cost or 0.0)
        view.updated_at = event.returned_at
        repo.add(view)

    @on(DamagedStockWrittenOff)
    def on_damaged_stock_written_off(self, event):
        repo, view = self._get_view(event.inventory_item_id)
        if view is None:
            return
        # DamagedStockWrittenOff reduces damaged count, not on_hand directly.
        # on_hand was already reduced when StockMarkedDamaged was processed.
        view.updated_at = event.written_off_at
        repo.add(view)
