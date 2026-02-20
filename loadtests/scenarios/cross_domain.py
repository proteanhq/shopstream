"""Cross-domain load test scenarios targeting race conditions.

These scenarios weave threads across multiple bounded contexts, exercising
the same resources concurrently to surface race conditions, version
conflicts, and saga failure modes described in the domain specification.

Scenarios:
1. EndToEndOrderJourney — Full happy path: Customer → Product → Stock →
   Cart → Order → Payment → Ship → Deliver
2. FlashSaleStampede — N users competing for limited inventory
3. CancelDuringPayment — Cancel arrives while payment webhook is in-flight
4. ConcurrentCheckout — Two users checkout the same cart/product
5. OrderPaymentSaga — Full saga: order + reserve stock + pay + confirm
"""

import random
import uuid

from locust import HttpUser, SequentialTaskSet, between, constant_pacing, task

from loadtests.data_generators import (
    customer_name,
    initialize_stock_data,
    invoice_data,
    order_data,
    order_item,
    payment_data,
    product_data,
    reserve_stock_data,
    shipment_data,
    unique_external_id,
    valid_email,
    valid_phone,
    variant_data,
    warehouse_data,
    webhook_data_failure,
    webhook_data_success,
)
from loadtests.helpers.response import extract_error_detail
from loadtests.helpers.state import CrossDomainState


