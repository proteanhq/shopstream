"""Daily order stats projection — analytics dashboard for order metrics.

Maintains daily aggregated counts of orders created, completed, cancelled,
and refunded, along with revenue totals. Keyed by date (YYYY-MM-DD).
"""

from decimal import Decimal as D

from protean.core.projector import on
from protean.fields import Decimal, Integer, String
from protean.utils.globals import current_domain

from ordering.domain import ordering
from ordering.order.events import (
    OrderCancelled,
    OrderCompleted,
    OrderCreated,
    OrderRefunded,
)
from ordering.order.order import Order
from shared.money import to_money


@ordering.projection
class DailyOrderStats:
    date: str = String(identifier=True, required=True, max_length=10)  # YYYY-MM-DD
    orders_created: int = Integer(default=0)
    orders_completed: int = Integer(default=0)
    orders_cancelled: int = Integer(default=0)
    orders_refunded: int = Integer(default=0)
    total_revenue: D = Decimal(precision=19, scale=4, default=D("0"))
    total_refunds: D = Decimal(precision=19, scale=4, default=D("0"))


def _get_or_create(date_key: str) -> DailyOrderStats:
    repo = current_domain.repository_for(DailyOrderStats)
    record: DailyOrderStats | None = repo.get_or_none(date_key)
    if record is not None:
        return record
    return DailyOrderStats(
        date=date_key,
        orders_created=0,
        orders_completed=0,
        orders_cancelled=0,
        orders_refunded=0,
        total_revenue=D("0"),
        total_refunds=D("0"),
    )


@ordering.projector(projector_for=DailyOrderStats, aggregates=[Order])
class DailyOrderStatsProjector:
    @on(OrderCreated)
    def on_order_created(self, event: OrderCreated) -> None:
        date_key = event.created_at.date().isoformat()
        record = _get_or_create(date_key)
        record.orders_created = (record.orders_created or 0) + 1
        record.total_revenue = to_money(record.total_revenue) + to_money(event.grand_total)
        current_domain.repository_for(DailyOrderStats).add(record)

    @on(OrderCompleted)
    def on_order_completed(self, event: OrderCompleted) -> None:
        date_key = event.completed_at.date().isoformat()
        record = _get_or_create(date_key)
        record.orders_completed = (record.orders_completed or 0) + 1
        current_domain.repository_for(DailyOrderStats).add(record)

    @on(OrderCancelled)
    def on_order_cancelled(self, event: OrderCancelled) -> None:
        date_key = event.cancelled_at.date().isoformat()
        record = _get_or_create(date_key)
        record.orders_cancelled = (record.orders_cancelled or 0) + 1
        current_domain.repository_for(DailyOrderStats).add(record)

    @on(OrderRefunded)
    def on_order_refunded(self, event: OrderRefunded) -> None:
        date_key = event.refunded_at.date().isoformat()
        record = _get_or_create(date_key)
        record.orders_refunded = (record.orders_refunded or 0) + 1
        record.total_refunds = to_money(record.total_refunds) + to_money(event.refund_amount)
        current_domain.repository_for(DailyOrderStats).add(record)
