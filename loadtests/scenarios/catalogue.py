"""Catalogue domain load test scenarios.

Three stateful SequentialTaskSet journeys covering product catalog building,
product lifecycle, and category hierarchy management. Steps execute in order —
each depends on the previous step succeeding.
"""

import random

from locust import HttpUser, SequentialTaskSet, between, task

from loadtests.data_generators import (
    category_name,
    image_data,
    product_data,
    variant_data,
)
from loadtests.helpers.state import CategoryState, ProductState


class ProductCatalogBuilder(SequentialTaskSet):
    """Create Product -> Add Variants -> Add Images -> Activate.

    Models a seller building out a product listing.
    Generates 6 events: ProductCreated, VariantAdded (x2),
    ProductImageAdded (x2), ProductActivated.
    """

    def on_start(self):
        self.state = ProductState()

    @task
    def create_product(self):
        payload = product_data()
        with self.client.post(
            "/products",
            json=payload,
            catch_response=True,
            name="POST /products",
        ) as resp:
            if resp.status_code == 201:
                self.state.product_id = resp.json()["product_id"]
            else:
                resp.failure(f"Create product failed: {resp.status_code}")
                self.interrupt()

    @task
    def add_variant_1(self):
        with self.client.post(
            f"/products/{self.state.product_id}/variants",
            json=variant_data(),
            catch_response=True,
            name="POST /products/{id}/variants",
        ) as resp:
            if resp.status_code == 201:
                self.state.variant_count += 1
            else:
                resp.failure(f"Add variant failed: {resp.status_code}")

    @task
    def add_variant_2(self):
        with self.client.post(
            f"/products/{self.state.product_id}/variants",
            json=variant_data(),
            catch_response=True,
            name="POST /products/{id}/variants",
        ) as resp:
            if resp.status_code == 201:
                self.state.variant_count += 1
            else:
                resp.failure(f"Add variant 2 failed: {resp.status_code}")

    @task
    def add_primary_image(self):
        with self.client.post(
            f"/products/{self.state.product_id}/images",
            json=image_data(is_primary=True),
            catch_response=True,
            name="POST /products/{id}/images",
        ) as resp:
            if resp.status_code == 201:
                self.state.image_count += 1
            else:
                resp.failure(f"Add image failed: {resp.status_code}")

    @task
    def add_secondary_image(self):
        with self.client.post(
            f"/products/{self.state.product_id}/images",
            json=image_data(is_primary=False),
            catch_response=True,
            name="POST /products/{id}/images",
        ) as resp:
            if resp.status_code == 201:
                self.state.image_count += 1
            else:
                resp.failure(f"Add second image failed: {resp.status_code}")

    @task
    def activate_product(self):
        with self.client.put(
            f"/products/{self.state.product_id}/activate",
            catch_response=True,
            name="PUT /products/{id}/activate",
        ) as resp:
            if resp.status_code == 200:
                self.state.current_status = "Active"
            else:
                resp.failure(f"Activate failed: {resp.status_code}")

    @task
    def done(self):
        self.interrupt()


class ProductLifecycleJourney(SequentialTaskSet):
    """Create -> Add Variant -> Activate -> Discontinue -> Archive.

    Exercises the full product state machine:
    Draft -> Active -> Discontinued -> Archived.
    Generates 5 events: ProductCreated, VariantAdded,
    ProductActivated, ProductDiscontinued, ProductArchived.
    """

    def on_start(self):
        self.state = ProductState()

    @task
    def create(self):
        payload = product_data()
        with self.client.post(
            "/products",
            json=payload,
            catch_response=True,
            name="POST /products",
        ) as resp:
            if resp.status_code == 201:
                self.state.product_id = resp.json()["product_id"]
            else:
                resp.failure(f"Create product failed: {resp.status_code}")
                self.interrupt()

    @task
    def add_variant(self):
        with self.client.post(
            f"/products/{self.state.product_id}/variants",
            json=variant_data(),
            catch_response=True,
            name="POST /products/{id}/variants",
        ) as resp:
            if resp.status_code != 201:
                resp.failure(f"Add variant failed: {resp.status_code}")
                self.interrupt()

    @task
    def activate(self):
        with self.client.put(
            f"/products/{self.state.product_id}/activate",
            catch_response=True,
            name="PUT /products/{id}/activate",
        ) as resp:
            if resp.status_code != 200:
                resp.failure(f"Activate failed: {resp.status_code}")
                self.interrupt()

    @task
    def discontinue(self):
        with self.client.put(
            f"/products/{self.state.product_id}/discontinue",
            catch_response=True,
            name="PUT /products/{id}/discontinue",
        ) as resp:
            if resp.status_code != 200:
                resp.failure(f"Discontinue failed: {resp.status_code}")

    @task
    def archive(self):
        with self.client.put(
            f"/products/{self.state.product_id}/archive",
            catch_response=True,
            name="PUT /products/{id}/archive",
        ) as resp:
            if resp.status_code != 200:
                resp.failure(f"Archive failed: {resp.status_code}")

    @task
    def done(self):
        self.interrupt()


