"""Integration tests for product projections."""

import json

from catalogue.product.creation import CreateProduct
from catalogue.product.details import UpdateProductDetails
from catalogue.product.images import AddProductImage
from catalogue.product.lifecycle import ActivateProduct, ArchiveProduct, DiscontinueProduct
from catalogue.product.product import Product
from catalogue.product.variants import AddVariant, SetTierPrice, UpdateVariantPrice
from catalogue.projections.price_history import PriceHistory
from catalogue.projections.product_card import ProductCard
from catalogue.projections.product_detail import ProductDetail
from catalogue.projections.seller_catalogue import SellerCatalogue
from protean.utils.globals import current_domain


def _create_product(**overrides):
    defaults = {"sku": "PROJ-001", "title": "Projection Test", "seller_id": "seller-001"}
    defaults.update(overrides)
    command = CreateProduct(**defaults)
    return current_domain.process(command, asynchronous=False)


class TestProductDetailProjection:
    def test_created_on_product_created(self):
        product_id = _create_product()

        detail = current_domain.repository_for(ProductDetail).get(product_id)
        assert detail.sku == "PROJ-001"
        assert detail.title == "Projection Test"
        assert detail.status == "Draft"

    def test_updated_on_details_changed(self):
        product_id = _create_product()
        current_domain.process(
            UpdateProductDetails(product_id=product_id, title="Updated Title", brand="BrandX"),
            asynchronous=False,
        )

        detail = current_domain.repository_for(ProductDetail).get(product_id)
        assert detail.title == "Updated Title"
        assert detail.brand == "BrandX"

    def test_variants_tracked(self):
        product_id = _create_product()
        current_domain.process(
            AddVariant(product_id=product_id, variant_sku="V-001", base_price=29.99),
            asynchronous=False,
        )

        detail = current_domain.repository_for(ProductDetail).get(product_id)
        variants = json.loads(detail.variants)
        assert len(variants) == 1
        assert variants[0]["variant_sku"] == "V-001"

    def test_images_tracked(self):
        product_id = _create_product()
        current_domain.process(
            AddProductImage(product_id=product_id, url="https://cdn.example.com/img.jpg"),
            asynchronous=False,
        )

        detail = current_domain.repository_for(ProductDetail).get(product_id)
        images = json.loads(detail.images)
        assert len(images) == 1

    def test_variant_price_change_tracked(self):
        product_id = _create_product()
        current_domain.process(
            AddVariant(product_id=product_id, variant_sku="V-001", base_price=29.99),
            asynchronous=False,
        )

        product = current_domain.repository_for(Product).get(product_id)
        variant_id = product.variants[0].id

        current_domain.process(
            UpdateVariantPrice(product_id=product_id, variant_id=variant_id, base_price=49.99),
            asynchronous=False,
        )

        detail = current_domain.repository_for(ProductDetail).get(product_id)
        variants = json.loads(detail.variants)
        assert variants[0]["price_amount"] == 49.99

    def test_tier_price_tracked(self):
        product_id = _create_product()
        current_domain.process(
            AddVariant(product_id=product_id, variant_sku="V-001", base_price=29.99),
            asynchronous=False,
        )

        product = current_domain.repository_for(Product).get(product_id)
        variant_id = product.variants[0].id

        current_domain.process(
            SetTierPrice(product_id=product_id, variant_id=variant_id, tier="Silver", price=24.99),
            asynchronous=False,
        )

        detail = current_domain.repository_for(ProductDetail).get(product_id)
        variants = json.loads(detail.variants)
        assert variants[0]["tier_prices"]["Silver"] == 24.99

    def test_status_transitions_tracked(self):
        product_id = _create_product()
        current_domain.process(
            AddVariant(product_id=product_id, variant_sku="V-001", base_price=29.99),
            asynchronous=False,
        )
        current_domain.process(ActivateProduct(product_id=product_id), asynchronous=False)

        detail = current_domain.repository_for(ProductDetail).get(product_id)
        assert detail.status == "Active"

        current_domain.process(DiscontinueProduct(product_id=product_id), asynchronous=False)
        detail = current_domain.repository_for(ProductDetail).get(product_id)
        assert detail.status == "Discontinued"

        current_domain.process(ArchiveProduct(product_id=product_id), asynchronous=False)
        detail = current_domain.repository_for(ProductDetail).get(product_id)
        assert detail.status == "Archived"


