"""Application tests for CatalogueInventoryEventHandler — Inventory reacts to Catalogue events.

Covers:
- on_product_created: logs only, no side effects
- on_variant_added: dispatches InitializeStock, creating a new InventoryItem
"""

from datetime import UTC, datetime

from inventory.projections.inventory_level import InventoryLevel
from inventory.stock.catalogue_events import CatalogueInventoryEventHandler
from protean import current_domain
from shared.events.catalogue import ProductCreated, VariantAdded


class TestProductCreatedHandler:
    def test_product_created_logs_without_error(self):
        """ProductCreated just logs — no inventory item should be created."""
        handler = CatalogueInventoryEventHandler()
        handler.on_product_created(
            ProductCreated(
                product_id="prod-cat-001",
                sku="NEW-PROD",
                title="New Product",
                status="Draft",
                created_at=datetime.now(UTC),
            )
        )
        # No InventoryLevel projection should have been created
        try:
            levels = current_domain.repository_for(InventoryLevel)._dao.query.all().items
        except Exception:
            levels = []
        matching = [lv for lv in levels if str(lv.product_id) == "prod-cat-001"]
        assert len(matching) == 0


class TestVariantAddedHandler:
    def test_variant_added_creates_inventory_item(self):
        """VariantAdded should dispatch InitializeStock and create an InventoryItem.

        Verified via the InventoryLevel projection which is populated by the
        StockInitialized event projector.
        """
        handler = CatalogueInventoryEventHandler()
        handler.on_variant_added(
            VariantAdded(
                product_id="prod-cat-002",
                variant_id="var-cat-002",
                variant_sku="VARIANT-SKU-002",
                price_amount=29.99,
                price_currency="USD",
                created_at=datetime.now(UTC),
            )
        )

        # The InventoryLevel projection should show the new item
        try:
            levels = current_domain.repository_for(InventoryLevel)._dao.query.all().items
        except Exception:
            levels = []
        matching = [lv for lv in levels if str(lv.product_id) == "prod-cat-002" and str(lv.variant_id) == "var-cat-002"]
        assert len(matching) == 1

        level = matching[0]
        assert level.sku == "VARIANT-SKU-002"
        assert level.warehouse_id == "default-warehouse"
        assert level.on_hand == 0
        assert level.available == 0

    def test_variant_added_with_different_products(self):
        """Each variant should create a separate InventoryItem."""
        handler = CatalogueInventoryEventHandler()

        handler.on_variant_added(
            VariantAdded(
                product_id="prod-cat-003a",
                variant_id="var-cat-003a",
                variant_sku="SKU-A",
                price_amount=10.0,
                price_currency="USD",
                created_at=datetime.now(UTC),
            )
        )
        handler.on_variant_added(
            VariantAdded(
                product_id="prod-cat-003b",
                variant_id="var-cat-003b",
                variant_sku="SKU-B",
                price_amount=20.0,
                price_currency="USD",
                created_at=datetime.now(UTC),
            )
        )

        try:
            levels = current_domain.repository_for(InventoryLevel)._dao.query.all().items
        except Exception:
            levels = []

        matching_a = [lv for lv in levels if str(lv.product_id) == "prod-cat-003a"]
        matching_b = [lv for lv in levels if str(lv.product_id) == "prod-cat-003b"]
        assert len(matching_a) == 1
        assert len(matching_b) == 1
