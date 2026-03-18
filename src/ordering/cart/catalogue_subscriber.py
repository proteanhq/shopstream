"""Inbound cross-domain subscriber — Ordering reacts to Catalogue events.

Listens for ProductDiscontinued events from the Catalogue domain's external bus.
When a product is discontinued, active carts containing that product's items are
flagged for notification. Cart items are not automatically removed — the
customer is informed at checkout instead.

Note: VariantPriceChanged is NOT handled here. Carts don't store prices;
prices are resolved at checkout from the current catalogue. This is a
deliberate design decision: carts reference product/variant IDs, and the
storefront resolves current pricing at display and checkout time.

Uses the subscriber (ACL) pattern: receives raw dict payloads from the global
broker, filters by event type, and performs side-effects.
No dependency on shared event classes or register_external_event.
"""

import structlog
from protean.utils.globals import current_domain

from ordering.domain import ordering
from ordering.projections.cart_view import CartView

logger = structlog.get_logger(__name__)


@ordering.subscriber(broker="global", stream="catalogue::product")
class CatalogueEventsSubscriber:
    """Reacts to Catalogue domain events affecting shopping carts.

    ACL pattern: receives raw broker message dict, extracts event type from
    metadata.headers.type, and performs side-effects. Ignores all event types
    not relevant to the Ordering domain.
    """

    def __call__(self, payload: dict) -> None:
        event_type = payload.get("metadata", {}).get("headers", {}).get("type", "")
        data = payload.get("data", {})

        if "ProductDiscontinued" in event_type:
            self._on_product_discontinued(data)

    def _on_product_discontinued(self, data: dict) -> None:
        """Log when a product is discontinued that may be in active carts.

        Active carts containing the discontinued product will show a warning
        at checkout time when the storefront checks product availability.
        """
        product_id = str(data.get("product_id", ""))
        sku = data.get("sku", "")

        logger.info(
            "Product discontinued — active carts may contain this item",
            product_id=product_id,
            sku=sku,
        )

        # Find active carts containing this product
        active_carts = current_domain.view_for(CartView).query.filter(status="Active").all().items

        affected_count = 0
        for cart in active_carts:
            items = cart.items or []
            has_product = any(item.get("product_id") == product_id for item in items)
            if has_product:
                affected_count += 1

        if affected_count:
            logger.warning(
                "Active carts contain discontinued product",
                product_id=product_id,
                affected_cart_count=affected_count,
            )
