"""Low stock report — items below reorder point for purchasing alerts."""

from protean.core.projector import on
from protean.fields import Boolean, DateTime, Identifier, Integer, String
from protean.utils.globals import current_domain

from inventory.domain import inventory
from inventory.stock.events import LowStockDetected, StockReceived, StockReturned
from inventory.stock.stock import InventoryItem


@inventory.projection
class LowStockReport:
    inventory_item_id = Identifier(identifier=True, required=True)
    product_id = Identifier(required=True)
    variant_id = Identifier(required=True)
    sku = String(required=True)
    current_available = Integer(default=0)
    reorder_point = Integer(default=10)
    is_critical = Boolean(default=False)  # available == 0
    detected_at = DateTime()


@inventory.projector(projector_for=LowStockReport, aggregates=[InventoryItem])
class LowStockReportProjector:
    @on(LowStockDetected)
    def on_low_stock_detected(self, event):
        repo = current_domain.repository_for(LowStockReport)
        try:
            report = repo.get(event.inventory_item_id)
            report.current_available = event.current_available
            report.is_critical = event.current_available == 0
            report.detected_at = event.detected_at
        except Exception:
            report = LowStockReport(
                inventory_item_id=event.inventory_item_id,
                product_id=event.product_id,
                variant_id=event.variant_id,
                sku=event.sku,
                current_available=event.current_available,
                reorder_point=event.reorder_point,
                is_critical=event.current_available == 0,
                detected_at=event.detected_at,
            )
        repo.add(report)

    @on(StockReceived)
    def on_stock_received(self, event):
        """Remove from low stock report if restocked above threshold."""
        repo = current_domain.repository_for(LowStockReport)
        try:
            report = repo.get(event.inventory_item_id)
        except Exception:
            return  # Not in the report

        # Use event's new_available and report's stored reorder_point
        if event.new_available > report.reorder_point:
            repo._dao.delete(report)
        else:
            report.current_available = event.new_available
            report.is_critical = event.new_available == 0
            repo.add(report)

    @on(StockReturned)
    def on_stock_returned(self, event):
        """Remove from low stock report if returns bring stock above threshold."""
        repo = current_domain.repository_for(LowStockReport)
        try:
            report = repo.get(event.inventory_item_id)
        except Exception:
            return

        if event.new_available > report.reorder_point:
            repo._dao.delete(report)
        else:
            report.current_available = event.new_available
            report.is_critical = event.new_available == 0
            repo.add(report)
