"""Inventory valuation projection — finance reporting of stock value.

Maintains per-item stock valuation based on on-hand quantity and unit cost.
Unit cost starts at zero. No inventory event carries a unit cost yet, so
it is set on the view directly.
"""

from datetime import datetime
from decimal import Decimal as D

from protean.core.projector import on
from protean.core.repository import BaseRepository
from protean.fields import DateTime, Decimal, Identifier, Integer, String
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
from shared.money import to_money


@inventory.projection
class InventoryValuation:
    inventory_item_id: str = Identifier(identifier=True, required=True)
    product_id: str = Identifier(required=True)
    variant_id: str = Identifier(required=True)
    sku: str | None = String(max_length=50)
    warehouse_id: str | None = Identifier()
    on_hand: int = Integer(default=0)
    unit_cost: D = Decimal(precision=19, scale=4, default=D("0"))
    total_value: D = Decimal(precision=19, scale=4, default=D("0"))
    updated_at: datetime | None = DateTime()


@inventory.projector(projector_for=InventoryValuation, aggregates=[InventoryItem], idempotent=True)
class InventoryValuationProjector:
    @on(StockInitialized)
    def on_stock_initialized(self, event: StockInitialized) -> None:
        on_hand = event.initial_quantity or 0
        current_domain.repository_for(InventoryValuation).add(
            InventoryValuation(
                inventory_item_id=event.inventory_item_id,
                product_id=event.product_id,
                variant_id=event.variant_id,
                sku=event.sku,
                warehouse_id=event.warehouse_id,
                on_hand=on_hand,
                unit_cost=D("0"),
                total_value=D("0"),
                updated_at=event.initialized_at,
            )
        )

    def _get_view(self, inventory_item_id: str) -> tuple[BaseRepository, InventoryValuation | None]:
        """Get the valuation record, or None if it doesn't exist yet."""
        repo = current_domain.repository_for(InventoryValuation)
        return repo, repo.get_or_none(str(inventory_item_id))

    @on(StockReceived)
    def on_stock_received(self, event: StockReceived) -> None:
        repo, view = self._get_view(event.inventory_item_id)
        if view is None:
            return
        view.on_hand = event.new_on_hand
        view.total_value = to_money(view.on_hand * to_money(view.unit_cost))
        view.updated_at = event.received_at
        repo.add(view)

    @on(StockCommitted)
    def on_stock_committed(self, event: StockCommitted) -> None:
        repo, view = self._get_view(event.inventory_item_id)
        if view is None:
            return
        view.on_hand = event.new_on_hand
        view.total_value = to_money(view.on_hand * to_money(view.unit_cost))
        view.updated_at = event.committed_at
        repo.add(view)

    @on(StockAdjusted)
    def on_stock_adjusted(self, event: StockAdjusted) -> None:
        repo, view = self._get_view(event.inventory_item_id)
        if view is None:
            return
        view.on_hand = event.new_on_hand
        view.total_value = to_money(view.on_hand * to_money(view.unit_cost))
        view.updated_at = event.adjusted_at
        repo.add(view)

    @on(StockReturned)
    def on_stock_returned(self, event: StockReturned) -> None:
        repo, view = self._get_view(event.inventory_item_id)
        if view is None:
            return
        view.on_hand = event.new_on_hand
        view.total_value = to_money(view.on_hand * to_money(view.unit_cost))
        view.updated_at = event.returned_at
        repo.add(view)

    @on(DamagedStockWrittenOff)
    def on_damaged_stock_written_off(self, event: DamagedStockWrittenOff) -> None:
        repo, view = self._get_view(event.inventory_item_id)
        if view is None:
            return
        # DamagedStockWrittenOff reduces damaged count, not on_hand directly.
        # on_hand was already reduced when StockMarkedDamaged was processed.
        view.updated_at = event.written_off_at
        repo.add(view)
