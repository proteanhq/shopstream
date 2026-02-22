"""Abandoned checkouts projection — orders created but never confirmed.

Captures orders stuck in CREATED state for cart recovery purposes. Orders
are inserted on creation and removed when confirmed or cancelled.
"""

from protean.core.projector import on
from protean.exceptions import ObjectNotFoundError
from protean.fields import DateTime, Float, Identifier, Integer, String
from protean.utils.globals import current_domain

from ordering.domain import ordering
from ordering.order.events import OrderCancelled, OrderConfirmed, OrderCreated
from ordering.order.order import Order


@ordering.projection
class AbandonedCheckout:
    order_id = Identifier(identifier=True, required=True)
    customer_id = Identifier(required=True)
    item_count = Integer(default=0)
    grand_total = Float(default=0.0)
    currency = String(default="USD")
    created_at = DateTime()


@ordering.projector(projector_for=AbandonedCheckout, aggregates=[Order])
class AbandonedCheckoutProjector:
    @on(OrderCreated)
    def on_order_created(self, event):
        import json

        items = json.loads(event.items) if isinstance(event.items, str) else (event.items or [])
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
    def on_order_confirmed(self, event):
        """Remove from abandoned checkouts — order was confirmed."""
        repo = current_domain.repository_for(AbandonedCheckout)
        try:
            record = repo.get(str(event.order_id))
            repo._dao.delete(record)
        except ObjectNotFoundError:
            pass

    @on(OrderCancelled)
    def on_order_cancelled(self, event):
        """Remove from abandoned checkouts — order was explicitly cancelled."""
        repo = current_domain.repository_for(AbandonedCheckout)
        try:
            record = repo.get(str(event.order_id))
            repo._dao.delete(record)
        except ObjectNotFoundError:
            pass