class TestProductCardProjection:
    def test_created_on_product_created(self):
        product_id = _create_product()

        card = current_domain.repository_for(ProductCard).get(product_id)
        assert card.sku == "PROJ-001"
        assert card.title == "Projection Test"
        assert card.status == "Draft"
        assert card.variant_count == 0

    def test_variant_count_and_prices_tracked(self):
        product_id = _create_product()
        current_domain.process(
            AddVariant(product_id=product_id, variant_sku="V-001", base_price=29.99),
            asynchronous=False,
        )
        current_domain.process(
            AddVariant(product_id=product_id, variant_sku="V-002", base_price=49.99),
            asynchronous=False,
        )

        card = current_domain.repository_for(ProductCard).get(product_id)
        assert card.variant_count == 2
        assert card.min_price == 29.99
        assert card.max_price == 49.99

    def test_variant_price_change_updates_card(self):
        product_id = _create_product()
        current_domain.process(
            AddVariant(product_id=product_id, variant_sku="V-001", base_price=29.99),
            asynchronous=False,
        )

        product = current_domain.repository_for(Product).get(product_id)
        variant_id = product.variants[0].id

        current_domain.process(
            UpdateVariantPrice(product_id=product_id, variant_id=variant_id, base_price=9.99),
            asynchronous=False,
        )

        card = current_domain.repository_for(ProductCard).get(product_id)
        assert card.min_price == 9.99

    def test_primary_image_tracked(self):
        product_id = _create_product()
        current_domain.process(
            AddProductImage(product_id=product_id, url="https://cdn.example.com/primary.jpg"),
            asynchronous=False,
        )

        card = current_domain.repository_for(ProductCard).get(product_id)
        assert card.primary_image_url == "https://cdn.example.com/primary.jpg"

    def test_status_transitions_tracked(self):
        product_id = _create_product()
        current_domain.process(
            AddVariant(product_id=product_id, variant_sku="V-001", base_price=29.99),
            asynchronous=False,
        )
        current_domain.process(ActivateProduct(product_id=product_id), asynchronous=False)

        card = current_domain.repository_for(ProductCard).get(product_id)
        assert card.status == "Active"


class TestSellerCatalogueProjection:
    def test_created_on_product_created(self):
        product_id = _create_product(seller_id="seller-xyz")

        record = current_domain.repository_for(SellerCatalogue).get(product_id)
        assert record.seller_id == "seller-xyz"
        assert record.sku == "PROJ-001"
        assert record.status == "Draft"
        assert record.variant_count == 0

    def test_variant_count_tracked(self):
        product_id = _create_product()
        current_domain.process(
            AddVariant(product_id=product_id, variant_sku="V-001", base_price=29.99),
            asynchronous=False,
        )

        record = current_domain.repository_for(SellerCatalogue).get(product_id)
        assert record.variant_count == 1

    def test_title_update_tracked(self):
        product_id = _create_product()
        current_domain.process(
            UpdateProductDetails(product_id=product_id, title="New Title"),
            asynchronous=False,
        )

        record = current_domain.repository_for(SellerCatalogue).get(product_id)
        assert record.title == "New Title"


class TestPriceHistoryProjection:
    def test_price_change_recorded(self):
        product_id = _create_product()
        current_domain.process(
            AddVariant(product_id=product_id, variant_sku="V-001", base_price=29.99),
            asynchronous=False,
        )

        product = current_domain.repository_for(Product).get(product_id)
        variant_id = product.variants[0].id

        current_domain.process(
            UpdateVariantPrice(product_id=product_id, variant_id=variant_id, base_price=39.99),
            asynchronous=False,
        )

        # Check price history has an entry
        repo = current_domain.repository_for(PriceHistory)
        results = repo._dao.query.all()
        matching = [r for r in results.items if r.product_id == product_id]
        assert len(matching) == 1
        assert matching[0].previous_price == 29.99
        assert matching[0].new_price == 39.99
