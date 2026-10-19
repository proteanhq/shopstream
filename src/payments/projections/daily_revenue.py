"""Daily revenue — revenue analytics aggregation."""

from protean.core.projector import on
from protean.fields import Float, Integer, String
from protean.utils.globals import current_domain

from payments.domain import payments
from payments.payment.events import PaymentSucceeded, RefundCompleted
from payments.payment.payment import Payment


@payments.projection
class DailyRevenue:
    date: str = String(identifier=True, max_length=10, required=True)  # "YYYY-MM-DD"
    currency: str = String(default="USD")
    total_revenue: float = Float(default=0.0)
    total_refunded: float = Float(default=0.0)
    net_revenue: float = Float(default=0.0)
    transaction_count: int = Integer(default=0)
    refund_count: int = Integer(default=0)


@payments.projector(projector_for=DailyRevenue, aggregates=[Payment])
class DailyRevenueProjector:
    @on(PaymentSucceeded)
    def on_payment_succeeded(self, event):
        repo = current_domain.repository_for(DailyRevenue)
        date_key = event.succeeded_at.date().isoformat()

        record = repo.get_or_none(date_key)
        if record is None:
            record = DailyRevenue(
                date=date_key,
                currency=event.currency,
            )

        record.total_revenue = (record.total_revenue or 0.0) + event.amount
        record.net_revenue = (record.total_revenue or 0.0) - (record.total_refunded or 0.0)
        record.transaction_count = (record.transaction_count or 0) + 1
        repo.add(record)

    @on(RefundCompleted)
    def on_refund_completed(self, event):
        repo = current_domain.repository_for(DailyRevenue)
        date_key = event.completed_at.date().isoformat()

        record = repo.get_or_none(date_key)
        if record is None:
            record = DailyRevenue(date=date_key)

        record.total_refunded = (record.total_refunded or 0.0) + event.amount
        record.net_revenue = (record.total_revenue or 0.0) - (record.total_refunded or 0.0)
        record.refund_count = (record.refund_count or 0) + 1
        repo.add(record)
