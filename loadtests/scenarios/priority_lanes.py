"""Priority Lanes load test scenarios.

Exercise the priority-based event processing pipeline where production
events are processed before migration/backfill events.

Scenarios:
1. MigrationWithProductionTrafficUser — Mixed migration + production traffic
2. BackfillDrainRateUser — Measures backfill drain rate after burst
3. PriorityStarvationTestUser — Verifies production starves backfill
4. PriorityLanesDisabledBaseline — Baseline comparison without lanes

Enable priority lanes in domain.toml before running:
    [server.priority_lanes]
    enabled = true

Usage:
    locust -f loadtests/locustfile.py MigrationWithProductionTrafficUser
    locust -f loadtests/locustfile.py BackfillDrainRateUser
    locust -f loadtests/locustfile.py PriorityStarvationTestUser
    locust -f loadtests/locustfile.py PriorityLanesDisabledBaseline
"""

from locust import HttpUser, SequentialTaskSet, between, constant_pacing, task

from loadtests.data_generators import (
    customer_name,
    order_data,
    payment_data,
    product_data,
    unique_external_id,
    valid_email,
    valid_phone,
    webhook_data_success,
)
from loadtests.helpers.response import extract_error_detail
from loadtests.helpers.state import CrossDomainState

MIGRATION_PRIORITY_HEADER = {"X-Processing-Priority": "low"}


# ---------------------------------------------------------------------------
# SequentialTaskSet phases
# ---------------------------------------------------------------------------


class MigrationBulkImportPhase(SequentialTaskSet):
    """Simulates migration traffic with low-priority header.

    All requests carry X-Processing-Priority: low to signal that these
    are migration/backfill events that should yield to production traffic
    in the priority lanes pipeline.
    """

    @task
    def bulk_register_customers(self):
        """Register 10 customers per invocation as migration imports."""
        for _ in range(10):
            first, last = customer_name()
            self.client.post(
                "/customers",
                json={
                    "external_id": unique_external_id(),
                    "email": valid_email(),
                    "first_name": first,
                    "last_name": last,
                    "phone": valid_phone(),
                },
                headers=MIGRATION_PRIORITY_HEADER,
                name="[MIGRATION] POST /customers",
            )

    @task
    def bulk_create_products(self):
        """Create 5 products per invocation as migration imports."""
        for _ in range(5):
            self.client.post(
                "/products",
                json=product_data(),
                headers=MIGRATION_PRIORITY_HEADER,
                name="[MIGRATION] POST /products",
            )

    @task
    def done(self):
        self.interrupt()


class ProductionTrafficPhase(SequentialTaskSet):
    """Simulates normal production traffic (no priority header).

    Creates an order, confirms it, initiates payment, and processes
    the payment webhook — a typical production checkout flow.
    """

    def on_start(self):
        self.state = CrossDomainState()

    @task
    def create_order(self):
        payload = order_data()
        with self.client.post(
            "/orders",
            json=payload,
            catch_response=True,
            name="[PRODUCTION] POST /orders",
        ) as resp:
            if resp.status_code == 201:
                self.state.order_id = resp.json()["order_id"]
                self.state.customer_id = payload["customer_id"]
            else:
                resp.failure(f"Create order failed: {extract_error_detail(resp)}")
                self.interrupt()

    @task
    def confirm_order(self):
        with self.client.put(
            f"/orders/{self.state.order_id}/confirm",
            catch_response=True,
            name="[PRODUCTION] PUT /orders/{id}/confirm",
        ) as resp:
            if resp.status_code != 200:
                resp.failure(f"Confirm failed: {extract_error_detail(resp)}")
                self.interrupt()

    @task
    def initiate_payment(self):
        payload = payment_data(
            order_id=self.state.order_id,
            customer_id=self.state.customer_id,
        )
        with self.client.post(
            "/payments",
            json=payload,
            catch_response=True,
            name="[PRODUCTION] POST /payments",
        ) as resp:
            if resp.status_code == 201:
                self.state.payment_id = resp.json()["payment_id"]
            else:
                resp.failure(f"Initiate payment failed: {extract_error_detail(resp)}")
                self.interrupt()

    @task
    def payment_webhook(self):
        payload = webhook_data_success(self.state.payment_id)
        with self.client.post(
            "/payments/webhook",
            json=payload,
            headers={"X-Gateway-Signature": "test-signature"},
            catch_response=True,
            name="[PRODUCTION] POST /payments/webhook",
        ) as resp:
            if resp.status_code != 200:
                resp.failure(f"Payment webhook failed: {extract_error_detail(resp)}")

    @task
    def done(self):
        self.interrupt()


