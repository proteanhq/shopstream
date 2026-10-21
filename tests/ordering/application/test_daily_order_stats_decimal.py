"""DailyOrderStats keeps exact Decimal money totals.

The order events carry money as 4-place Decimals, and the projector adds
them with ``to_money`` on both sides.
"""

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from protean import current_domain
from protean.exceptions import ValidationError
from protean.utils.reflection import fields

from ordering.order.events import OrderCreated, OrderRefunded
from ordering.projections.daily_order_stats import DailyOrderStats, DailyOrderStatsProjector

pytestmark = pytest.mark.protean_bug(
    issue=1038,
    state="guard",
    bug=(
        "No `Decimal` field — money as `Float` loses precision. Events carry money as 4-place strings that rebuild as "
        "exact `Decimal`s; the `DailyRevenue`, `PaymentStatusView` and `DailyOrderStats` projections and the Payment "
        "`Money` value object store money as `Decimal(precision=19, scale=4)`."
    ),
)

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

    def test_the_event_rejects_an_unrounded_float_grand_total(self):
        # 0.1 + 0.2 is 0.30000000000000004, more places than the scale-4 field accepts.
        with pytest.raises(ValidationError, match="no more than 4 decimal places"):
            _order_created("ord-dec-3", 0.1 + 0.2)

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
