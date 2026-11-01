"""Cart abandonment detection — command and handler for flagging idle carts.

Designed to be triggered periodically by an external scheduler (cron, K8s
CronJob) via the maintenance API endpoint. Queries the CartView projection
for active carts idle beyond the threshold and dispatches AbandonCart
commands for each. The resulting CartAbandoned events are consumed by the
Notifications domain to send recovery emails.
"""

from datetime import datetime, timedelta

import structlog
from protean import handle
from protean.fields import DateTime, Integer
from protean.utils.globals import current_domain
from protean.utils.processing import Priority, processing_priority

from ordering.cart.cart import ShoppingCart
from ordering.domain import ordering
from ordering.projections.cart_view import CartView

logger = structlog.get_logger(__name__)


@ordering.command(part_of="ShoppingCart")
class DetectAbandonedCarts:
    """Flag active carts idle beyond the specified threshold."""

    idle_threshold_hours: int = Integer(default=24)
    as_of: datetime | None = DateTime()  # Optional: defaults to the domain clock


@ordering.command_handler(part_of=ShoppingCart)
class DetectAbandonedCartsHandler:
    @handle(DetectAbandonedCarts)
    def detect_abandoned_carts(self, command: DetectAbandonedCarts) -> int:
        with processing_priority(Priority.LOW):
            as_of = command.as_of or current_domain.clock.now()
            threshold_hours = 24 if command.idle_threshold_hours is None else command.idle_threshold_hours
            cutoff = as_of - timedelta(hours=threshold_hours)
            # Strip tzinfo for comparison with naive datetimes from DB
            cutoff_naive = cutoff.replace(tzinfo=None)

            logger.info(
                "Checking for abandoned carts",
                cutoff=cutoff_naive.isoformat(),
                threshold_hours=threshold_hours,
            )

            abandoned = _idle_carts_with_items(cutoff_naive)
            if not abandoned:
                logger.info("No abandoned carts found")
                return 0

            # Every AbandonCart joins this handler's transaction. A failed one would
            # roll back all of them, so skip any cart the aggregate would reject, and
            # let an unexpected failure fail the whole batch instead of reporting success.
            repo = current_domain.repository_for(ShoppingCart)
            abandoned_count = 0
            for cart in abandoned:
                aggregate = repo.get_or_none(str(cart.cart_id))
                blocker = "Cart not found" if aggregate is None else aggregate.abandon_blocker()
                if blocker is None:
                    _abandon(cart)
                    abandoned_count += 1
                else:
                    logger.warning(
                        "Skipped cart",
                        cart_id=str(cart.cart_id),
                        error=blocker,
                    )

            logger.info("Cart abandonment detection complete", abandoned_count=abandoned_count)
            return abandoned_count


def _idle_carts_with_items(cutoff_naive: datetime) -> list[CartView]:
    active_carts = current_domain.view_for(CartView).query.filter(status="Active").all().items
    return [
        cart
        for cart in active_carts
        if cart.updated_at and cart.updated_at.replace(tzinfo=None) <= cutoff_naive and (cart.item_count or 0) > 0
    ]


def _abandon(cart: CartView) -> None:
    from ordering.cart.management import AbandonCart

    current_domain.process(
        AbandonCart(cart_id=str(cart.cart_id)),
        asynchronous=False,
    )
    logger.info(
        "Marked cart as abandoned",
        cart_id=str(cart.cart_id),
        customer_id=str(cart.customer_id) if cart.customer_id else None,
        item_count=cart.item_count,
        last_updated=str(cart.updated_at),
    )
