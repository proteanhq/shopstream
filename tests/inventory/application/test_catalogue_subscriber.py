"""Application tests for CatalogueVariantSubscriber — Inventory reacts to Catalogue stream.

Tests the subscriber ACL pattern: raw dict payloads are filtered by event type
and translated into InitializeStock commands.
"""

from datetime import UTC, datetime

from protean import current_domain

from inventory.projections.inventory_level import InventoryLevel
from inventory.stock.catalogue_subscriber import CatalogueVariantSubscriber


def _build_message(event_type: str, data: dict) -> dict:
    """Build a broker message payload with metadata and data."""
    return {
        "data": data,
        "metadata": {"headers": {"type": event_type}},
    }


class TestCatalogueVariantSubscriber:
    def test_variant_added_creates_inventory_item(self):
        """VariantAdded should dispatch InitializeStock and create an InventoryItem.

        Verified via the InventoryLevel projection which is populated by the
        StockInitialized event projector.
        """
        payload = _build_message(
            "Catalogue.VariantAdded.v1",
            {
                "product_id": "prod-cat-002",
                "variant_id": "var-cat-002",
                "variant_sku": "VARIANT-SKU-002",
                "price_amount": 29.99,
                "price_currency": "USD",
                "created_at": datetime.now(UTC).isoformat(),
            },
        )

        subscriber = CatalogueVariantSubscriber()
        subscriber(payload)

        # The InventoryLevel projection should show the new item
        try:
            levels = current_domain.repository_for(InventoryLevel).query.all().items
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
        subscriber = CatalogueVariantSubscriber()

        subscriber(
            _build_message(
                "Catalogue.VariantAdded.v1",
                {
                    "product_id": "prod-cat-003a",
                    "variant_id": "var-cat-003a",
                    "variant_sku": "SKU-A",
                    "price_amount": 10.0,
                    "price_currency": "USD",
                    "created_at": datetime.now(UTC).isoformat(),
                },
            )
        )
        subscriber(
            _build_message(
                "Catalogue.VariantAdded.v1",
                {
                    "product_id": "prod-cat-003b",
                    "variant_id": "var-cat-003b",
                    "variant_sku": "SKU-B",
                    "price_amount": 20.0,
                    "price_currency": "USD",
                    "created_at": datetime.now(UTC).isoformat(),
                },
            )
        )

        try:
            levels = current_domain.repository_for(InventoryLevel).query.all().items
        except Exception:
            levels = []

        matching_a = [lv for lv in levels if str(lv.product_id) == "prod-cat-003a"]
        matching_b = [lv for lv in levels if str(lv.product_id) == "prod-cat-003b"]
        assert len(matching_a) == 1
        assert len(matching_b) == 1

    def test_ignores_non_variant_added_events(self):
        """Non-VariantAdded events on the catalogue stream are ignored."""
        payload = _build_message(
            "Catalogue.ProductCreated.v1",
            {
                "product_id": "prod-cat-ignored",
                "sku": "IGNORED-SKU",
                "title": "Ignored Product",
                "status": "Draft",
                "created_at": datetime.now(UTC).isoformat(),
            },
        )

        subscriber = CatalogueVariantSubscriber()
        subscriber(payload)

        # No InventoryLevel projection should have been created
        try:
            levels = current_domain.repository_for(InventoryLevel).query.all().items
        except Exception:
            levels = []
        matching = [lv for lv in levels if str(lv.product_id) == "prod-cat-ignored"]
        assert len(matching) == 0

    def test_uses_default_warehouse(self):
        """Subscriber should assign default-warehouse to initialized stock."""
        payload = _build_message(
            "Catalogue.VariantAdded.v1",
            {
                "product_id": "prod-cat-wh",
                "variant_id": "var-cat-wh",
                "variant_sku": "WH-SKU",
                "price_amount": 15.0,
                "price_currency": "USD",
                "created_at": datetime.now(UTC).isoformat(),
            },
        )

        subscriber = CatalogueVariantSubscriber()
        subscriber(payload)

        try:
            levels = current_domain.repository_for(InventoryLevel).query.all().items
        except Exception:
            levels = []
        matching = [lv for lv in levels if str(lv.product_id) == "prod-cat-wh"]
        assert len(matching) == 1
        assert matching[0].warehouse_id == "default-warehouse"

    def test_initializes_with_zero_quantity(self):
        """Newly initialized stock should have zero on-hand and available."""
        payload = _build_message(
            "Catalogue.VariantAdded.v1",
            {
                "product_id": "prod-cat-qty",
                "variant_id": "var-cat-qty",
                "variant_sku": "QTY-SKU",
                "price_amount": 25.0,
                "price_currency": "USD",
                "created_at": datetime.now(UTC).isoformat(),
            },
        )

        subscriber = CatalogueVariantSubscriber()
        subscriber(payload)

        try:
            levels = current_domain.repository_for(InventoryLevel).query.all().items
        except Exception:
            levels = []
        matching = [lv for lv in levels if str(lv.product_id) == "prod-cat-qty"]
        assert len(matching) == 1
        assert matching[0].on_hand == 0
        assert matching[0].available == 0

    def test_ignores_payload_without_metadata(self):
        """Payloads missing metadata entirely are ignored."""
        payload = {
            "data": {
                "product_id": "prod-no-meta",
                "variant_id": "var-no-meta",
                "variant_sku": "NO-META-SKU",
            }
        }

        subscriber = CatalogueVariantSubscriber()
        subscriber(payload)

        try:
            levels = current_domain.repository_for(InventoryLevel).query.all().items
        except Exception:
            levels = []
        matching = [lv for lv in levels if str(lv.product_id) == "prod-no-meta"]
        assert len(matching) == 0