class CategoryHierarchyBuilder(SequentialTaskSet):
    """Create root -> child -> grandchild -> update -> reorder -> deactivate.

    Tests category depth up to 3 levels (max is 5).
    Generates 6 events: CategoryCreated (x3), CategoryDetailsUpdated,
    CategoryReordered, CategoryDeactivated.
    """

    def on_start(self):
        self.state = CategoryState()

    @task
    def create_root(self):
        with self.client.post(
            "/categories",
            json={"name": category_name()},
            catch_response=True,
            name="POST /categories",
        ) as resp:
            if resp.status_code == 201:
                self.state.category_ids.append(resp.json()["category_id"])
            else:
                resp.failure(f"Create root category failed: {resp.status_code}")
                self.interrupt()

    @task
    def create_child(self):
        with self.client.post(
            "/categories",
            json={
                "name": category_name(),
                "parent_category_id": self.state.category_ids[0],
            },
            catch_response=True,
            name="POST /categories",
        ) as resp:
            if resp.status_code == 201:
                self.state.category_ids.append(resp.json()["category_id"])
            else:
                resp.failure(f"Create child category failed: {resp.status_code}")

    @task
    def create_grandchild(self):
        with self.client.post(
            "/categories",
            json={
                "name": category_name(),
                "parent_category_id": self.state.category_ids[1],
                "attributes": "season=summer",
            },
            catch_response=True,
            name="POST /categories",
        ) as resp:
            if resp.status_code == 201:
                self.state.category_ids.append(resp.json()["category_id"])
            else:
                resp.failure(f"Create grandchild failed: {resp.status_code}")

    @task
    def update_root(self):
        with self.client.put(
            f"/categories/{self.state.category_ids[0]}",
            json={"name": category_name(), "attributes": "updated=true"},
            catch_response=True,
            name="PUT /categories/{id}",
        ) as resp:
            if resp.status_code != 200:
                resp.failure(f"Update category failed: {resp.status_code}")

    @task
    def reorder_leaf(self):
        with self.client.put(
            f"/categories/{self.state.category_ids[-1]}/reorder",
            json={"new_display_order": random.randint(1, 100)},
            catch_response=True,
            name="PUT /categories/{id}/reorder",
        ) as resp:
            if resp.status_code != 200:
                resp.failure(f"Reorder failed: {resp.status_code}")

    @task
    def deactivate_leaf(self):
        with self.client.put(
            f"/categories/{self.state.category_ids[-1]}/deactivate",
            catch_response=True,
            name="PUT /categories/{id}/deactivate",
        ) as resp:
            if resp.status_code != 200:
                resp.failure(f"Deactivate failed: {resp.status_code}")

    @task
    def done(self):
        self.interrupt()


class CatalogueUser(HttpUser):
    """Locust user simulating Catalogue domain interactions.

    Weighted distribution:
    - 50% Product Catalog Builder (most common seller activity)
    - 25% Product Lifecycle
    - 25% Category Hierarchy Builder
    """

    wait_time = between(0.5, 2.0)
    tasks = {
        ProductCatalogBuilder: 5,
        ProductLifecycleJourney: 2,
        CategoryHierarchyBuilder: 3,
    }