# ---------------------------------------------------------------------------
# HttpUser classes
# ---------------------------------------------------------------------------


class MigrationWithProductionTrafficUser(HttpUser):
    """Mixed workload: 70% migration bulk imports, 30% production traffic.

    Simulates a real-world scenario where a data migration runs alongside
    normal production operations. Priority lanes should ensure production
    events (orders, payments) are processed before migration events
    (bulk customer/product imports).

    Monitor:
    - Production event latency should remain low
    - Migration events should queue up in the backfill lane
    - Overall throughput should not degrade significantly
    """

    wait_time = between(0.5, 2.0)
    tasks = {MigrationBulkImportPhase: 7, ProductionTrafficPhase: 3}


class BackfillDrainRateUser(HttpUser):
    """Measures backfill drain rate after an initial burst of migration events.

    Seeds 100 migration events (customers with low-priority header) in a
    burst during on_start, then switches to light production traffic only.
    This lets you measure how fast the backfill lane drains when production
    load is minimal.

    Monitor:
    - Time to drain 100 backfill events
    - Production order latency during drain
    - protean_outbox_messages{priority="low"} gauge
    """

    wait_time = constant_pacing(0.5)  # 2 req/sec per user

    def on_start(self):
        """Seed 100 migration events in a burst."""
        for _ in range(100):
            first, last = customer_name()
            self.client.post(
                "/customers",
                json={
                    "external_id": unique_external_id(),
                    "email": valid_email(),
                    "first_name": first,
                    "last_name": last,
                    "phone": valid_phone(),
                },
                headers=MIGRATION_PRIORITY_HEADER,
                name="[DRAIN] POST /customers (seed)",
            )

    @task
    def production_order(self):
        """Generate light production traffic while backfill drains."""
        self.client.post(
            "/orders",
            json=order_data(),
            name="[DRAIN] POST /orders",
        )


class PriorityStarvationTestUser(HttpUser):
    """Verifies that continuous production traffic starves backfill.

    Generates aggressive production traffic (orders + customers) alongside
    a smaller stream of migration events. With priority lanes enabled,
    the migration events should be stuck in the backfill lane while
    production events are processed promptly.

    Monitor:
    - Migration event processing latency vs production latency
    - Backfill lane queue depth should grow
    - Production throughput should remain stable
    """

    wait_time = constant_pacing(0.1)  # 10 req/sec per user — aggressive

    @task(6)
    def production_order(self):
        """High-volume production order creation."""
        self.client.post(
            "/orders",
            json=order_data(),
            name="[STARVE-PROD] POST /orders",
        )

    @task(2)
    def production_customer(self):
        """Production customer registration (normal priority)."""
        first, last = customer_name()
        self.client.post(
            "/customers",
            json={
                "external_id": unique_external_id(),
                "email": valid_email(),
                "first_name": first,
                "last_name": last,
                "phone": valid_phone(),
            },
            name="[STARVE-PROD] POST /customers",
        )

    @task(2)
    def migration_customer(self):
        """Migration customer import (low priority — should be starved)."""
        first, last = customer_name()
        self.client.post(
            "/customers",
            json={
                "external_id": unique_external_id(),
                "email": valid_email(),
                "first_name": first,
                "last_name": last,
                "phone": valid_phone(),
            },
            headers=MIGRATION_PRIORITY_HEADER,
            name="[STARVE-MIGRATION] POST /customers",
        )


class PriorityLanesDisabledBaseline(HttpUser):
    """Baseline comparison: same workload WITHOUT priority headers.

    Generates the same traffic mix as MigrationWithProductionTrafficUser
    but without any X-Processing-Priority headers. All events are treated
    equally by the pipeline. Compare metrics against the priority-lanes-
    enabled runs to measure the impact of lane separation.

    Monitor:
    - Overall throughput and latency distribution
    - Compare p50/p95/p99 against MigrationWithProductionTrafficUser
    - Event processing should be FIFO (no lane separation)
    """

    wait_time = between(0.5, 2.0)

    @task(7)
    def bulk_customers(self):
        """Register 3 customers per call — no priority header (baseline)."""
        for _ in range(3):
            first, last = customer_name()
            self.client.post(
                "/customers",
                json={
                    "external_id": unique_external_id(),
                    "email": valid_email(),
                    "first_name": first,
                    "last_name": last,
                    "phone": valid_phone(),
                },
                name="[BASELINE] POST /customers",
            )

    @task(3)
    def production_order(self):
        """Production order creation — no priority header (baseline)."""
        self.client.post(
            "/orders",
            json=order_data(),
            name="[BASELINE] POST /orders",
        )
