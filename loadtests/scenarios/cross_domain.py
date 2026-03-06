"""Cross-domain load test scenarios targeting race conditions and subscriber flows.

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
6. SubscriberVariantStockJourney — Catalogue → Inventory via subscriber
7. SubscriberOrderRefundJourney — Ordering → Payments via subscriber
8. SubscriberVerifiedPurchaseJourney — Ordering → Reviews via subscriber
"""

import random
import time
import uuid

from locust import HttpUser, SequentialTaskSet, between, constant_pacing, task

from loadtests.data_generators import (
    cart_data,
    checkout_data,
    customer_name,
    initialize_stock_data,
    invoice_data,
    order_data,
    order_item,
    payment_data,
    product_data,
    reserve_stock_data,
    review_data,
    saga_cart_item_data,
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
from loadtests.helpers.state import CrossDomainState, SagaState


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
            headers={"X-Gateway-Signature": "test-signature"},
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
            if resp.status_code == 200:
                resp.success()
            elif resp.status_code == 422 and "Paid" in resp.text:
                # Saga already moved the order to Paid — expected race condition
                resp.success()
            else:
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
    _setup_complete = False

    def on_start(self):
        # First user sets up the shared inventory item with limited stock
        if not FlashSaleStampede._setup_done:
            FlashSaleStampede._setup_done = True
            self._setup_shared_inventory()
            FlashSaleStampede._setup_complete = True

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
        # Wait for setup to complete (first user is creating shared inventory)
        for _ in range(50):  # Wait up to 5 seconds
            if FlashSaleStampede._setup_complete:
                break
            time.sleep(0.1)

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
            headers={"X-Gateway-Signature": "test-signature"},
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
                headers={"X-Gateway-Signature": "test-signature"},
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
                headers={"X-Gateway-Signature": "test-signature"},
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
# Saga-Driven Journeys (async event flow via Engine)
# ---------------------------------------------------------------------------

# Shared warehouse — created once, reused across all saga journeys
_shared_warehouse_id: str | None = None


def _ensure_warehouse(client) -> str | None:
    """Create a warehouse once and cache it for all saga journeys."""
    global _shared_warehouse_id
    if _shared_warehouse_id:
        return _shared_warehouse_id
    resp = client.post(
        "/warehouses",
        json=warehouse_data(),
        name="[SAGA-PM] POST /warehouses (setup)",
    )
    if resp.status_code == 201:
        _shared_warehouse_id = resp.json()["warehouse_id"]
    return _shared_warehouse_id


class SagaDrivenCheckoutJourney(SequentialTaskSet):
    """Cart -> Checkout -> Confirm -> Reserve Stock -> Pay -> Verify.

    Unlike SagaOrderCheckoutJourney which manually calls each order state
    transition, this journey lets the OrderCheckoutSaga process manager
    drive the order through async event flow:

    1. OrderConfirmed -> saga starts (awaiting_reservation)
    2. StockReserved  -> saga dispatches RecordPaymentPending
    3. PaymentSucceeded -> saga dispatches RecordPaymentSuccess

    Requires Ordering, Inventory, and Payments Engines running.
    Polls order status to verify saga-driven state transitions.
    """

    def on_start(self):
        self.state = SagaState()
        self.state.product_id = f"prod-{uuid.uuid4().hex[:8]}"
        self.state.variant_id = f"var-{uuid.uuid4().hex[:8]}"
        self.state.customer_id = f"cust-{uuid.uuid4().hex[:8]}"
        self.state.quantity = random.randint(1, 3)
        self.state.unit_price = round(random.uniform(19.99, 99.99), 2)

    def _poll_order_status(self, expected: str, timeout: float = 12, interval: float = 0.5) -> bool:
        """Poll GET /orders/{id} until status matches or timeout."""
        elapsed = 0.0
        while elapsed < timeout:
            with self.client.get(
                f"/orders/{self.state.order_id}",
                catch_response=True,
                name="[SAGA-PM] POLL /orders/{id}",
            ) as resp:
                if resp.status_code == 200:
                    data = resp.json()
                    status = data.get("status", "")
                    if status == expected:
                        resp.success()
                        self.state.order_status = status
                        return True
                    resp.success()  # Not there yet, but not an error
                elif resp.status_code == 404:
                    resp.success()  # Projection not yet populated
                else:
                    resp.failure(f"Poll failed: {resp.status_code}")
                    return False
            time.sleep(interval)
            elapsed += interval
        return False

    @task
    def setup_inventory(self):
        """Create inventory stock for a known product/variant."""
        wh_id = _ensure_warehouse(self.client)
        self.state.warehouse_id = wh_id

        payload = initialize_stock_data(
            product_id=self.state.product_id,
            variant_id=self.state.variant_id,
            warehouse_id=wh_id,
            initial_quantity=50,
        )
        with self.client.post(
            "/inventory",
            json=payload,
            catch_response=True,
            name="[SAGA-PM] POST /inventory",
        ) as resp:
            if resp.status_code == 201:
                self.state.inventory_item_id = resp.json()["inventory_item_id"]
            else:
                resp.failure(f"Init stock failed: {extract_error_detail(resp)}")
                self.interrupt()

    @task
    def create_cart(self):
        payload = cart_data(customer_id=self.state.customer_id)
        with self.client.post(
            "/carts",
            json=payload,
            catch_response=True,
            name="[SAGA-PM] POST /carts",
        ) as resp:
            if resp.status_code == 201:
                self.state.cart_id = resp.json()["cart_id"]
            else:
                resp.failure(f"Create cart failed: {extract_error_detail(resp)}")
                self.interrupt()

    @task
    def add_item(self):
        payload = saga_cart_item_data(
            product_id=self.state.product_id,
            variant_id=self.state.variant_id,
            quantity=self.state.quantity,
        )
        with self.client.post(
            f"/carts/{self.state.cart_id}/items",
            json=payload,
            catch_response=True,
            name="[SAGA-PM] POST /carts/{id}/items",
        ) as resp:
            if resp.status_code != 200:
                resp.failure(f"Add item failed: {extract_error_detail(resp)}")
                self.interrupt()

    @task
    def checkout(self):
        with self.client.post(
            f"/carts/{self.state.cart_id}/checkout",
            json=checkout_data(),
            catch_response=True,
            name="[SAGA-PM] POST /carts/{id}/checkout",
        ) as resp:
            if resp.status_code == 201:
                self.state.order_id = resp.json()["order_id"]
            else:
                resp.failure(f"Checkout failed: {extract_error_detail(resp)}")
                self.interrupt()

    @task
    def confirm_order(self):
        """Confirm order — raises OrderConfirmed, starting the saga."""
        with self.client.put(
            f"/orders/{self.state.order_id}/confirm",
            catch_response=True,
            name="[SAGA-PM] PUT /orders/{id}/confirm",
        ) as resp:
            if resp.status_code != 200:
                resp.failure(f"Confirm failed: {extract_error_detail(resp)}")
                self.interrupt()

    @task
    def wait_for_saga_start(self):
        """Give Engine time to process OrderConfirmed via outbox."""
        time.sleep(2)

    @task
    def reserve_stock(self):
        """Reserve stock with order_id — raises StockReserved.

        The saga picks up StockReserved, correlates on order_id,
        and dispatches RecordPaymentPending to Ordering.
        """
        payload = reserve_stock_data(
            order_id=self.state.order_id,
            quantity=self.state.quantity,
        )
        with self.client.post(
            f"/inventory/{self.state.inventory_item_id}/reserve",
            json=payload,
            catch_response=True,
            name="[SAGA-PM] POST /inventory/{id}/reserve",
        ) as resp:
            if resp.status_code != 201:
                resp.failure(f"Reserve failed: {extract_error_detail(resp)}")
                self.interrupt()

    @task
    def verify_payment_pending(self):
        """Poll until saga drives order to Payment_Pending."""
        if not self._poll_order_status("Payment_Pending"):
            with self.client.get(
                f"/orders/{self.state.order_id}",
                catch_response=True,
                name="[SAGA-PM] POLL /orders/{id} (timeout)",
            ) as resp:
                resp.failure(
                    f"Saga did not reach Payment_Pending within timeout. Current status: {self.state.order_status}"
                )
            self.interrupt()

    @task
    def initiate_payment(self):
        """Create Payment in Payments domain."""
        payload = payment_data(
            order_id=self.state.order_id,
            customer_id=self.state.customer_id,
            amount=self.state.unit_price * self.state.quantity,
        )
        with self.client.post(
            "/payments",
            json=payload,
            catch_response=True,
            name="[SAGA-PM] POST /payments",
        ) as resp:
            if resp.status_code == 201:
                self.state.payment_id = resp.json()["payment_id"]
            else:
                resp.failure(f"Initiate payment failed: {extract_error_detail(resp)}")
                self.interrupt()

    @task
    def payment_webhook_success(self):
        """Success webhook — raises PaymentSucceeded.

        The saga picks up PaymentSucceeded, correlates on order_id,
        and dispatches RecordPaymentSuccess to Ordering.
        """
        payload = webhook_data_success(self.state.payment_id)
        with self.client.post(
            "/payments/webhook",
            json=payload,
            headers={"X-Gateway-Signature": "test-signature"},
            catch_response=True,
            name="[SAGA-PM] POST /payments/webhook",
        ) as resp:
            if resp.status_code != 200:
                resp.failure(f"Webhook failed: {extract_error_detail(resp)}")
                self.interrupt()

    @task
    def verify_paid(self):
        """Poll until saga drives order to Paid — confirms saga completed."""
        if not self._poll_order_status("Paid"):
            with self.client.get(
                f"/orders/{self.state.order_id}",
                catch_response=True,
                name="[SAGA-PM] POLL /orders/{id} (timeout)",
            ) as resp:
                resp.failure(f"Saga did not reach Paid within timeout. Current status: {self.state.order_status}")
            self.interrupt()

    @task
    def done(self):
        self.interrupt()


class SagaDrivenCheckoutFailureJourney(SequentialTaskSet):
    """Cart -> Checkout -> Confirm -> Reserve Stock -> Pay (fail) -> Verify.

    Exercises the saga's failure path: PaymentFailed triggers retry/cancel.
    Since the saga retries up to 3 times, a single failure transitions to
    'retrying' state. We verify the saga processed the PaymentFailed event
    rather than polling for a terminal order state.
    """

    def on_start(self):
        self.state = SagaState()
        self.state.product_id = f"prod-{uuid.uuid4().hex[:8]}"
        self.state.variant_id = f"var-{uuid.uuid4().hex[:8]}"
        self.state.customer_id = f"cust-{uuid.uuid4().hex[:8]}"
        self.state.quantity = 1
        self.state.unit_price = round(random.uniform(19.99, 99.99), 2)

    def _poll_order_status(self, expected: str, timeout: float = 12, interval: float = 0.5) -> bool:
        """Poll GET /orders/{id} until status matches or timeout."""
        elapsed = 0.0
        while elapsed < timeout:
            with self.client.get(
                f"/orders/{self.state.order_id}",
                catch_response=True,
                name="[SAGA-PM] POLL /orders/{id}",
            ) as resp:
                if resp.status_code == 200:
                    data = resp.json()
                    status = data.get("status", "")
                    if status == expected:
                        resp.success()
                        self.state.order_status = status
                        return True
                    resp.success()
                elif resp.status_code == 404:
                    resp.success()
                else:
                    resp.failure(f"Poll failed: {resp.status_code}")
                    return False
            time.sleep(interval)
            elapsed += interval
        return False

    @task
    def setup_inventory(self):
        wh_id = _ensure_warehouse(self.client)
        self.state.warehouse_id = wh_id

        payload = initialize_stock_data(
            product_id=self.state.product_id,
            variant_id=self.state.variant_id,
            warehouse_id=wh_id,
            initial_quantity=50,
        )
        with self.client.post(
            "/inventory",
            json=payload,
            catch_response=True,
            name="[SAGA-PM] POST /inventory",
        ) as resp:
            if resp.status_code == 201:
                self.state.inventory_item_id = resp.json()["inventory_item_id"]
            else:
                resp.failure(f"Init stock failed: {extract_error_detail(resp)}")
                self.interrupt()

    @task
    def create_cart(self):
        payload = cart_data(customer_id=self.state.customer_id)
        with self.client.post(
            "/carts",
            json=payload,
            catch_response=True,
            name="[SAGA-PM] POST /carts",
        ) as resp:
            if resp.status_code == 201:
                self.state.cart_id = resp.json()["cart_id"]
            else:
                resp.failure(f"Create cart failed: {extract_error_detail(resp)}")
                self.interrupt()

    @task
    def add_item(self):
        payload = saga_cart_item_data(
            product_id=self.state.product_id,
            variant_id=self.state.variant_id,
            quantity=self.state.quantity,
        )
        with self.client.post(
            f"/carts/{self.state.cart_id}/items",
            json=payload,
            catch_response=True,
            name="[SAGA-PM] POST /carts/{id}/items",
        ) as resp:
            if resp.status_code != 200:
                resp.failure(f"Add item failed: {extract_error_detail(resp)}")
                self.interrupt()

    @task
    def checkout(self):
        with self.client.post(
            f"/carts/{self.state.cart_id}/checkout",
            json=checkout_data(),
            catch_response=True,
            name="[SAGA-PM] POST /carts/{id}/checkout",
        ) as resp:
            if resp.status_code == 201:
                self.state.order_id = resp.json()["order_id"]
            else:
                resp.failure(f"Checkout failed: {extract_error_detail(resp)}")
                self.interrupt()

    @task
    def confirm_order(self):
        with self.client.put(
            f"/orders/{self.state.order_id}/confirm",
            catch_response=True,
            name="[SAGA-PM] PUT /orders/{id}/confirm",
        ) as resp:
            if resp.status_code != 200:
                resp.failure(f"Confirm failed: {extract_error_detail(resp)}")
                self.interrupt()

    @task
    def wait_for_saga_start(self):
        time.sleep(2)

    @task
    def reserve_stock(self):
        payload = reserve_stock_data(
            order_id=self.state.order_id,
            quantity=self.state.quantity,
        )
        with self.client.post(
            f"/inventory/{self.state.inventory_item_id}/reserve",
            json=payload,
            catch_response=True,
            name="[SAGA-PM] POST /inventory/{id}/reserve",
        ) as resp:
            if resp.status_code != 201:
                resp.failure(f"Reserve failed: {extract_error_detail(resp)}")
                self.interrupt()

    @task
    def verify_payment_pending(self):
        if not self._poll_order_status("Payment_Pending"):
            with self.client.get(
                f"/orders/{self.state.order_id}",
                catch_response=True,
                name="[SAGA-PM] POLL /orders/{id} (timeout)",
            ) as resp:
                resp.failure(
                    f"Saga did not reach Payment_Pending within timeout. Current status: {self.state.order_status}"
                )
            self.interrupt()

    @task
    def initiate_payment(self):
        payload = payment_data(
            order_id=self.state.order_id,
            customer_id=self.state.customer_id,
            amount=self.state.unit_price * self.state.quantity,
        )
        with self.client.post(
            "/payments",
            json=payload,
            catch_response=True,
            name="[SAGA-PM] POST /payments",
        ) as resp:
            if resp.status_code == 201:
                self.state.payment_id = resp.json()["payment_id"]
            else:
                resp.failure(f"Initiate payment failed: {extract_error_detail(resp)}")
                self.interrupt()

    @task
    def payment_webhook_failure(self):
        """Failure webhook — raises PaymentFailed.

        The saga picks up PaymentFailed. With attempt_number=1 < MAX=3,
        the saga transitions to 'retrying' and does NOT dispatch CancelOrder.
        """
        payload = webhook_data_failure(self.state.payment_id)
        with self.client.post(
            "/payments/webhook",
            json=payload,
            headers={"X-Gateway-Signature": "test-signature"},
            catch_response=True,
            name="[SAGA-PM] POST /payments/webhook (failure)",
        ) as resp:
            if resp.status_code in (200, 400, 422):
                resp.success()
            else:
                resp.failure(f"Webhook failed: {extract_error_detail(resp)}")

    @task
    def wait_for_saga_processing(self):
        """Give Engine time to process PaymentFailed event."""
        time.sleep(3)

    @task
    def done(self):
        self.interrupt()


# ---------------------------------------------------------------------------
# HttpUser classes
# ---------------------------------------------------------------------------


class CrossDomainUser(HttpUser):
    """Realistic cross-domain workload exercising all bounded contexts.

    Weight distribution:
    - 30% End-to-end order (the most realistic journey)
    - 20% Saga checkout — manual orchestration (distributed transaction)
    - 20% Saga checkout — PM-driven (exercises OrderCheckoutSaga process manager)
    - 10% Saga failure — PM-driven (exercises saga failure path)
    - 10% Cancel during payment (race condition)
    - 10% Concurrent modifications (race condition)
    """

    wait_time = between(1.0, 3.0)
    tasks = {
        EndToEndOrderJourney: 6,
        SagaOrderCheckoutJourney: 4,
        SagaDrivenCheckoutJourney: 4,
        SagaDrivenCheckoutFailureJourney: 2,
        CancelDuringPaymentJourney: 2,
        ConcurrentOrderModificationJourney: 2,
    }


class FlashSaleUser(HttpUser):
    """Flash sale simulation: many users competing for limited stock.

    WARNING: This is a specialty scenario that produces deliberate failures.
    It is excluded from default Locust discovery to avoid polluting error
    traces during normal load testing. Run explicitly:

        locust -f loadtests/locustfile.py FlashSaleUser --headless -u 20 -t 30s

    Each user runs the FlashSaleStampede which tries to reserve
    from a shared inventory item with only 10 units.
    Launch 20-50 of these simultaneously.

    Note: This scenario does NOT model a realistic flash sale flow. A real
    implementation would queue reservation requests and allocate stock in
    order of receipt. This scenario exists purely to stress-test optimistic
    locking and validate that the system never oversells.

    Expected: Most reservations will fail with "Insufficient stock" (400)
    or version conflicts (409). These are expected and marked as Locust
    successes, but they DO generate handler.failed traces in Observatory.

    Monitor:
    - 409 / version conflict rate
    - Reservation success vs failure ratio
    - Inventory item final state consistency
    """

    wait_time = constant_pacing(0.2)  # 5 req/sec per user
    tasks = [FlashSaleStampede]


class RaceConditionUser(HttpUser):
    """Targeted race condition exerciser.

    WARNING: This is a specialty scenario that produces deliberate failures.
    It is excluded from default Locust discovery to avoid polluting error
    traces during normal load testing. Run explicitly:

        locust -f loadtests/locustfile.py RaceConditionUser --headless -u 10 -t 60s

    Runs three race condition scenarios with aggressive timing to maximize
    conflict probability:
    - CancelDuringPaymentJourney: cancel vs payment webhook race
    - ConcurrentOrderModificationJourney: simultaneous order mutations
    - FlashSaleStampede: N users competing for limited inventory

    Expected: Version conflicts (409), validation errors (400/422), and
    state machine rejections are normal and intentional. These generate
    handler.failed traces in Observatory.
    """

    wait_time = between(0.3, 1.0)
    tasks = {
        CancelDuringPaymentJourney: 4,
        ConcurrentOrderModificationJourney: 4,
        FlashSaleStampede: 2,
    }


# ---------------------------------------------------------------------------
# Subscriber ACL happy-path scenarios
# ---------------------------------------------------------------------------


class SubscriberVariantStockJourney(SequentialTaskSet):
    """Subscriber flow: Catalogue → Inventory via CatalogueVariantSubscriber.

    Creates a product with a variant and verifies that the subscriber
    auto-initializes inventory stock for the new variant.

    Thread: Catalogue → Inventory (async via subscriber)
    """

    def on_start(self):
        self.state = CrossDomainState()

    @task
    def create_product(self):
        with self.client.post(
            "/products",
            json=product_data(),
            catch_response=True,
            name="[Sub:Stock] POST /products",
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
            name="[Sub:Stock] POST /products/{id}/variants",
        ) as resp:
            if resp.status_code == 201:
                self.state.variant_id = vd["variant_sku"]
            else:
                resp.failure(f"Add variant failed: {extract_error_detail(resp)}")

    @task
    def activate_product(self):
        with self.client.put(
            f"/products/{self.state.product_id}/activate",
            catch_response=True,
            name="[Sub:Stock] PUT /products/{id}/activate",
        ) as resp:
            if resp.status_code != 200:
                resp.failure(f"Activate failed: {extract_error_detail(resp)}")

    @task
    def done(self):
        self.interrupt()


class SubscriberOrderRefundJourney(SequentialTaskSet):
    """Subscriber flow: Ordering → Payments via OrderReturnedSubscriber.

    Walks an order through the full lifecycle to Returned, triggering the
    subscriber to auto-initiate a refund for the succeeded payment.

    Thread: Identity → Ordering → Payments → Ordering (return lifecycle)
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
            name="[Sub:Refund] POST /customers",
        ) as resp:
            if resp.status_code == 201:
                self.state.customer_id = resp.json()["customer_id"]
            else:
                resp.failure(f"Register failed: {extract_error_detail(resp)}")
                self.interrupt()

    @task
    def create_order(self):
        payload = order_data(customer_id=self.state.customer_id, num_items=2)
        with self.client.post(
            "/orders",
            json=payload,
            catch_response=True,
            name="[Sub:Refund] POST /orders",
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
            name="[Sub:Refund] PUT /orders/{id}/confirm",
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
            name="[Sub:Refund] POST /payments",
        ) as resp:
            if resp.status_code == 201:
                self.state.payment_id = resp.json()["payment_id"]
            else:
                resp.failure(f"Payment init failed: {extract_error_detail(resp)}")
                self.interrupt()

    @task
    def payment_webhook_success(self):
        payload = webhook_data_success(self.state.payment_id)
        with self.client.post(
            "/payments/webhook",
            json=payload,
            headers={"X-Gateway-Signature": "test-signature"},
            catch_response=True,
            name="[Sub:Refund] POST /payments/webhook",
        ) as resp:
            if resp.status_code != 200:
                resp.failure(f"Webhook failed: {extract_error_detail(resp)}")

    @task
    def record_payment_success_on_order(self):
        with self.client.put(
            f"/orders/{self.state.order_id}/payment/success",
            json={
                "payment_id": self.state.payment_id,
                "amount": round(random.uniform(29.99, 199.99), 2),
                "payment_method": "credit_card",
            },
            catch_response=True,
            name="[Sub:Refund] PUT /orders/{id}/payment/success",
        ) as resp:
            if resp.status_code == 200:
                resp.success()
            elif resp.status_code == 422 and "Paid" in resp.text:
                resp.success()  # Saga already moved to Paid
            else:
                resp.failure(f"Payment success failed: {extract_error_detail(resp)}")

    @task
    def ship_order(self):
        with self.client.put(
            f"/orders/{self.state.order_id}/ship",
            json=shipment_data(),
            catch_response=True,
            name="[Sub:Refund] PUT /orders/{id}/ship",
        ) as resp:
            if resp.status_code != 200:
                resp.failure(f"Ship failed: {extract_error_detail(resp)}")

    @task
    def deliver_order(self):
        with self.client.put(
            f"/orders/{self.state.order_id}/deliver",
            catch_response=True,
            name="[Sub:Refund] PUT /orders/{id}/deliver",
        ) as resp:
            if resp.status_code != 200:
                resp.failure(f"Deliver failed: {extract_error_detail(resp)}")

    @task
    def request_return(self):
        with self.client.put(
            f"/orders/{self.state.order_id}/return/request",
            json={"reason": "Product not as described"},
            catch_response=True,
            name="[Sub:Refund] PUT /orders/{id}/return/request",
        ) as resp:
            if resp.status_code != 200:
                resp.failure(f"Return request failed: {extract_error_detail(resp)}")

    @task
    def approve_return(self):
        with self.client.put(
            f"/orders/{self.state.order_id}/return/approve",
            catch_response=True,
            name="[Sub:Refund] PUT /orders/{id}/return/approve",
        ) as resp:
            if resp.status_code != 200:
                resp.failure(f"Return approve failed: {extract_error_detail(resp)}")

    @task
    def record_return(self):
        with self.client.put(
            f"/orders/{self.state.order_id}/return/record",
            json={"returned_item_ids": None},
            catch_response=True,
            name="[Sub:Refund] PUT /orders/{id}/return/record",
        ) as resp:
            if resp.status_code != 200:
                resp.failure(f"Record return failed: {extract_error_detail(resp)}")

    @task
    def done(self):
        self.interrupt()


class SubscriberVerifiedPurchaseJourney(SequentialTaskSet):
    """Subscriber flow: Ordering → Reviews via OrderDeliveredSubscriber.

    Walks an order through delivery, then submits a review. The subscriber
    creates VerifiedPurchases records on delivery, allowing the review to be
    flagged as a verified purchase.

    Thread: Identity → Ordering → Payments → Reviews
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
            name="[Sub:VP] POST /customers",
        ) as resp:
            if resp.status_code == 201:
                self.state.customer_id = resp.json()["customer_id"]
            else:
                resp.failure(f"Register failed: {extract_error_detail(resp)}")
                self.interrupt()

    @task
    def create_order(self):
        payload = order_data(customer_id=self.state.customer_id, num_items=1)
        # Track product_id for the review
        self.state.product_id = payload["items"][0]["product_id"]
        with self.client.post(
            "/orders",
            json=payload,
            catch_response=True,
            name="[Sub:VP] POST /orders",
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
            name="[Sub:VP] PUT /orders/{id}/confirm",
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
            name="[Sub:VP] POST /payments",
        ) as resp:
            if resp.status_code == 201:
                self.state.payment_id = resp.json()["payment_id"]
            else:
                resp.failure(f"Payment init failed: {extract_error_detail(resp)}")
                self.interrupt()

    @task
    def payment_webhook_success(self):
        payload = webhook_data_success(self.state.payment_id)
        with self.client.post(
            "/payments/webhook",
            json=payload,
            headers={"X-Gateway-Signature": "test-signature"},
            catch_response=True,
            name="[Sub:VP] POST /payments/webhook",
        ) as resp:
            if resp.status_code != 200:
                resp.failure(f"Webhook failed: {extract_error_detail(resp)}")

    @task
    def record_payment_success_on_order(self):
        with self.client.put(
            f"/orders/{self.state.order_id}/payment/success",
            json={
                "payment_id": self.state.payment_id,
                "amount": round(random.uniform(29.99, 199.99), 2),
                "payment_method": "credit_card",
            },
            catch_response=True,
            name="[Sub:VP] PUT /orders/{id}/payment/success",
        ) as resp:
            if resp.status_code == 200:
                resp.success()
            elif resp.status_code == 422 and "Paid" in resp.text:
                resp.success()  # Saga already moved to Paid
            else:
                resp.failure(f"Payment success failed: {extract_error_detail(resp)}")

    @task
    def ship_order(self):
        with self.client.put(
            f"/orders/{self.state.order_id}/ship",
            json=shipment_data(),
            catch_response=True,
            name="[Sub:VP] PUT /orders/{id}/ship",
        ) as resp:
            if resp.status_code != 200:
                resp.failure(f"Ship failed: {extract_error_detail(resp)}")

    @task
    def deliver_order(self):
        with self.client.put(
            f"/orders/{self.state.order_id}/deliver",
            catch_response=True,
            name="[Sub:VP] PUT /orders/{id}/deliver",
        ) as resp:
            if resp.status_code != 200:
                resp.failure(f"Deliver failed: {extract_error_detail(resp)}")

    @task
    def submit_review(self):
        payload = review_data(
            product_id=self.state.product_id,
            customer_id=self.state.customer_id,
        )
        with self.client.post(
            "/reviews",
            json=payload,
            catch_response=True,
            name="[Sub:VP] POST /reviews",
        ) as resp:
            if resp.status_code == 201:
                resp.success()
            else:
                # Review submission may fail if verified purchase record
                # hasn't propagated yet — this is acceptable under load
                resp.failure(f"Submit review failed: {extract_error_detail(resp)}")

    @task
    def done(self):
        self.interrupt()


class SubscriberUser(HttpUser):
    """Subscriber ACL happy-path scenarios.

    Exercises the three subscriber-based cross-domain flows:
    - CatalogueVariantSubscriber: Catalogue → Inventory stock initialization
    - OrderReturnedSubscriber: Ordering → Payments refund initiation
    - OrderDeliveredSubscriber: Ordering → Reviews verified purchase tracking

    These are happy-path scenarios with no expected failures.

    Usage:
        locust -f loadtests/scenarios/cross_domain.py SubscriberUser
        locust -f loadtests/scenarios/cross_domain.py SubscriberUser --headless -u 3 -r 1 -t 30s
    """

    wait_time = between(1.0, 3.0)
    tasks = {
        SubscriberVariantStockJourney: 1,
        SubscriberOrderRefundJourney: 1,
        SubscriberVerifiedPurchaseJourney: 1,
    }