class EndToEndOrderJourney(SequentialTaskSet):
    """Complete cross-domain order lifecycle.

    Thread: Identity → Catalogue → Inventory → Ordering → Payments → Ordering

    1. Register a customer
    2. Create a product with variant
    3. Create warehouse + initialize stock
    4. Create a cart, add items, checkout
    5. Create order, confirm, initiate payment
    6. Payment webhook success
    7. Ship and deliver

    This journey generates 15+ events across 5 bounded contexts
    and exercises the DomainContextMiddleware routing under load.
    """

    def on_start(self):
        self.state = CrossDomainState()

    @task
    def register_customer(self):
        first, last = customer_name()
        with self.client.post(
            "/customers",
            json={
                "external_id": unique_external_id(),
                "email": valid_email(),
                "first_name": first,
                "last_name": last,
                "phone": valid_phone(),
            },
            catch_response=True,
            name="[E2E] POST /customers",
        ) as resp:
            if resp.status_code == 201:
                self.state.customer_id = resp.json()["customer_id"]
            else:
                resp.failure(f"Register failed: {extract_error_detail(resp)}")
                self.interrupt()

    @task
    def create_product(self):
        with self.client.post(
            "/products",
            json=product_data(),
            catch_response=True,
            name="[E2E] POST /products",
        ) as resp:
            if resp.status_code == 201:
                self.state.product_id = resp.json()["product_id"]
            else:
                resp.failure(f"Create product failed: {extract_error_detail(resp)}")
                self.interrupt()

    @task
    def add_variant(self):
        vd = variant_data()
        with self.client.post(
            f"/products/{self.state.product_id}/variants",
            json=vd,
            catch_response=True,
            name="[E2E] POST /products/{id}/variants",
        ) as resp:
            if resp.status_code == 201:
                self.state.variant_id = vd["variant_sku"]  # Track variant
            else:
                resp.failure(f"Add variant failed: {extract_error_detail(resp)}")

    @task
    def activate_product(self):
        with self.client.put(
            f"/products/{self.state.product_id}/activate",
            catch_response=True,
            name="[E2E] PUT /products/{id}/activate",
        ) as resp:
            if resp.status_code != 200:
                resp.failure(f"Activate product failed: {extract_error_detail(resp)}")

    @task
    def create_warehouse(self):
        with self.client.post(
            "/warehouses",
            json=warehouse_data(),
            catch_response=True,
            name="[E2E] POST /warehouses",
        ) as resp:
            if resp.status_code == 201:
                self.state.warehouse_id = resp.json()["warehouse_id"]
            else:
                resp.failure(f"Create warehouse failed: {extract_error_detail(resp)}")

    @task
    def initialize_stock(self):
        payload = initialize_stock_data(
            product_id=self.state.product_id,
            variant_id=self.state.variant_id or f"var-{uuid.uuid4().hex[:8]}",
            warehouse_id=self.state.warehouse_id or f"wh-{uuid.uuid4().hex[:8]}",
            initial_quantity=100,
        )
        with self.client.post(
            "/inventory",
            json=payload,
            catch_response=True,
            name="[E2E] POST /inventory",
        ) as resp:
            if resp.status_code == 201:
                self.state.inventory_item_id = resp.json()["inventory_item_id"]
            else:
                resp.failure(f"Init stock failed: {extract_error_detail(resp)}")

    @task
    def create_order(self):
        payload = order_data(customer_id=self.state.customer_id, num_items=2)
        with self.client.post(
            "/orders",
            json=payload,
            catch_response=True,
            name="[E2E] POST /orders",
        ) as resp:
            if resp.status_code == 201:
                self.state.order_id = resp.json()["order_id"]
            else:
                resp.failure(f"Create order failed: {extract_error_detail(resp)}")
                self.interrupt()

    @task
    def reserve_stock(self):
        if not self.state.inventory_item_id:
            return
        payload = reserve_stock_data(order_id=self.state.order_id, quantity=2)
        with self.client.post(
            f"/inventory/{self.state.inventory_item_id}/reserve",
            json=payload,
            catch_response=True,
            name="[E2E] POST /inventory/{id}/reserve",
        ) as resp:
            if resp.status_code != 201:
                resp.failure(f"Reserve stock failed: {extract_error_detail(resp)}")

    @task
    def confirm_order(self):
        with self.client.put(
            f"/orders/{self.state.order_id}/confirm",
            catch_response=True,
            name="[E2E] PUT /orders/{id}/confirm",
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
            name="[E2E] POST /payments",
        ) as resp:
            if resp.status_code == 201:
                self.state.payment_id = resp.json()["payment_id"]
            else:
                resp.failure(f"Initiate payment failed: {extract_error_detail(resp)}")
                self.interrupt()

    @task
    def record_payment_pending(self):
        with self.client.put(
            f"/orders/{self.state.order_id}/payment/pending",
            json={
                "payment_id": self.state.payment_id,
                "payment_method": "credit_card",
            },
            catch_response=True,
            name="[E2E] PUT /orders/{id}/payment/pending",
        ) as resp:
            if resp.status_code != 200:
                resp.failure(f"Payment pending failed: {extract_error_detail(resp)}")

    @task
    def payment_webhook_success(self):
        payload = webhook_data_success(self.state.payment_id)
        with self.client.post(
            "/payments/webhook",
            json=payload,
            catch_response=True,
            name="[E2E] POST /payments/webhook",
        ) as resp:
            if resp.status_code != 200:
                resp.failure(f"Payment webhook failed: {extract_error_detail(resp)}")

    @task
    def record_payment_success(self):
        with self.client.put(
            f"/orders/{self.state.order_id}/payment/success",
            json={
                "payment_id": self.state.payment_id,
                "amount": round(random.uniform(29.99, 199.99), 2),
                "payment_method": "credit_card",
            },
            catch_response=True,
            name="[E2E] PUT /orders/{id}/payment/success",
        ) as resp:
            if resp.status_code != 200:
                resp.failure(f"Payment success failed: {extract_error_detail(resp)}")

    @task
    def ship_order(self):
        with self.client.put(
            f"/orders/{self.state.order_id}/ship",
            json=shipment_data(),
            catch_response=True,
            name="[E2E] PUT /orders/{id}/ship",
        ) as resp:
            if resp.status_code != 200:
                resp.failure(f"Ship failed: {extract_error_detail(resp)}")

    @task
    def deliver_order(self):
        with self.client.put(
            f"/orders/{self.state.order_id}/deliver",
            catch_response=True,
            name="[E2E] PUT /orders/{id}/deliver",
        ) as resp:
            if resp.status_code != 200:
                resp.failure(f"Deliver failed: {extract_error_detail(resp)}")

    @task
    def generate_invoice(self):
        payload = invoice_data(
            order_id=self.state.order_id,
            customer_id=self.state.customer_id,
        )
        with self.client.post(
            "/invoices",
            json=payload,
            catch_response=True,
            name="[E2E] POST /invoices",
        ) as resp:
            if resp.status_code != 201:
                pass  # Invoice generation is non-critical

    @task
    def done(self):
        self.interrupt()


