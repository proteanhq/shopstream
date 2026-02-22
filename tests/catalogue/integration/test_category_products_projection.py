"""Integration tests for CategoryProducts projection.

Covers:
- Category creation creates a CategoryProducts projection record
- Product creation with category_id adds the product to the projection
- Product activation updates status in the projection
- Product discontinuation updates status in the projection
- Product archival updates status in the projection
- Product details update (title change) updates title in the projection
"""

import json
from datetime import UTC, datetime

from catalogue.category.management import CreateCategory
from catalogue.product.creation import CreateProduct
from catalogue.product.details import UpdateProductDetails
from catalogue.product.lifecycle import ActivateProduct, ArchiveProduct, DiscontinueProduct
from catalogue.product.variants import AddVariant
from catalogue.projections.category_products import CategoryProducts
from protean.utils.globals import current_domain


def _create_category(name="Electronics"):
    return current_domain.process(
        CreateCategory(name=name),
        asynchronous=False,
    )


def _create_product_in_category(category_id, **overrides):
    defaults = {
        "sku": "CAT-PROD-001",
        "title": "Test Product",
        "category_id": category_id,
    }
    defaults.update(overrides)
    return current_domain.process(
        CreateProduct(**defaults),
        asynchronous=False,
    )


class TestCategoryProductsProjection:
    def test_category_creation_creates_projection(self):
        """Creating a category should create a CategoryProducts projection record."""
        category_id = _create_category(name="Clothing")

        view = current_domain.repository_for(CategoryProducts).get(category_id)
        assert view.category_name == "Clothing"
        assert view.product_count == 0
        products = json.loads(view.products)
        assert products == []

    def test_product_creation_adds_to_category(self):
        """Creating a product with a category_id adds it to the CategoryProducts projection."""
        category_id = _create_category(name="Books")
        product_id = _create_product_in_category(category_id, sku="BOOK-001", title="Python Cookbook")

        view = current_domain.repository_for(CategoryProducts).get(category_id)
        assert view.product_count == 1
        products = json.loads(view.products)
        assert len(products) == 1
        assert products[0]["product_id"] == product_id
        assert products[0]["title"] == "Python Cookbook"
        assert products[0]["sku"] == "BOOK-001"
        assert products[0]["status"] == "Draft"

    def test_multiple_products_in_category(self):
        """Multiple products in the same category should all appear in the projection."""
        category_id = _create_category(name="Gadgets")
        _create_product_in_category(category_id, sku="GAD-001", title="Widget A")
        _create_product_in_category(category_id, sku="GAD-002", title="Widget B")

        view = current_domain.repository_for(CategoryProducts).get(category_id)
        assert view.product_count == 2
        products = json.loads(view.products)
        titles = {p["title"] for p in products}
        assert titles == {"Widget A", "Widget B"}

    def test_product_activation_updates_status(self):
        """Activating a product updates its status in the CategoryProducts projection."""
        category_id = _create_category(name="Toys")
        product_id = _create_product_in_category(category_id, sku="TOY-001", title="Action Figure")

        # Add a variant (required for activation)
        current_domain.process(
            AddVariant(product_id=product_id, variant_sku="TOY-V1", base_price=14.99),
            asynchronous=False,
        )

        current_domain.process(
            ActivateProduct(product_id=product_id),
            asynchronous=False,
        )

        view = current_domain.repository_for(CategoryProducts).get(category_id)
        products = json.loads(view.products)
        product = next(p for p in products if p["product_id"] == product_id)
        assert product["status"] == "active"

    def test_product_discontinuation_updates_status(self):
        """Discontinuing a product updates its status in the CategoryProducts projection."""
        category_id = _create_category(name="Food")
        product_id = _create_product_in_category(category_id, sku="FOOD-001", title="Organic Honey")

        # Activate first (requires variant)
        current_domain.process(
            AddVariant(product_id=product_id, variant_sku="FOOD-V1", base_price=9.99),
            asynchronous=False,
        )
        current_domain.process(
            ActivateProduct(product_id=product_id),
            asynchronous=False,
        )

        # Discontinue
        current_domain.process(
            DiscontinueProduct(product_id=product_id),
            asynchronous=False,
        )

        view = current_domain.repository_for(CategoryProducts).get(category_id)
        products = json.loads(view.products)
        product = next(p for p in products if p["product_id"] == product_id)
        assert product["status"] == "discontinued"

    def test_product_archival_updates_status(self):
        """Archiving a product updates its status in the CategoryProducts projection."""
        category_id = _create_category(name="Legacy")
        product_id = _create_product_in_category(category_id, sku="LEG-001", title="Old Widget")

        # Walk through lifecycle: activate, discontinue, archive
        current_domain.process(
            AddVariant(product_id=product_id, variant_sku="LEG-V1", base_price=5.0),
            asynchronous=False,
        )
        current_domain.process(ActivateProduct(product_id=product_id), asynchronous=False)
        current_domain.process(DiscontinueProduct(product_id=product_id), asynchronous=False)
        current_domain.process(ArchiveProduct(product_id=product_id), asynchronous=False)

        view = current_domain.repository_for(CategoryProducts).get(category_id)
        products = json.loads(view.products)
        product = next(p for p in products if p["product_id"] == product_id)
        assert product["status"] == "archived"

    def test_product_title_update_reflected_in_projection(self):
        """Updating a product's title should reflect in the CategoryProducts projection."""
        category_id = _create_category(name="Office")
        product_id = _create_product_in_category(category_id, sku="OFF-001", title="Desk Lamp")

        current_domain.process(
            UpdateProductDetails(product_id=product_id, title="Premium Desk Lamp"),
            asynchronous=False,
        )

        view = current_domain.repository_for(CategoryProducts).get(category_id)
        products = json.loads(view.products)
        product = next(p for p in products if p["product_id"] == product_id)
        assert product["title"] == "Premium Desk Lamp"

    def test_product_without_category_does_not_appear(self):
        """A product created without a category_id should not appear in any CategoryProducts."""
        category_id = _create_category(name="Empty Category")

        # Create a product without a category
        current_domain.process(
            CreateProduct(sku="NO-CAT-001", title="Uncategorized"),
            asynchronous=False,
        )

        view = current_domain.repository_for(CategoryProducts).get(category_id)
        assert view.product_count == 0


class TestCategoryProductsNotFound:
    """Mock-based: on_product_created returns early when category doesn't exist."""

    def test_on_product_created_returns_when_category_not_found(self):
        from unittest.mock import MagicMock, patch

        from catalogue.product.events import ProductCreated
        from catalogue.projections.category_products import CategoryProductsProjector
        from protean.exceptions import ObjectNotFoundError

        projector = CategoryProductsProjector()
        event = ProductCreated(
            product_id="prod-orphan-001",
            sku="ORPHAN-001",
            title="Orphan Product",
            category_id="nonexistent-category",
            status="Draft",
            created_at=datetime.now(UTC),
        )
        mock_repo = MagicMock()
        mock_repo.get.side_effect = ObjectNotFoundError({"_entity": "CategoryProducts not found"})

        with patch("catalogue.projections.category_products.current_domain") as mock_domain:
            mock_domain.repository_for = MagicMock(return_value=mock_repo)
            # Should not raise; returns early
            projector.on_product_created(event)
            # repo.add should NOT be called since we returned early
            mock_repo.add.assert_not_called()
