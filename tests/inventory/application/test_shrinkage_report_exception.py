"""ShrinkageReport projector: a miss on the item's row creates a fresh record.

Covers the miss branch in _get_or_create, where `get_or_none` finds no row and a
new ShrinkageReport is built instead. Uses the real repository.
"""

from datetime import UTC, datetime

from protean import current_domain

from inventory.projections.shrinkage_report import (
    ShrinkageReport,
    ShrinkageReportProjector,
    _get_or_create,
)
from inventory.stock.events import DamagedStockWrittenOff, StockAdjusted, StockMarkedDamaged


class TestShrinkageReportGetOrCreate:
    """When no row exists for the item, _get_or_create builds a new record."""

    def test_creates_new_record_when_not_found(self):
        event = StockMarkedDamaged(
            inventory_item_id="item-new-001",
            product_id="prod-001",
            quantity=1,
            reason="Dropped",
            previous_on_hand=10,
            new_on_hand=9,
            previous_damaged=0,
            new_damaged=1,
            new_available=9,
            marked_at=datetime.now(UTC),
        )

        record = _get_or_create(event)

        assert record.inventory_item_id == "item-new-001"
        assert record.product_id == "prod-001"
        assert record.total_adjustments == 0
        assert record.total_damaged == 0
        assert record.total_written_off == 0
        assert record.total_shrinkage_value == 0.0
        # _get_or_create returns a new record without saving it;
        # the caller's repo.add handles both insert and update
        assert current_domain.repository_for(ShrinkageReport).get_or_none("item-new-001") is None

    def test_stock_adjusted_creates_record_when_not_found(self):
        projector = ShrinkageReportProjector()
        event = StockAdjusted(
            inventory_item_id="item-new-002",
            product_id="prod-002",
            adjustment_type="Shrinkage",
            quantity_change=-3,
            reason="Missing items",
            adjusted_by="admin",
            previous_on_hand=50,
            new_on_hand=47,
            new_available=47,
            adjusted_at=datetime.now(UTC),
        )
        projector.on_stock_adjusted(event)

        record = current_domain.repository_for(ShrinkageReport).get_or_none(event.inventory_item_id)
        assert record is not None
        assert record.product_id == event.product_id
        assert record.total_adjustments == 3

    def test_stock_marked_damaged_creates_record_when_not_found(self):
        projector = ShrinkageReportProjector()
        event = StockMarkedDamaged(
            inventory_item_id="item-new-003",
            product_id="prod-003",
            quantity=2,
            reason="Water damage",
            previous_on_hand=40,
            new_on_hand=38,
            previous_damaged=0,
            new_damaged=2,
            new_available=38,
            marked_at=datetime.now(UTC),
        )
        projector.on_stock_marked_damaged(event)

        record = current_domain.repository_for(ShrinkageReport).get_or_none(event.inventory_item_id)
        assert record is not None
        assert record.product_id == event.product_id
        assert record.total_damaged == 2

    def test_damaged_written_off_creates_record_when_not_found(self):
        projector = ShrinkageReportProjector()
        event = DamagedStockWrittenOff(
            inventory_item_id="item-new-004",
            product_id="prod-004",
            quantity=1,
            approved_by="manager",
            previous_damaged=3,
            new_damaged=2,
            written_off_at=datetime.now(UTC),
        )
        projector.on_damaged_stock_written_off(event)

        record = current_domain.repository_for(ShrinkageReport).get_or_none(event.inventory_item_id)
        assert record is not None
        assert record.product_id == event.product_id
        assert record.total_written_off == 1
