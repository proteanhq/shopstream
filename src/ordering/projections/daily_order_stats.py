"""Daily order stats projection — analytics dashboard for order metrics.

Maintains daily aggregated counts of orders created, completed, cancelled,
and refunded, along with revenue totals. Keyed by date (YYYY-MM-DD).
"""

from protean.core.projector import on
from protean.exceptions import ObjectNotFoundError
from protean.fields import Float, Integer, String
from protean.utils.globals import current_domain

from ordering.domain import ordering
from ordering.order.events import (
    OrderCancelled,
    OrderCompleted,
    OrderCreated,
    OrderRefunded,
)
from ordering.order.order import Order


@ordering.projection
class DailyOrderStats:
    date = String(identifier=True, required=True, max_length=10)  # YYYY-MM-DD
    orders_created = Integer(default=0)
    orders_completed = Integer(default=0)
    orders_cancelled = Integer(default=0)
    orders_refunded = Integer(default=0)
    total_revenue = Float(default=0.0)
    total_refunds = Float(default=0.0)


def _get_or_create(date_key):
    repo = current_domain.repository_for(DailyOrderStats)
    try:
        return repo.get(date_key)
    except ObjectNotFoundError:
        record = DailyOrderStats(
            date=date_key,
            orders_created=0,
            orders_completed=0,
            orders_cancelled=0,
            orders_refunded=0,
            total_revenue=0.0,
            total_refunds=0.0,
        )
        return record


@ordering.projector(projector_for=DailyOrderStats, aggregates=[Order])
class DailyOrderStatsProjector:
    @on(OrderCreated)
    def on_order_created(self, event):
        date_key = event.created_at.date().isoformat()
        record = _get_or_create(date_key)
        record.orders_created = (record.orders_created or 0) + 1
        record.total_revenue = (record.total_revenue or 0.0) + (event.grand_total or 0.0)
        current_domain.repository_for(DailyOrderStats).add(record)

    @on(OrderCompleted)
    def on_order_completed(self, event):
        date_key = event.completed_at.date().isoformat()
        record = _get_or_create(date_key)
        record.orders_completed = (record.orders_completed or 0) + 1
        current_domain.repository_for(DailyOrderStats).add(record)

    @on(OrderCancelled)
    def on_order_cancelled(self, event):
        date_key = event.cancelled_at.date().isoformat()
        record = _get_or_create(date_key)
        record.orders_cancelled = (record.orders_cancelled or 0) + 1
        current_domain.repository_for(DailyOrderStats).add(record)

    @on(OrderRefunded)
    def on_order_refunded(self, event):
        date_key = event.refunded_at.date().isoformat()
        record = _get_or_create(date_key)
        record.orders_refunded = (record.orders_refunded or 0) + 1
        record.total_refunds = (record.total_refunds or 0.0) + (event.refund_amount or 0.0)
        current_domain.repository_for(DailyOrderStats).add(record)
