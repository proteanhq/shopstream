"""Integration tests for FastAPI endpoints."""

import pytest
from catalogue.api import category_router, product_router
from catalogue.category.category import Category
from catalogue.product.product import Product
from fastapi import FastAPI
from fastapi.testclient import TestClient
from protean.utils.globals import current_domain


@pytest.fixture()
def client():
    app = FastAPI()
    app.include_router(product_router)
    app.include_router(category_router)
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
        assert product.variants[0].price.base_price == 49.99

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