class FlashSaleStampede(SequentialTaskSet):
    """Race condition: N users competing for limited inventory.

    Per the domain spec (Phase 3 — Flash Sale Scenario):
    Multiple users try to reserve the last few units simultaneously.
    Optimistic locking should cause version conflicts and retries.

    Each user creates their own order but all reserve from the SAME
    shared inventory item (created once in on_start via class variable).

    Expected behavior:
    - Some reservations succeed (first-come-first-served via version)
    - Some fail with version conflicts / insufficient stock
    - The system should remain consistent (no overselling)
    """

    # Shared inventory item — all users compete for this
    _shared_inventory_item_id = None
    _shared_warehouse_id = None
    _setup_done = False

    def on_start(self):
        # First user sets up the shared inventory item with limited stock
        if not FlashSaleStampede._setup_done:
            FlashSaleStampede._setup_done = True
            self._setup_shared_inventory()

    def _setup_shared_inventory(self):
        """Create a warehouse and inventory item with limited stock (10 units)."""
        wh_resp = self.client.post(
            "/warehouses",
            json=warehouse_data(),
            name="[FLASH] POST /warehouses (setup)",
        )
        if wh_resp.status_code == 201:
            FlashSaleStampede._shared_warehouse_id = wh_resp.json()["warehouse_id"]

        payload = initialize_stock_data(
            warehouse_id=FlashSaleStampede._shared_warehouse_id,
            initial_quantity=10,  # Only 10 units — many users will fight for these
        )
        inv_resp = self.client.post(
            "/inventory",
            json=payload,
            name="[FLASH] POST /inventory (setup)",
        )
        if inv_resp.status_code == 201:
            FlashSaleStampede._shared_inventory_item_id = inv_resp.json()["inventory_item_id"]

    @task
    def rush_reserve(self):
        """Each user tries to grab 1-3 units — most will fail."""
        if not FlashSaleStampede._shared_inventory_item_id:
            self.interrupt()
            return

        qty = random.randint(1, 3)
        order_id = f"flash-ord-{uuid.uuid4().hex[:8]}"

        with self.client.post(
            f"/inventory/{FlashSaleStampede._shared_inventory_item_id}/reserve",
            json=reserve_stock_data(order_id=order_id, quantity=qty),
            catch_response=True,
            name="[FLASH] POST /inventory/{id}/reserve (RACE)",
        ) as resp:
            if resp.status_code == 201:
                resp.success()  # Won the race
            elif resp.status_code in (409, 422, 400):
                # Expected: version conflict or insufficient stock
                resp.success()  # Mark as success — this IS the expected race behavior
            else:
                resp.failure(f"Unexpected error: {resp.status_code} — {extract_error_detail(resp)}")

    @task
    def done(self):
        self.interrupt()


