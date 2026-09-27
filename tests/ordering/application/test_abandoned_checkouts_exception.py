"""AbandonedCheckout projector: confirm and cancel skip when there is no row.

Covers the miss branches in on_order_confirmed and on_order_cancelled, where
`get_or_none` finds no row and the handler does nothing. Uses the real repository.
"""

from datetime import UTC, datetime

from protean import current_domain

from ordering.order.events import OrderCancelled, OrderConfirmed
from ordering.projections.abandoned_checkouts import (
    AbandonedCheckout,
    AbandonedCheckoutProjector,
)


class TestAbandonedCheckoutNotFound:
    """When no row exists for the order, the handlers return without error."""

    def test_on_order_confirmed_passes_when_not_found(self):
        AbandonedCheckoutProjector().on_order_confirmed(
            OrderConfirmed(order_id="ord-missing-001", confirmed_at=datetime.now(UTC))
        )
        assert current_domain.repository_for(AbandonedCheckout).get_or_none("ord-missing-001") is None

    def test_on_order_cancelled_passes_when_not_found(self):
        AbandonedCheckoutProjector().on_order_cancelled(
            OrderCancelled(
                order_id="ord-missing-002",
                reason="No stock",
                cancelled_by="System",
                cancelled_at=datetime.now(UTC),
            )
        )
        assert current_domain.repository_for(AbandonedCheckout).get_or_none("ord-missing-002") is None


class TestAbandonedCheckoutFound:
    """When a row exists for the order, confirm and cancel delete it."""

    def _seed(self, order_id):
        repo = current_domain.repository_for(AbandonedCheckout)
        repo.add(AbandonedCheckout(order_id=order_id, customer_id="cust-ac-001"))
        assert repo.get_or_none(order_id) is not None
        return repo

    def test_on_order_confirmed_deletes_existing_row(self):
        repo = self._seed("ord-ac-001")
        AbandonedCheckoutProjector().on_order_confirmed(
            OrderConfirmed(order_id="ord-ac-001", confirmed_at=datetime.now(UTC))
        )
        assert repo.get_or_none("ord-ac-001") is None

    def test_on_order_cancelled_deletes_existing_row(self):
        repo = self._seed("ord-ac-002")
        AbandonedCheckoutProjector().on_order_cancelled(
            OrderCancelled(
                order_id="ord-ac-002",
                reason="No stock",
                cancelled_by="System",
                cancelled_at=datetime.now(UTC),
            )
        )
        assert repo.get_or_none("ord-ac-002") is None
