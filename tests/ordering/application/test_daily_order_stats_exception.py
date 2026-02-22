"""Mock-based tests for DailyOrderStats projector exception branches.

Covers the ObjectNotFoundError branch in _get_or_create (line 37) where
repo.get() fails and a new DailyOrderStats record is created instead.
"""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

from ordering.order.events import OrderCancelled, OrderCreated
from ordering.projections.daily_order_stats import (
    DailyOrderStatsProjector,
    _get_or_create,
)
from protean.exceptions import ObjectNotFoundError


class TestDailyOrderStatsGetOrCreate:
    """When _get_or_create encounters ObjectNotFoundError, it should create a new record."""

    def test_creates_new_record_when_not_found(self):
        mock_repo = MagicMock()
        mock_repo.get.side_effect = ObjectNotFoundError({"_entity": "DailyOrderStats not found"})

        with patch("ordering.projections.daily_order_stats.current_domain") as mock_domain:
            mock_domain.repository_for = MagicMock(return_value=mock_repo)
            record = _get_or_create("2026-01-15")

        assert record is not None
        assert record.date == "2026-01-15"
        assert record.orders_created == 0
        assert record.orders_completed == 0
        assert record.orders_cancelled == 0
        assert record.orders_refunded == 0
        assert record.total_revenue == 0.0
        assert record.total_refunds == 0.0
        mock_repo.add.assert_not_called()

    def test_on_order_created_creates_record_when_not_found(self):
        projector = DailyOrderStatsProjector()
        event = OrderCreated(
            order_id="ord-new-001",
            customer_id="cust-001",
            items="[]",
            shipping_address="{}",
            billing_address="{}",
            subtotal=100.0,
            grand_total=110.0,
            created_at=datetime.now(UTC),
        )
        mock_repo = MagicMock()
        mock_repo.get.side_effect = ObjectNotFoundError({"_entity": "DailyOrderStats not found"})

        with patch("ordering.projections.daily_order_stats.current_domain") as mock_domain:
            mock_domain.repository_for = MagicMock(return_value=mock_repo)
            projector.on_order_created(event)
            # Only the handler calls repo.add (not _get_or_create)
            mock_repo.add.assert_called_once()

    def test_on_order_cancelled_creates_record_when_not_found(self):
        projector = DailyOrderStatsProjector()
        event = OrderCancelled(
            order_id="ord-cancel-001",
            reason="Changed mind",
            cancelled_by="Customer",
            cancelled_at=datetime.now(UTC),
        )
        mock_repo = MagicMock()
        mock_repo.get.side_effect = ObjectNotFoundError({"_entity": "DailyOrderStats not found"})

        with patch("ordering.projections.daily_order_stats.current_domain") as mock_domain:
            mock_domain.repository_for = MagicMock(return_value=mock_repo)
            projector.on_order_cancelled(event)
            mock_repo.add.assert_called_once()
