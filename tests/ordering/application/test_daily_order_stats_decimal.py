"""DailyOrderStats keeps exact Decimal money totals.

The order events still carry money as floats, so the projector converts each
amount to a 4-place Decimal before adding it.
"""

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from protean import current_domain
from protean.utils.reflection import fields

from ordering.order.events import OrderCreated, OrderRefunded
from ordering.projections.daily_order_stats import DailyOrderStats, DailyOrderStatsProjector

_DAY = datetime(2026, 1, 15, 12, 0, tzinfo=UTC)


def _order_created(order_id, grand_total):
    return OrderCreated(
        order_id=order_id,
        customer_id="cust-001",
        items=[],
        shipping_address={},
        billing_address={},
        subtotal=grand_total,
        grand_total=grand_total,
        created_at=_DAY,
    )


def _saved_record():
    record = current_domain.repository_for(DailyOrderStats).get_or_none("2026-01-15")
    assert record is not None, "Expected the projector to persist a record for 2026-01-15"
    return record


class TestDailyOrderStatsDecimal:
    def test_revenue_of_tenths_sums_exactly(self):
        projector = DailyOrderStatsProjector()
        projector.on_order_created(_order_created("ord-dec-1", 0.1))
        projector.on_order_created(_order_created("ord-dec-2", 0.2))

        record = _saved_record()
        assert isinstance(record.total_revenue, Decimal)
        assert record.total_revenue == Decimal("0.3")

    def test_float_artifacts_in_a_grand_total_are_rounded(self):
        # 0.1 + 0.2 is 0.30000000000000004, more places than the scale-4 field accepts.
        DailyOrderStatsProjector().on_order_created(_order_created("ord-dec-3", 0.1 + 0.2))

        assert str(_saved_record().total_revenue) == "0.3000"

    @pytest.mark.parametrize("field_name", ["total_revenue", "total_refunds"])
    def test_money_fields_are_numeric_19_4(self, field_name):
        field = fields(DailyOrderStats)[field_name]
        assert (field.precision, field.scale) == (19, 4)

    def test_refunds_of_tenths_sum_exactly(self):
        projector = DailyOrderStatsProjector()
        for index, amount in enumerate((0.1, 0.2)):
            projector.on_order_refunded(
                OrderRefunded(order_id=f"ord-dec-ref-{index}", refund_amount=amount, refunded_at=_DAY)
            )

        record = _saved_record()
        assert isinstance(record.total_refunds, Decimal)
        assert record.total_refunds == Decimal("0.3")
        assert record.orders_refunded == 2
