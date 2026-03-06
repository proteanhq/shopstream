"""Inbound cross-domain subscriber — Inventory reacts to Catalogue stream.

Listens for VariantAdded messages from the Catalogue domain's broker stream
to automatically initialize inventory records for new product variants.

Uses the subscriber (ACL) pattern: receives raw dict payloads from the broker,
filters by event type, and translates into an InitializeStock command.
No dependency on shared event classes or register_external_event.
"""

import structlog
from protean.utils.globals import current_domain

from inventory.domain import inventory

logger = structlog.get_logger(__name__)

# Default warehouse for auto-initialized stock
_DEFAULT_WAREHOUSE_ID = "default-warehouse"


@inventory.subscriber(stream="catalogue::product")
class CatalogueVariantSubscriber:
    """Reacts to VariantAdded events to initialize inventory records.

    ACL pattern: receives raw broker message dict, extracts event type from
    metadata.headers.type, and dispatches an InitializeStock command with
    default warehouse and quantity settings. Ignores all other event types.
    """

    def __call__(self, payload: dict) -> None:
        event_type = payload.get("metadata", {}).get("headers", {}).get("type", "")
        if "VariantAdded" not in event_type:
            return

        data = payload.get("data", {})

        logger.info(
            "Initializing inventory for new variant",
            product_id=str(data.get("product_id", "")),
            variant_id=str(data.get("variant_id", "")),
            variant_sku=data.get("variant_sku", ""),
        )

        from inventory.stock.initialization import InitializeStock

        current_domain.process(
            InitializeStock(
                product_id=data["product_id"],
                variant_id=data["variant_id"],
                warehouse_id=_DEFAULT_WAREHOUSE_ID,
                sku=data["variant_sku"],
                initial_quantity=0,
                reorder_point=10,
                reorder_quantity=50,
            ),
            asynchronous=False,
        )

        logger.info(
            "Inventory initialized for variant",
            product_id=str(data.get("product_id", "")),
            variant_id=str(data.get("variant_id", "")),
        )
