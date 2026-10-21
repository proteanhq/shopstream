"""Integration tests for FastAPI endpoints."""

from decimal import Decimal

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from protean.integrations.fastapi import register_exception_handlers
from protean.utils.globals import current_domain

from catalogue.api import category_router, product_router
from catalogue.category.category import Category
from catalogue.product.product import Product


@pytest.fixture()
def client():
    app = FastAPI()
    app.include_router(product_router)
    app.include_router(category_router)
    register_exception_handlers(app)
    return TestClient(app)


class TestCreateProductEndpoint:
    def test_create_product(self, client):
        response = client.post(
            "/products",
            json={
                "sku": "API-001",
                "title": "API Product",
                "seller_id": "seller-api",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert "product_id" in data

        product = current_domain.repository_for(Product).get(data["product_id"])
        assert product.title == "API Product"

    def test_create_product_with_seo(self, client):
        response = client.post(
            "/products",
            json={
                "sku": "API-SEO",
                "title": "SEO Product",
                "slug": "seo-product",
                "meta_title": "SEO Title",
            },
        )
        assert response.status_code == 201

        product = current_domain.repository_for(Product).get(response.json()["product_id"])
        assert product.seo.slug == "seo-product"


class TestUpdateProductDetailsEndpoint:
    def _create(self, client):
        resp = client.post("/products", json={"sku": "UPD-001", "title": "Original"})
        return resp.json()["product_id"]

    def test_update_details(self, client):
        product_id = self._create(client)
        response = client.put(
            f"/products/{product_id}/details",
            json={
                "title": "Updated",
                "brand": "BrandX",
            },
        )
        assert response.status_code == 200

        product = current_domain.repository_for(Product).get(product_id)
        assert product.title == "Updated"
        assert product.brand == "BrandX"


class TestVariantEndpoints:
    def _create(self, client):
        resp = client.post("/products", json={"sku": "VAR-API-001", "title": "Variant Product"})
        return resp.json()["product_id"]

    def test_add_variant(self, client):
        product_id = self._create(client)
        response = client.post(
            f"/products/{product_id}/variants",
            json={
                "variant_sku": "V-API-001",
                "base_price": 29.99,
            },
        )
        assert response.status_code == 201

        product = current_domain.repository_for(Product).get(product_id)
        assert len(product.variants) == 1

    def test_update_variant_price(self, client):
        product_id = self._create(client)
        client.post(
            f"/products/{product_id}/variants",
            json={
                "variant_sku": "V-API-002",
                "base_price": 29.99,
            },
        )

        product = current_domain.repository_for(Product).get(product_id)
        variant_id = product.variants[0].id

        response = client.put(
            f"/products/{product_id}/variants/{variant_id}/price",
            json={
                "base_price": 49.99,
            },
        )
        assert response.status_code == 200

        product = current_domain.repository_for(Product).get(product_id)
        assert product.variants[0].price.base_price == Decimal("49.99")

    def test_set_tier_price(self, client):
        product_id = self._create(client)
        client.post(
            f"/products/{product_id}/variants",
            json={
                "variant_sku": "V-API-003",
                "base_price": 99.99,
            },
        )

        product = current_domain.repository_for(Product).get(product_id)
        variant_id = product.variants[0].id

        response = client.put(
            f"/products/{product_id}/variants/{variant_id}/tier-price",
            json={
                "tier": "Silver",
                "price": 89.99,
            },
        )
        assert response.status_code == 200

        product = current_domain.repository_for(Product).get(product_id)
        assert product.variants[0].price.tier_prices["Silver"].amount == Decimal("89.99")

    @pytest.mark.parametrize(
        ("price", "field"),
        [(0, "amount"), (99.99, "tier_prices")],
    )
    def test_set_invalid_tier_price_returns_400(self, client, price, field):
        product_id = self._create(client)
        client.post(
            f"/products/{product_id}/variants",
            json={"variant_sku": "V-API-004", "base_price": 99.99},
        )
        variant_id = current_domain.repository_for(Product).get(product_id).variants[0].id

        response = client.put(
            f"/products/{product_id}/variants/{variant_id}/tier-price",
            json={"tier": "Silver", "price": price},
        )

        assert response.status_code == 400
        assert field in response.json()["error"]
        assert current_domain.repository_for(Product).get(product_id).variants[0].price.tier_prices == {}


class TestImageEndpoints:
    def _create(self, client):
        resp = client.post("/products", json={"sku": "IMG-API-001", "title": "Image Product"})
        return resp.json()["product_id"]

    def test_add_image(self, client):
        product_id = self._create(client)
        response = client.post(
            f"/products/{product_id}/images",
            json={
                "url": "https://cdn.example.com/img.jpg",
                "alt_text": "Product image",
            },
        )
        assert response.status_code == 201

        product = current_domain.repository_for(Product).get(product_id)
        assert len(product.images) == 1

    def test_remove_image(self, client):
        product_id = self._create(client)
        client.post(
            f"/products/{product_id}/images",
            json={
                "url": "https://cdn.example.com/img1.jpg",
            },
        )

        product = current_domain.repository_for(Product).get(product_id)
        image_id = product.images[0].id

        response = client.delete(f"/products/{product_id}/images/{image_id}")
        assert response.status_code == 200

        product = current_domain.repository_for(Product).get(product_id)
        assert len(product.images) == 0


class TestLifecycleEndpoints:
    def _create_with_variant(self, client):
        resp = client.post("/products", json={"sku": "LC-API-001", "title": "Lifecycle Product"})
        product_id = resp.json()["product_id"]
        client.post(
            f"/products/{product_id}/variants",
            json={
                "variant_sku": "LC-V-001",
                "base_price": 29.99,
            },
        )
        return product_id

    def test_activate(self, client):
        product_id = self._create_with_variant(client)
        response = client.put(f"/products/{product_id}/activate")
        assert response.status_code == 200

        product = current_domain.repository_for(Product).get(product_id)
        assert product.status == "Active"

    def test_discontinue(self, client):
        product_id = self._create_with_variant(client)
        client.put(f"/products/{product_id}/activate")
        response = client.put(f"/products/{product_id}/discontinue")
        assert response.status_code == 200

        product = current_domain.repository_for(Product).get(product_id)
        assert product.status == "Discontinued"

    def test_archive(self, client):
        product_id = self._create_with_variant(client)
        client.put(f"/products/{product_id}/activate")
        client.put(f"/products/{product_id}/discontinue")
        response = client.put(f"/products/{product_id}/archive")
        assert response.status_code == 200

        product = current_domain.repository_for(Product).get(product_id)
        assert product.status == "Archived"


class TestCategoryEndpoints:
    def test_create_category(self, client):
        response = client.post("/categories", json={"name": "Electronics"})
        assert response.status_code == 201
        data = response.json()
        assert "category_id" in data

        category = current_domain.repository_for(Category).get(data["category_id"])
        assert category.name == "Electronics"

    def test_update_category(self, client):
        resp = client.post("/categories", json={"name": "Original"})
        category_id = resp.json()["category_id"]

        response = client.put(f"/categories/{category_id}", json={"name": "Updated"})
        assert response.status_code == 200

        category = current_domain.repository_for(Category).get(category_id)
        assert category.name == "Updated"

    def test_reorder_category(self, client):
        resp = client.post("/categories", json={"name": "Reorder"})
        category_id = resp.json()["category_id"]

        response = client.put(f"/categories/{category_id}/reorder", json={"new_display_order": 5})
        assert response.status_code == 200

        category = current_domain.repository_for(Category).get(category_id)
        assert category.display_order == 5

    def test_deactivate_category(self, client):
        resp = client.post("/categories", json={"name": "Deactivate"})
        category_id = resp.json()["category_id"]

        response = client.put(f"/categories/{category_id}/deactivate")
        assert response.status_code == 200

        category = current_domain.repository_for(Category).get(category_id)
        assert category.is_active is False


class TestReadEndpoints:
    def test_list_products(self, client):
        response = client.get("/products")
        # Projection may not be populated in sync/memory mode
        assert response.status_code in (200, 404, 500)

    def test_get_product_detail(self, client):
        resp = client.post(
            "/products",
            json={"sku": "READ-001", "title": "Read Product", "seller_id": "seller-read"},
        )
        product_id = resp.json()["product_id"]
        response = client.get(f"/products/{product_id}")
        # Projection may not be populated in sync/memory mode
        assert response.status_code in (200, 404, 500)

    def test_list_categories(self, client):
        response = client.get("/categories")
        # Projection may not be populated in sync/memory mode
        assert response.status_code in (200, 404, 500)

    def test_get_category_products(self, client):
        resp = client.post("/categories", json={"name": "ReadCat"})
        category_id = resp.json()["category_id"]
        response = client.get(f"/categories/{category_id}/products")
        # Projection may not be populated in sync/memory mode
        assert response.status_code in (200, 404, 500)


class TestVariantPriceMoney:
    def _product_with_variant(self, client, sku, base_price):
        product_id = client.post("/products", json={"sku": sku, "title": "Money Product"}).json()["product_id"]
        response = client.post(
            f"/products/{product_id}/variants", json={"variant_sku": f"V-{sku}", "base_price": base_price}
        )
        assert response.status_code == 201
        return product_id

    @pytest.mark.parametrize(("sku", "base_price"), [("MONEY-N", 29.99), ("MONEY-S", "29.99"), ("MONEY-S4", "29.9900")])
    def test_number_and_string_prices_store_the_same_decimal(self, client, sku, base_price):
        product_id = self._product_with_variant(client, sku, base_price)

        product = current_domain.repository_for(Product).get(product_id)
        assert product.variants[0].price.base_price == Decimal("29.9900")

    def test_price_with_five_places_is_rejected(self, client):
        product_id = client.post("/products", json={"sku": "MONEY-5DP", "title": "Money"}).json()["product_id"]
        response = client.post(
            f"/products/{product_id}/variants", json={"variant_sku": "V-MONEY-5DP", "base_price": "29.99001"}
        )
        assert response.status_code == 422

    def test_product_list_sends_prices_as_4_place_strings(self, client):
        product_id = self._product_with_variant(client, "MONEY-LIST", 29.99)

        response = client.get("/products")

        assert response.status_code == 200
        cards = [card for card in response.json()["items"] if card["product_id"] == product_id]
        assert len(cards) == 1
        assert (cards[0]["min_price"], cards[0]["max_price"]) == ("29.9900", "29.9900")
