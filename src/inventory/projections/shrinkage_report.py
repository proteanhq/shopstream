"""Shrinkage report projection — loss analysis for inventory management.

Tracks stock adjustments, damaged items, and write-offs per inventory item.
Provides aggregate shrinkage data for loss prevention and auditing.
"""

import json

from protean.core.projector import on
from protean.exceptions import ObjectNotFoundError
from protean.fields import DateTime, Float, Identifier, Integer, String, Text
from protean.utils.globals import current_domain

from inventory.domain import inventory
from inventory.stock.events import DamagedStockWrittenOff, StockAdjusted, StockMarkedDamaged
from inventory.stock.stock import InventoryItem


@inventory.projection
class ShrinkageReport:
    inventory_item_id = Identifier(identifier=True, required=True)
    product_id = Identifier(required=True)
    sku = String(max_length=50)
    warehouse_id = Identifier()
    total_adjustments = Integer(default=0)
    total_damaged = Integer(default=0)
    total_written_off = Integer(default=0)
    total_shrinkage_value = Float(default=0.0)
    last_adjustment_at = DateTime()
    adjustment_reasons = Text(default="[]")  # JSON list of reason strings


def _get_or_create(event):
    repo = current_domain.repository_for(ShrinkageReport)
    try:
        return repo.get(str(event.inventory_item_id))
    except ObjectNotFoundError:
        record = ShrinkageReport(
            inventory_item_id=event.inventory_item_id,
            product_id=event.product_id,
            sku=getattr(event, "sku", None),
            warehouse_id=getattr(event, "warehouse_id", None),
            total_adjustments=0,
            total_damaged=0,
            total_written_off=0,
            total_shrinkage_value=0.0,
            adjustment_reasons="[]",
        )
        return record


@inventory.projector(projector_for=ShrinkageReport, aggregates=[InventoryItem])
class ShrinkageReportProjector:
    @on(StockAdjusted)
    def on_stock_adjusted(self, event):
        repo = current_domain.repository_for(ShrinkageReport)
        view = _get_or_create(event)

        # Only count negative adjustments as shrinkage
        qty_change = event.quantity_change or 0
        if qty_change < 0:
            view.total_adjustments = (view.total_adjustments or 0) + abs(qty_change)

        # Track reason
        reasons = (
            json.loads(view.adjustment_reasons)
            if isinstance(view.adjustment_reasons, str)
            else (view.adjustment_reasons or [])
        )
        reason_entry = f"{event.adjustment_type}: {event.reason}"
        reasons.append(reason_entry)
        # Keep last 100 reasons
        view.adjustment_reasons = json.dumps(reasons[-100:])

        view.last_adjustment_at = event.adjusted_at
        repo.add(view)

    @on(StockMarkedDamaged)
    def on_stock_marked_damaged(self, event):
        repo = current_domain.repository_for(ShrinkageReport)
        view = _get_or_create(event)
        view.total_damaged = (view.total_damaged or 0) + (event.quantity or 0)
        view.last_adjustment_at = event.marked_at
        repo.add(view)

    @on(DamagedStockWrittenOff)
    def on_damaged_stock_written_off(self, event):
        repo = current_domain.repository_for(ShrinkageReport)
        view = _get_or_create(event)
        view.total_written_off = (view.total_written_off or 0) + (event.quantity or 0)
        view.last_adjustment_at = event.written_off_at
        repo.add(view)
