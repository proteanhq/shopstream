"""DailyOrderStats projector: a miss on the day's row creates a fresh record.

Covers the miss branch in _get_or_create, where `get_or_none` finds no row for
the date and a new DailyOrderStats is built instead. Uses the real repository.
"""

from datetime import UTC, datetime

from protean import current_domain

from ordering.order.events import OrderCancelled, OrderCreated
from ordering.projections.daily_order_stats import (
    DailyOrderStats,
    DailyOrderStatsProjector,
    _get_or_create,
)

_DAY = datetime(2026, 1, 15, 12, 0, tzinfo=UTC)


def _saved_record():
    record = current_domain.repository_for(DailyOrderStats).get_or_none("2026-01-15")
    assert record is not None, "Expected the projector to persist a record for 2026-01-15"
    return record


class TestDailyOrderStatsGetOrCreate:
    """When no row exists for the date, _get_or_create builds a new, unsaved record."""

    def test_creates_new_record_when_not_found(self):
        record = _get_or_create("2026-01-15")

        assert record.date == "2026-01-15"
        assert record.orders_created == 0
        assert record.orders_completed == 0
        assert record.orders_cancelled == 0
        assert record.orders_refunded == 0
        assert record.total_revenue == 0.0
        assert record.total_refunds == 0.0
        # _get_or_create does not persist; the handler does
        assert current_domain.repository_for(DailyOrderStats).get_or_none("2026-01-15") is None

    def test_on_order_created_creates_record_when_not_found(self):
        DailyOrderStatsProjector().on_order_created(
            OrderCreated(
                order_id="ord-new-001",
                customer_id="cust-001",
                items=[],
                shipping_address={},
                billing_address={},
                subtotal=100.0,
                grand_total=110.0,
                created_at=_DAY,
            )
        )
        record = _saved_record()
        assert record.orders_created == 1
        assert record.total_revenue == 110.0

    def test_on_order_cancelled_creates_record_when_not_found(self):
        DailyOrderStatsProjector().on_order_cancelled(
            OrderCancelled(
                order_id="ord-cancel-001",
                reason="Changed mind",
                cancelled_by="Customer",
                cancelled_at=_DAY,
            )
        )
        assert _saved_record().orders_cancelled == 1

    def test_second_event_updates_existing_record(self):
        projector = DailyOrderStatsProjector()
        for n in (1, 2):
            projector.on_order_cancelled(
                OrderCancelled(
                    order_id=f"ord-cancel-upd-{n}",
                    reason="Changed mind",
                    cancelled_by="Customer",
                    cancelled_at=_DAY,
                )
            )
        assert _saved_record().orders_cancelled == 2
