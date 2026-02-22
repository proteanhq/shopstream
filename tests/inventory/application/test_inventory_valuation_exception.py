"""Mock-based tests for InventoryValuation projector exception branches.

Covers the ObjectNotFoundError branch in _get_view (line 56) where repo.get()
fails and returns (repo, None), causing the handler to return early.
"""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

from inventory.projections.inventory_valuation import (
    InventoryValuationProjector,
)
from inventory.stock.events import (
    DamagedStockWrittenOff,
    StockAdjusted,
    StockCommitted,
    StockReceived,
    StockReturned,
)
from protean.exceptions import ObjectNotFoundError


class TestInventoryValuationNotFound:
    """When _get_view raises ObjectNotFoundError, handlers should return gracefully."""

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
        mock_repo = MagicMock()
        mock_repo.get.side_effect = ObjectNotFoundError({"_entity": "InventoryValuation not found"})
        with patch("inventory.projections.inventory_valuation.current_domain") as mock_domain:
            mock_domain.repository_for = MagicMock(return_value=mock_repo)
            # Should not raise
            projector.on_stock_received(event)
            # repo.add should NOT be called since view is None
            mock_repo.add.assert_not_called()

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
        mock_repo = MagicMock()
        mock_repo.get.side_effect = ObjectNotFoundError({"_entity": "InventoryValuation not found"})
        with patch("inventory.projections.inventory_valuation.current_domain") as mock_domain:
            mock_domain.repository_for = MagicMock(return_value=mock_repo)
            projector.on_stock_committed(event)
            mock_repo.add.assert_not_called()

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
        mock_repo = MagicMock()
        mock_repo.get.side_effect = ObjectNotFoundError({"_entity": "InventoryValuation not found"})
        with patch("inventory.projections.inventory_valuation.current_domain") as mock_domain:
            mock_domain.repository_for = MagicMock(return_value=mock_repo)
            projector.on_stock_adjusted(event)
            mock_repo.add.assert_not_called()

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
        mock_repo = MagicMock()
        mock_repo.get.side_effect = ObjectNotFoundError({"_entity": "InventoryValuation not found"})
        with patch("inventory.projections.inventory_valuation.current_domain") as mock_domain:
            mock_domain.repository_for = MagicMock(return_value=mock_repo)
            projector.on_stock_returned(event)
            mock_repo.add.assert_not_called()

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
        mock_repo = MagicMock()
        mock_repo.get.side_effect = ObjectNotFoundError({"_entity": "InventoryValuation not found"})
        with patch("inventory.projections.inventory_valuation.current_domain") as mock_domain:
            mock_domain.repository_for = MagicMock(return_value=mock_repo)
            projector.on_damaged_stock_written_off(event)
            mock_repo.add.assert_not_called()
