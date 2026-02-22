"""Inbound cross-domain event handler — Inventory reacts to Catalogue events.

Listens for ProductCreated and VariantAdded events from the Catalogue domain
to automatically initialize inventory records for new product variants.

Cross-domain events are imported from shared.events.catalogue and registered
as external events via inventory.register_external_event().
"""

import structlog
from protean.utils.globals import current_domain
from protean.utils.mixins import handle
from shared.events.catalogue import ProductCreated, VariantAdded

from inventory.domain import inventory
from inventory.stock.stock import InventoryItem

logger = structlog.get_logger(__name__)

# Register external events so Protean can deserialize them
inventory.register_external_event(ProductCreated, "Catalogue.ProductCreated.v1")
inventory.register_external_event(VariantAdded, "Catalogue.VariantAdded.v1")

# Default warehouse for auto-initialized stock
_DEFAULT_WAREHOUSE_ID = "default-warehouse"


@inventory.event_handler(part_of=InventoryItem, stream_category="catalogue::product")
class CatalogueInventoryEventHandler:
    """Reacts to Catalogue domain events to initialize inventory records."""

    @handle(ProductCreated)
    def on_product_created(self, event: ProductCreated) -> None:
        """Initialize an inventory record when a new product is created.

        Note: Products start in Draft status and may not have variants yet.
        This creates a placeholder record. Real stock is initialized when
        variants are added via VariantAdded events.
        """
        logger.info(
            "Product created in catalogue — inventory record noted",
            product_id=str(event.product_id),
            sku=event.sku,
        )

    @handle(VariantAdded)
    def on_variant_added(self, event: VariantAdded) -> None:
        """Initialize inventory record when a new variant is added to a product."""
        from inventory.stock.initialization import InitializeStock

        logger.info(
            "Initializing inventory for new variant",
            product_id=str(event.product_id),
            variant_id=str(event.variant_id),
            variant_sku=event.variant_sku,
        )

        current_domain.process(
            InitializeStock(
                product_id=event.product_id,
                variant_id=event.variant_id,
                warehouse_id=_DEFAULT_WAREHOUSE_ID,
                sku=event.variant_sku,
                initial_quantity=0,
                reorder_point=10,
                reorder_quantity=50,
            ),
            asynchronous=False,
        )
        logger.info(
            "Inventory initialized for variant",
            product_id=str(event.product_id),
            variant_id=str(event.variant_id),
        )
