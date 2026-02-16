"""Application tests for product lifecycle handlers."""

import pytest
from catalogue.product.creation import CreateProduct
from catalogue.product.lifecycle import ActivateProduct, ArchiveProduct, DiscontinueProduct
from catalogue.product.product import Product
from catalogue.product.variants import AddVariant
from protean.exceptions import ValidationError
from protean.utils.globals import current_domain


def _create_product(**overrides):
    defaults = {"sku": "PROD-001", "title": "Test Product"}
    defaults.update(overrides)
    command = CreateProduct(**defaults)
    return current_domain.process(command, asynchronous=False)


def _add_variant(product_id, **overrides):
    defaults = {"product_id": product_id, "variant_sku": "VAR-001", "base_price": 29.99}
    defaults.update(overrides)
    command = AddVariant(**defaults)
    current_domain.process(command, asynchronous=False)


def _create_active_product():
    product_id = _create_product()
    _add_variant(product_id)
    current_domain.process(ActivateProduct(product_id=product_id), asynchronous=False)
    return product_id


class TestActivateProductHandler:
    def test_activate_product(self):
        product_id = _create_product()
        _add_variant(product_id)

        current_domain.process(ActivateProduct(product_id=product_id), asynchronous=False)

        product = current_domain.repository_for(Product).get(product_id)
        assert product.status == "Active"

    def test_activate_without_variants_rejected(self):
        product_id = _create_product()
        with pytest.raises(ValidationError):
            current_domain.process(ActivateProduct(product_id=product_id), asynchronous=False)


class TestDiscontinueProductHandler:
    def test_discontinue_product(self):
        product_id = _create_active_product()

        current_domain.process(DiscontinueProduct(product_id=product_id), asynchronous=False)

        product = current_domain.repository_for(Product).get(product_id)
        assert product.status == "Discontinued"

    def test_discontinue_draft_rejected(self):
        product_id = _create_product()
        with pytest.raises(ValidationError):
            current_domain.process(DiscontinueProduct(product_id=product_id), asynchronous=False)


class TestArchiveProductHandler:
    def test_archive_product(self):
        product_id = _create_active_product()
        current_domain.process(DiscontinueProduct(product_id=product_id), asynchronous=False)

        current_domain.process(ArchiveProduct(product_id=product_id), asynchronous=False)

        product = current_domain.repository_for(Product).get(product_id)
        assert product.status == "Archived"

    def test_archive_active_rejected(self):
        product_id = _create_active_product()
        with pytest.raises(ValidationError):
            current_domain.process(ArchiveProduct(product_id=product_id), asynchronous=False)


class TestFullLifecycleThroughHandlers:
    def test_draft_to_archived(self):
        product_id = _create_product()
        _add_variant(product_id)

        current_domain.process(ActivateProduct(product_id=product_id), asynchronous=False)
        current_domain.process(DiscontinueProduct(product_id=product_id), asynchronous=False)
        current_domain.process(ArchiveProduct(product_id=product_id), asynchronous=False)

        product = current_domain.repository_for(Product).get(product_id)
        assert product.status == "Archived"
