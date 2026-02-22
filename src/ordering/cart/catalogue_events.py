"""Inbound cross-domain event handler — Ordering reacts to Catalogue events.

Listens for ProductDiscontinued events from the Catalogue domain. When a
product is discontinued, active carts containing that product's items are
flagged for notification. Cart items are not automatically removed — the
customer is informed at checkout instead.

Note: VariantPriceChanged is NOT handled here. Carts don't store prices;
prices are resolved at checkout from the current catalogue. This is a
deliberate design decision: carts reference product/variant IDs, and the
storefront resolves current pricing at display and checkout time.

Cross-domain events are imported from shared.events.catalogue and registered
as external events via ordering.register_external_event().
"""

import json

import structlog
from protean.utils.globals import current_domain
from protean.utils.mixins import handle
from shared.events.catalogue import ProductDiscontinued

from ordering.cart.cart import ShoppingCart
from ordering.domain import ordering
from ordering.projections.cart_view import CartView

logger = structlog.get_logger(__name__)

# Register external event so Protean can deserialize it
ordering.register_external_event(ProductDiscontinued, "Catalogue.ProductDiscontinued.v1")


@ordering.event_handler(part_of=ShoppingCart, stream_category="catalogue::product")
class CatalogueCartEventHandler:
    """Reacts to Catalogue domain events affecting shopping carts."""

    @handle(ProductDiscontinued)
    def on_product_discontinued(self, event: ProductDiscontinued) -> None:
        """Log when a product is discontinued that may be in active carts.

        Active carts containing the discontinued product will show a warning
        at checkout time when the storefront checks product availability.
        """
        logger.info(
            "Product discontinued — active carts may contain this item",
            product_id=str(event.product_id),
            sku=event.sku,
        )

        # Find active carts containing this product
        active_carts = current_domain.repository_for(CartView)._dao.query.filter(status="Active").all().items

        affected_count = 0
        for cart in active_carts:
            items = json.loads(cart.items) if isinstance(cart.items, str) else (cart.items or [])
            has_product = any(item.get("product_id") == str(event.product_id) for item in items)
            if has_product:
                affected_count += 1

        if affected_count:
            logger.warning(
                "Active carts contain discontinued product",
                product_id=str(event.product_id),
                affected_cart_count=affected_count,
            )