class CancelDuringPaymentJourney(SequentialTaskSet):
    """Race condition: Cancel arrives while payment is in-flight.

    Per the domain spec (Phase 2 — Scenario 2: Cancel During Payment):
    Customer cancels while payment gateway is processing.
    PaymentSucceeded webhook arrives after cancellation.

    This journey deliberately creates a race:
    1. Create order → confirm → payment pending
    2. Fire cancel AND payment webhook in rapid succession
    3. Observe which one wins (order state machine should handle both)
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
            name="[RACE-CANCEL] POST /orders",
        ) as resp:
            if resp.status_code == 201:
                self.state.order_id = resp.json()["order_id"]
            else:
                resp.failure(f"Create order failed: {extract_error_detail(resp)}")
                self.interrupt()

    @task
    def confirm_order(self):
        with self.client.put(
            f"/orders/{self.state.order_id}/confirm",
            catch_response=True,
            name="[RACE-CANCEL] PUT /orders/{id}/confirm",
        ) as resp:
            if resp.status_code != 200:
                resp.failure(f"Confirm failed: {extract_error_detail(resp)}")
                self.interrupt()

    @task
    def initiate_payment(self):
        payload = payment_data(order_id=self.state.order_id)
        with self.client.post(
            "/payments",
            json=payload,
            catch_response=True,
            name="[RACE-CANCEL] POST /payments",
        ) as resp:
            if resp.status_code == 201:
                self.state.payment_id = resp.json()["payment_id"]
            else:
                resp.failure(f"Initiate payment failed: {extract_error_detail(resp)}")
                self.interrupt()

    @task
    def payment_pending(self):
        with self.client.put(
            f"/orders/{self.state.order_id}/payment/pending",
            json={
                "payment_id": self.state.payment_id,
                "payment_method": "credit_card",
            },
            catch_response=True,
            name="[RACE-CANCEL] PUT /orders/{id}/payment/pending",
        ) as resp:
            if resp.status_code != 200:
                resp.failure(f"Payment pending failed: {extract_error_detail(resp)}")
                self.interrupt()

    @task
    def race_cancel_vs_payment(self):
        """Fire cancel and payment success — whichever arrives first wins.

        We intentionally don't await one before the other. Under load,
        these requests hit the server near-simultaneously, creating the
        exact race condition described in the spec.
        """
        # Cancel the order (customer-initiated)
        with self.client.put(
            f"/orders/{self.state.order_id}/cancel",
            json={"reason": "Changed my mind", "cancelled_by": "customer"},
            catch_response=True,
            name="[RACE-CANCEL] PUT /orders/{id}/cancel (RACE)",
        ) as resp:
            if resp.status_code in (200, 400, 409, 422):
                resp.success()  # Any of these is valid in a race
            else:
                resp.failure(f"Cancel race unexpected: {resp.status_code}")

        # Payment webhook arrives "from gateway" — may conflict with cancel
        payload = webhook_data_success(self.state.payment_id)
        with self.client.post(
            "/payments/webhook",
            json=payload,
            catch_response=True,
            name="[RACE-CANCEL] POST /payments/webhook (RACE)",
        ) as resp:
            if resp.status_code in (200, 400, 409, 422):
                resp.success()  # Any of these is valid in a race
            else:
                resp.failure(f"Webhook race unexpected: {resp.status_code}")

    @task
    def done(self):
        self.interrupt()


class ConcurrentOrderModificationJourney(SequentialTaskSet):
    """Race condition: Multiple modifications to the same order.

    Per the domain spec (Phase 2 — Scenario 3: Modify Order During Confirmation):
    Multiple operations hit the same order simultaneously — adding items,
    removing items, and confirming the order at the same time.

    Exercises optimistic locking on the event-sourced Order aggregate.
    """

    def on_start(self):
        self.state = CrossDomainState()

    @task
    def create_order(self):
        payload = order_data(num_items=3)
        with self.client.post(
            "/orders",
            json=payload,
            catch_response=True,
            name="[RACE-MOD] POST /orders",
        ) as resp:
            if resp.status_code == 201:
                self.state.order_id = resp.json()["order_id"]
            else:
                resp.failure(f"Create order failed: {extract_error_detail(resp)}")
                self.interrupt()

    @task
    def concurrent_modifications(self):
        """Fire multiple modifications and a confirm simultaneously."""
        order_id = self.state.order_id

        # Add a new item
        item = order_item()
        with self.client.post(
            f"/orders/{order_id}/items",
            json=item,
            catch_response=True,
            name="[RACE-MOD] POST /orders/{id}/items (RACE)",
        ) as resp:
            if resp.status_code in (200, 400, 409, 422):
                resp.success()
            else:
                resp.failure(f"Add item race: {resp.status_code}")

        # Simultaneously try to confirm
        with self.client.put(
            f"/orders/{order_id}/confirm",
            catch_response=True,
            name="[RACE-MOD] PUT /orders/{id}/confirm (RACE)",
        ) as resp:
            if resp.status_code in (200, 400, 409, 422):
                resp.success()
            else:
                resp.failure(f"Confirm race: {resp.status_code}")

        # Another add item — may conflict with confirm
        item2 = order_item()
        with self.client.post(
            f"/orders/{order_id}/items",
            json=item2,
            catch_response=True,
            name="[RACE-MOD] POST /orders/{id}/items (RACE-2)",
        ) as resp:
            if resp.status_code in (200, 400, 409, 422):
                resp.success()
            else:
                resp.failure(f"Add item race 2: {resp.status_code}")

    @task
    def done(self):
        self.interrupt()


class SagaOrderCheckoutJourney(SequentialTaskSet):
    """Order Checkout Saga — the full distributed transaction.

    Per the domain spec (Phase 4 — Order-Payment Saga):
    1. Create order
    2. Reserve inventory
    3. Initiate payment
    4. Payment succeeds → confirm order
    5. Payment fails → release inventory → cancel order

    This journey randomly decides success/failure to exercise both
    the happy path and compensation logic.
    """

    def on_start(self):
        self.state = CrossDomainState()
        self.payment_succeeds = random.random() < 0.7  # 70% success

    @task
    def setup_inventory(self):
        """Create warehouse + stock for this saga."""
        wh_resp = self.client.post(
            "/warehouses",
            json=warehouse_data(),
            name="[SAGA] POST /warehouses",
        )
        if wh_resp.status_code == 201:
            self.state.warehouse_id = wh_resp.json()["warehouse_id"]

        payload = initialize_stock_data(
            warehouse_id=self.state.warehouse_id,
            initial_quantity=50,
        )
        inv_resp = self.client.post(
            "/inventory",
            json=payload,
            name="[SAGA] POST /inventory",
        )
        if inv_resp.status_code == 201:
            self.state.inventory_item_id = inv_resp.json()["inventory_item_id"]

    @task
    def create_order(self):
        payload = order_data()
        self.state.customer_id = payload["customer_id"]
        with self.client.post(
            "/orders",
            json=payload,
            catch_response=True,
            name="[SAGA] POST /orders",
        ) as resp:
            if resp.status_code == 201:
                self.state.order_id = resp.json()["order_id"]
            else:
                resp.failure(f"Create order failed: {extract_error_detail(resp)}")
                self.interrupt()

    @task
    def reserve_inventory(self):
        """Step 1 of saga: Reserve stock."""
        if not self.state.inventory_item_id:
            return
        payload = reserve_stock_data(order_id=self.state.order_id, quantity=2)
        with self.client.post(
            f"/inventory/{self.state.inventory_item_id}/reserve",
            json=payload,
            catch_response=True,
            name="[SAGA] POST /inventory/{id}/reserve",
        ) as resp:
            if resp.status_code == 201:
                pass  # Reservation succeeded
            else:
                # Reservation failed → cancel order (compensation)
                self.client.put(
                    f"/orders/{self.state.order_id}/cancel",
                    json={"reason": "Out of stock", "cancelled_by": "system"},
                    name="[SAGA] PUT /orders/{id}/cancel (compensation)",
                )
                self.interrupt()

    @task
    def confirm_order(self):
        with self.client.put(
            f"/orders/{self.state.order_id}/confirm",
            catch_response=True,
            name="[SAGA] PUT /orders/{id}/confirm",
        ) as resp:
            if resp.status_code != 200:
                resp.failure(f"Confirm failed: {extract_error_detail(resp)}")
                self.interrupt()

    @task
    def initiate_payment(self):
        """Step 2 of saga: Initiate payment."""
        payload = payment_data(
            order_id=self.state.order_id,
            customer_id=self.state.customer_id,
        )
        with self.client.post(
            "/payments",
            json=payload,
            catch_response=True,
            name="[SAGA] POST /payments",
        ) as resp:
            if resp.status_code == 201:
                self.state.payment_id = resp.json()["payment_id"]
            else:
                resp.failure(f"Initiate payment failed: {extract_error_detail(resp)}")
                self.interrupt()

    @task
    def payment_pending(self):
        with self.client.put(
            f"/orders/{self.state.order_id}/payment/pending",
            json={
                "payment_id": self.state.payment_id,
                "payment_method": "credit_card",
            },
            catch_response=True,
            name="[SAGA] PUT /orders/{id}/payment/pending",
        ) as resp:
            if resp.status_code != 200:
                resp.failure(f"Payment pending failed: {extract_error_detail(resp)}")

    @task
    def payment_result(self):
        """Step 3 of saga: Payment succeeds or fails (randomly determined)."""
        if self.payment_succeeds:
            # Happy path: payment succeeds
            payload = webhook_data_success(self.state.payment_id)
            self.client.post(
                "/payments/webhook",
                json=payload,
                name="[SAGA] POST /payments/webhook (success)",
            )
            self.client.put(
                f"/orders/{self.state.order_id}/payment/success",
                json={
                    "payment_id": self.state.payment_id,
                    "amount": round(random.uniform(29.99, 199.99), 2),
                    "payment_method": "credit_card",
                },
                name="[SAGA] PUT /orders/{id}/payment/success",
            )
        else:
            # Failure path: payment fails → compensate
            payload = webhook_data_failure(self.state.payment_id)
            self.client.post(
                "/payments/webhook",
                json=payload,
                name="[SAGA] POST /payments/webhook (failure)",
            )
            self.client.put(
                f"/orders/{self.state.order_id}/payment/failure",
                json={
                    "payment_id": self.state.payment_id,
                    "reason": "Card declined",
                },
                name="[SAGA] PUT /orders/{id}/payment/failure",
            )
            # Compensation: cancel order
            self.client.put(
                f"/orders/{self.state.order_id}/cancel",
                json={"reason": "Payment failed", "cancelled_by": "system"},
                name="[SAGA] PUT /orders/{id}/cancel (compensation)",
            )

    @task
    def done(self):
        self.interrupt()


# ---------------------------------------------------------------------------
# HttpUser classes
# ---------------------------------------------------------------------------


class CrossDomainUser(HttpUser):
    """Realistic cross-domain workload exercising all bounded contexts.

    Weight distribution:
    - 40% End-to-end order (the most realistic journey)
    - 30% Saga checkout (distributed transaction)
    - 15% Cancel during payment (race condition)
    - 15% Concurrent modifications (race condition)
    """

    wait_time = between(1.0, 3.0)
    tasks = {
        EndToEndOrderJourney: 8,
        SagaOrderCheckoutJourney: 6,
        CancelDuringPaymentJourney: 3,
        ConcurrentOrderModificationJourney: 3,
    }


class FlashSaleUser(HttpUser):
    """Flash sale simulation: many users competing for limited stock.

    Each user runs the FlashSaleStampede which tries to reserve
    from a shared inventory item with only 10 units.
    Launch 20-50 of these simultaneously.

    Monitor:
    - 409 / version conflict rate
    - Reservation success vs failure ratio
    - Inventory item final state consistency
    """

    wait_time = constant_pacing(0.2)  # 5 req/sec per user
    tasks = [FlashSaleStampede]


class RaceConditionUser(HttpUser):
    """Targeted race condition exerciser.

    Runs the three race condition scenarios from the domain spec
    with aggressive timing to maximize conflict probability.
    """

    wait_time = between(0.3, 1.0)
    tasks = {
        CancelDuringPaymentJourney: 4,
        ConcurrentOrderModificationJourney: 4,
        FlashSaleStampede: 2,
    }
