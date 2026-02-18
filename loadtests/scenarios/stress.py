"""Stress test scenarios for event pipeline saturation.

EventFloodUser generates maximum events per second to stress the
OutboxProcessor and Redis Streams consumers. SpikeUser simulates
sudden traffic bursts.
"""

from locust import HttpUser, constant_pacing, task

from loadtests.data_generators import (
    category_name,
    customer_name,
    product_data,
    unique_external_id,
    valid_email,
    variant_data,
)


class EventFloodUser(HttpUser):
    """Stress test: maximum event throughput.

    Each task generates 1+ domain events. No sequential dependencies —
    every task creates a new aggregate to avoid contention.

    Target: saturate the outbox table to test Engine drain rate.
    Monitor: protean_outbox_messages{status="PENDING"} should grow,
    then drain when engines are running.
    """

    wait_time = constant_pacing(0.1)  # ~10 requests/sec per user

    @task(5)
    def register_customer(self):
        """1 event: CustomerRegistered."""
        first, last = customer_name()
        self.client.post(
            "/customers",
            json={
                "external_id": unique_external_id(),
                "email": valid_email(),
                "first_name": first,
                "last_name": last,
            },
            name="[STRESS] POST /customers",
        )

    @task(3)
    def create_product(self):
        """1 event: ProductCreated."""
        self.client.post(
            "/products",
            json=product_data(),
            name="[STRESS] POST /products",
        )

    @task(2)
    def create_category(self):
        """1 event: CategoryCreated."""
        self.client.post(
            "/categories",
            json={"name": category_name()},
            name="[STRESS] POST /categories",
        )

    @task(4)
    def create_product_with_variant(self):
        """2 events: ProductCreated + VariantAdded."""
        resp = self.client.post(
            "/products",
            json=product_data(),
            name="[STRESS] POST /products+variant",
        )
        if resp.status_code == 201:
            pid = resp.json()["product_id"]
            self.client.post(
                f"/products/{pid}/variants",
                json=variant_data(),
                name="[STRESS] POST /products/{id}/variants",
            )


class SpikeUser(HttpUser):
    """Spike test: rapid-fire customer registration.

    Use with high user count and instant spawn rate to simulate
    sudden traffic bursts. Spawn 50-100 of these simultaneously
    to see how the system handles sudden load.
    """

    wait_time = constant_pacing(0.05)  # ~20 req/sec per user

    @task
    def rapid_registration(self):
        first, last = customer_name()
        self.client.post(
            "/customers",
            json={
                "external_id": unique_external_id(),
                "email": valid_email(),
                "first_name": first,
                "last_name": last,
            },
            name="[SPIKE] POST /customers",
        )
