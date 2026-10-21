"""Abandoned checkouts projection — orders created but never confirmed.

Captures orders stuck in CREATED state for cart recovery purposes. Orders
are inserted on creation and removed when confirmed or cancelled.
"""

from datetime import datetime
from decimal import Decimal as D

from protean.core.projector import on
from protean.fields import DateTime, Decimal, Identifier, Integer, String
from protean.utils.globals import current_domain

from ordering.domain import ordering
from ordering.order.events import OrderCancelled, OrderConfirmed, OrderCreated
from ordering.order.order import Order


@ordering.projection
class AbandonedCheckout:
    order_id: str = Identifier(identifier=True, required=True)
    customer_id: str = Identifier(required=True)
    item_count: int = Integer(default=0)
    grand_total: D = Decimal(precision=19, scale=4, default=D("0"))
    currency: str = String(default="USD")
    created_at: datetime | None = DateTime()


@ordering.projector(projector_for=AbandonedCheckout, aggregates=[Order])
class AbandonedCheckoutProjector:
    @on(OrderCreated)
    def on_order_created(self, event: OrderCreated) -> None:
        items = event.items or []
        current_domain.repository_for(AbandonedCheckout).add(
            AbandonedCheckout(
                order_id=event.order_id,
                customer_id=event.customer_id,
                item_count=len(items),
                grand_total=event.grand_total,
                currency=event.currency or "USD",
                created_at=event.created_at,
            )
        )

    @on(OrderConfirmed)
    def on_order_confirmed(self, event: OrderConfirmed) -> None:
        """Remove from abandoned checkouts — order was confirmed."""
        repo = current_domain.repository_for(AbandonedCheckout)
        if repo.get_or_none(str(event.order_id)) is not None:
            repo.query.filter(order_id=str(event.order_id)).delete()

    @on(OrderCancelled)
    def on_order_cancelled(self, event: OrderCancelled) -> None:
        """Remove from abandoned checkouts — order was explicitly cancelled."""
        repo = current_domain.repository_for(AbandonedCheckout)
        if repo.get_or_none(str(event.order_id)) is not None:
            repo.query.filter(order_id=str(event.order_id)).delete()
