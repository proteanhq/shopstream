"""InventoryValuation projector: handlers skip when there is no valuation row.

Covers the miss branch in _get_view, where `get_or_none` finds no row and the
handler returns without writing. Uses the real repository.
"""

from datetime import UTC, datetime

from protean import current_domain

from inventory.projections.inventory_valuation import (
    InventoryValuation,
    InventoryValuationProjector,
)
from inventory.stock.events import (
    DamagedStockWrittenOff,
    StockAdjusted,
    StockCommitted,
    StockReceived,
    StockReturned,
)


class TestInventoryValuationNotFound:
    """When _get_view finds no row, handlers return without creating one."""

    def test_stock_received_returns_when_view_not_found(self):
        projector = InventoryValuationProjector()
        event = StockReceived(
            inventory_item_id="item-missing-001",
            quantity=10,
            previous_on_hand=0,
            new_on_hand=10,
            new_available=10,
            received_at=datetime.now(UTC),
        )
        projector.on_stock_received(event)
        assert current_domain.repository_for(InventoryValuation).get_or_none(event.inventory_item_id) is None

    def test_stock_committed_returns_when_view_not_found(self):
        projector = InventoryValuationProjector()
        event = StockCommitted(
            inventory_item_id="item-missing-002",
            reservation_id="res-001",
            order_id="ord-001",
            quantity=5,
            previous_on_hand=100,
            new_on_hand=95,
            previous_reserved=5,
            new_reserved=0,
            committed_at=datetime.now(UTC),
        )
        projector.on_stock_committed(event)
        assert current_domain.repository_for(InventoryValuation).get_or_none(event.inventory_item_id) is None

    def test_stock_adjusted_returns_when_view_not_found(self):
        projector = InventoryValuationProjector()
        event = StockAdjusted(
            inventory_item_id="item-missing-003",
            product_id="prod-001",
            adjustment_type="Shrinkage",
            quantity_change=-5,
            reason="Broken items",
            adjusted_by="admin",
            previous_on_hand=100,
            new_on_hand=95,
            new_available=95,
            adjusted_at=datetime.now(UTC),
        )
        projector.on_stock_adjusted(event)
        assert current_domain.repository_for(InventoryValuation).get_or_none(event.inventory_item_id) is None

    def test_stock_returned_returns_when_view_not_found(self):
        projector = InventoryValuationProjector()
        event = StockReturned(
            inventory_item_id="item-missing-004",
            quantity=3,
            order_id="ord-002",
            previous_on_hand=90,
            new_on_hand=93,
            new_available=93,
            returned_at=datetime.now(UTC),
        )
        projector.on_stock_returned(event)
        assert current_domain.repository_for(InventoryValuation).get_or_none(event.inventory_item_id) is None

    def test_damaged_stock_written_off_returns_when_view_not_found(self):
        projector = InventoryValuationProjector()
        event = DamagedStockWrittenOff(
            inventory_item_id="item-missing-005",
            product_id="prod-002",
            quantity=2,
            approved_by="admin",
            previous_damaged=5,
            new_damaged=3,
            written_off_at=datetime.now(UTC),
        )
        projector.on_damaged_stock_written_off(event)
        assert current_domain.repository_for(InventoryValuation).get_or_none(event.inventory_item_id) is None
