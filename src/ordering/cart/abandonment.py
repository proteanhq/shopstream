"""Cart abandonment detection — command and handler for flagging idle carts.

Designed to be triggered periodically by an external scheduler (cron, K8s
CronJob) via the maintenance API endpoint. Queries the CartView projection
for active carts idle beyond the threshold and dispatches AbandonCart
commands for each. The resulting CartAbandoned events are consumed by the
Notifications domain to send recovery emails.
"""

from datetime import UTC, datetime, timedelta

import structlog
from protean import handle
from protean.exceptions import InvalidOperationError, ValidationError
from protean.fields import DateTime, Integer
from protean.utils.globals import current_domain

from ordering.cart.cart import ShoppingCart
from ordering.domain import ordering
from ordering.projections.cart_view import CartView

logger = structlog.get_logger(__name__)


@ordering.command(part_of="ShoppingCart")
class DetectAbandonedCarts:
    """Flag active carts idle beyond the specified threshold."""

    idle_threshold_hours = Integer(default=24)
    as_of = DateTime()  # Optional: defaults to now


@ordering.command_handler(part_of=ShoppingCart)
class DetectAbandonedCartsHandler:
    @handle(DetectAbandonedCarts)
    def detect_abandoned_carts(self, command):
        as_of = command.as_of or datetime.now(UTC)
        threshold_hours = command.idle_threshold_hours or 24
        cutoff = (as_of - timedelta(hours=threshold_hours)).replace(tzinfo=None)

        logger.info(
            "Checking for abandoned carts",
            cutoff=cutoff.isoformat(),
            threshold_hours=threshold_hours,
        )

        # Query active carts
        active_carts = current_domain.repository_for(CartView)._dao.query.filter(status="Active").all().items

        # Filter idle carts with items
        abandoned = []
        for cart in active_carts:
            if cart.updated_at and cart.updated_at <= cutoff and (cart.item_count or 0) > 0:
                abandoned.append(cart)

        if not abandoned:
            logger.info("No abandoned carts found")
            return 0

        from ordering.cart.management import AbandonCart

        abandoned_count = 0
        for cart in abandoned:
            try:
                current_domain.process(
                    AbandonCart(cart_id=str(cart.cart_id)),
                    asynchronous=False,
                )
                abandoned_count += 1
                logger.info(
                    "Marked cart as abandoned",
                    cart_id=str(cart.cart_id),
                    customer_id=str(cart.customer_id) if cart.customer_id else None,
                    item_count=cart.item_count,
                    last_updated=str(cart.updated_at),
                )
            except (ValidationError, InvalidOperationError) as exc:
                logger.warning(
                    "Failed to abandon cart",
                    cart_id=str(cart.cart_id),
                    error=str(exc),
                )

        logger.info("Cart abandonment detection complete", abandoned_count=abandoned_count)
        return abandoned_count
