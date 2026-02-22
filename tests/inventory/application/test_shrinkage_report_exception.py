"""Mock-based tests for ShrinkageReport projector exception branches.

Covers the ObjectNotFoundError branch in _get_or_create (line 34) where
repo.get() fails and a new ShrinkageReport record is created instead.
"""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

from inventory.projections.shrinkage_report import (
    ShrinkageReportProjector,
    _get_or_create,
)
from inventory.stock.events import DamagedStockWrittenOff, StockAdjusted, StockMarkedDamaged
from protean.exceptions import ObjectNotFoundError


class TestShrinkageReportGetOrCreate:
    """When _get_or_create encounters ObjectNotFoundError, it should create a new record."""

    def test_creates_new_record_when_not_found(self):
        mock_repo = MagicMock()
        mock_repo.get.side_effect = ObjectNotFoundError({"_entity": "ShrinkageReport not found"})
        mock_event = MagicMock()
        mock_event.inventory_item_id = "item-new-001"
        mock_event.product_id = "prod-001"
        mock_event.sku = "SKU-001"
        mock_event.warehouse_id = "wh-001"

        with patch("inventory.projections.shrinkage_report.current_domain") as mock_domain:
            mock_domain.repository_for = MagicMock(return_value=mock_repo)
            record = _get_or_create(mock_event)

        assert record is not None
        assert record.inventory_item_id == "item-new-001"
        assert record.product_id == "prod-001"
        assert record.total_adjustments == 0
        assert record.total_damaged == 0
        assert record.total_written_off == 0
        assert record.total_shrinkage_value == 0.0
        # _get_or_create returns a new record without calling repo.add;
        # the caller's repo.add handles both insert and update
        mock_repo.add.assert_not_called()

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
        mock_repo = MagicMock()
        mock_repo.get.side_effect = ObjectNotFoundError({"_entity": "ShrinkageReport not found"})

        with patch("inventory.projections.shrinkage_report.current_domain") as mock_domain:
            mock_domain.repository_for = MagicMock(return_value=mock_repo)
            # Should not raise; creates a new record then the handler adds it
            projector.on_stock_adjusted(event)
            # repo.add called once by the handler (not by _get_or_create)
            mock_repo.add.assert_called_once()

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
        mock_repo = MagicMock()
        mock_repo.get.side_effect = ObjectNotFoundError({"_entity": "ShrinkageReport not found"})

        with patch("inventory.projections.shrinkage_report.current_domain") as mock_domain:
            mock_domain.repository_for = MagicMock(return_value=mock_repo)
            projector.on_stock_marked_damaged(event)
            mock_repo.add.assert_called_once()

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
        mock_repo = MagicMock()
        mock_repo.get.side_effect = ObjectNotFoundError({"_entity": "ShrinkageReport not found"})

        with patch("inventory.projections.shrinkage_report.current_domain") as mock_domain:
            mock_domain.repository_for = MagicMock(return_value=mock_repo)
            projector.on_damaged_stock_written_off(event)
            mock_repo.add.assert_called_once()
