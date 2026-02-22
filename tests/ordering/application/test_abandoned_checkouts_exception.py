"""Mock-based tests for AbandonedCheckout projector exception branches.

Covers the ObjectNotFoundError branches in:
- on_order_confirmed (line 51): catches ObjectNotFoundError and passes
- on_order_cancelled (line 61): catches ObjectNotFoundError and passes
"""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

from ordering.order.events import OrderCancelled, OrderConfirmed
from ordering.projections.abandoned_checkouts import (
    AbandonedCheckoutProjector,
)
from protean.exceptions import ObjectNotFoundError


class TestAbandonedCheckoutNotFound:
    """When repo.get() raises ObjectNotFoundError, the handlers should pass silently."""

    def test_on_order_confirmed_passes_when_not_found(self):
        projector = AbandonedCheckoutProjector()
        event = OrderConfirmed(
            order_id="ord-missing-001",
            confirmed_at=datetime.now(UTC),
        )
        mock_repo = MagicMock()
        mock_repo.get.side_effect = ObjectNotFoundError({"_entity": "AbandonedCheckout not found"})

        with patch("ordering.projections.abandoned_checkouts.current_domain") as mock_domain:
            mock_domain.repository_for = MagicMock(return_value=mock_repo)
            # Should not raise
            projector.on_order_confirmed(event)
            # _dao.delete should NOT be called since get raised
            mock_repo._dao.delete.assert_not_called()

    def test_on_order_cancelled_passes_when_not_found(self):
        projector = AbandonedCheckoutProjector()
        event = OrderCancelled(
            order_id="ord-missing-002",
            reason="No stock",
            cancelled_by="System",
            cancelled_at=datetime.now(UTC),
        )
        mock_repo = MagicMock()
        mock_repo.get.side_effect = ObjectNotFoundError({"_entity": "AbandonedCheckout not found"})

        with patch("ordering.projections.abandoned_checkouts.current_domain") as mock_domain:
            mock_domain.repository_for = MagicMock(return_value=mock_repo)
            # Should not raise
            projector.on_order_cancelled(event)
            mock_repo._dao.delete.assert_not_called()
