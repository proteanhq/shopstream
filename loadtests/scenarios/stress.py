"""Stress test scenarios for event pipeline saturation.

EventFloodUser generates maximum events per second to stress the
OutboxProcessor and Redis Streams consumers. SpikeUser simulates
sudden traffic bursts. CrossDomainFloodUser hits all five domains.
"""

import uuid

from locust import HttpUser, constant_pacing, task

from loadtests.data_generators import (
    category_name,
    customer_name,
    initialize_stock_data,
    order_data,
    payment_data,
    product_data,
    unique_external_id,
    valid_email,
    variant_data,
    warehouse_data,
    webhook_data_success,
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

    @task(3)
    def create_order(self):
        """1 event: OrderCreated."""
        self.client.post(
            "/orders",
            json=order_data(),
            name="[STRESS] POST /orders",
        )

    @task(3)
    def initialize_inventory(self):
        """1 event: StockInitialized."""
        self.client.post(
            "/inventory",
            json=initialize_stock_data(),
            name="[STRESS] POST /inventory",
        )

    @task(2)
    def create_payment(self):
        """1 event: PaymentInitiated."""
        self.client.post(
            "/payments",
            json=payment_data(),
            name="[STRESS] POST /payments",
        )

    @task(2)
    def create_warehouse(self):
        """1 event: WarehouseCreated."""
        self.client.post(
            "/warehouses",
            json=warehouse_data(),
            name="[STRESS] POST /warehouses",
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


class CrossDomainFloodUser(HttpUser):
    """Stress test hitting all five domains with equal pressure.

    Unlike EventFloodUser which focuses on identity + catalogue,
    this user distributes load evenly across all bounded contexts.
    Useful for finding which domain's outbox drains slowest.
    """

    wait_time = constant_pacing(0.1)  # ~10 req/sec per user

    @task(4)
    def register_customer(self):
        first, last = customer_name()
        self.client.post(
            "/customers",
            json={
                "external_id": unique_external_id(),
                "email": valid_email(),
                "first_name": first,
                "last_name": last,
            },
            name="[X-FLOOD] POST /customers",
        )

    @task(4)
    def create_product_variant(self):
        resp = self.client.post(
            "/products",
            json=product_data(),
            name="[X-FLOOD] POST /products",
        )
        if resp.status_code == 201:
            pid = resp.json()["product_id"]
            self.client.post(
                f"/products/{pid}/variants",
                json=variant_data(),
                name="[X-FLOOD] POST /products/{id}/variants",
            )

    @task(4)
    def create_order_confirm(self):
        resp = self.client.post(
            "/orders",
            json=order_data(),
            name="[X-FLOOD] POST /orders",
        )
        if resp.status_code == 201:
            oid = resp.json()["order_id"]
            self.client.put(
                f"/orders/{oid}/confirm",
                name="[X-FLOOD] PUT /orders/{id}/confirm",
            )

    @task(4)
    def inventory_init_receive(self):
        resp = self.client.post(
            "/inventory",
            json=initialize_stock_data(initial_quantity=100),
            name="[X-FLOOD] POST /inventory",
        )
        if resp.status_code == 201:
            iid = resp.json()["inventory_item_id"]
            self.client.put(
                f"/inventory/{iid}/receive",
                json={"quantity": 50, "reference": f"PO-{uuid.uuid4().hex[:6]}"},
                name="[X-FLOOD] PUT /inventory/{id}/receive",
            )

    @task(4)
    def payment_initiate_webhook(self):
        resp = self.client.post(
            "/payments",
            json=payment_data(),
            name="[X-FLOOD] POST /payments",
        )
        if resp.status_code == 201:
            pid = resp.json()["payment_id"]
            self.client.post(
                "/payments/webhook",
                json=webhook_data_success(pid),
                headers={"X-Gateway-Signature": "test-signature"},
                name="[X-FLOOD] POST /payments/webhook",
            )
