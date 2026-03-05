"""Ordering domain load test scenarios.

Five stateful SequentialTaskSet journeys covering the cart lifecycle,
full order lifecycle through delivery, order cancellation with refund,
the cart-to-checkout conversion flow, and the full checkout saga
(cart → checkout → confirm → pay → ship → deliver → complete).
"""

import random
import uuid

from locust import HttpUser, SequentialTaskSet, between, task

from loadtests.data_generators import (
    cart_data,
    cart_item_data,
    checkout_data,
    order_data,
    shipment_data,
    webhook_data_failure,
    webhook_data_success,
)
from loadtests.helpers.response import extract_error_detail
from loadtests.helpers.state import CartState, OrderState


class CartLifecycleJourney(SequentialTaskSet):
    """Create Cart -> Add Items -> Update Quantity -> Remove Item -> Abandon.

    Models a browsing customer who adds items, changes their mind,
    and ultimately abandons the cart.
    Generates events: CartCreated, CartItemAdded (x3), CartQuantityUpdated,
    CartItemRemoved, CartAbandoned.
    """

    def on_start(self):
        self.state = CartState()

    @task
    def create_cart(self):
        payload = cart_data()
        with self.client.post(
            "/carts",
            json=payload,
            catch_response=True,
            name="POST /carts",
        ) as resp:
            if resp.status_code == 201:
                self.state.cart_id = resp.json()["cart_id"]
            else:
                resp.failure(f"Create cart failed: {resp.status_code} — {extract_error_detail(resp)}")
                self.interrupt()

    @task
    def add_item_1(self):
        with self.client.post(
            f"/carts/{self.state.cart_id}/items",
            json=cart_item_data(),
            catch_response=True,
            name="POST /carts/{id}/items",
        ) as resp:
            if resp.status_code == 200:
                self.state.item_count += 1
            else:
                resp.failure(f"Add cart item failed: {resp.status_code} — {extract_error_detail(resp)}")

    @task
    def add_item_2(self):
        with self.client.post(
            f"/carts/{self.state.cart_id}/items",
            json=cart_item_data(),
            catch_response=True,
            name="POST /carts/{id}/items",
        ) as resp:
            if resp.status_code == 200:
                self.state.item_count += 1
            else:
                resp.failure(f"Add cart item 2 failed: {resp.status_code} — {extract_error_detail(resp)}")

    @task
    def add_item_3(self):
        with self.client.post(
            f"/carts/{self.state.cart_id}/items",
            json=cart_item_data(),
            catch_response=True,
            name="POST /carts/{id}/items",
        ) as resp:
            if resp.status_code == 200:
                self.state.item_count += 1
            else:
                resp.failure(f"Add cart item 3 failed: {resp.status_code} — {extract_error_detail(resp)}")

    @task
    def get_cart(self):
        """Verify CartView projection is populated."""
        with self.client.get(
            f"/carts/{self.state.cart_id}",
            catch_response=True,
            name="GET /carts/{id}",
        ) as resp:
            if resp.status_code in (200, 404):
                resp.success()
            else:
                resp.failure(f"Get cart failed: {resp.status_code} — {extract_error_detail(resp)}")

    @task
    def abandon_cart(self):
        with self.client.put(
            f"/carts/{self.state.cart_id}/abandon",
            catch_response=True,
            name="PUT /carts/{id}/abandon",
        ) as resp:
            if resp.status_code != 200:
                resp.failure(f"Abandon cart failed: {resp.status_code} — {extract_error_detail(resp)}")

    @task
    def done(self):
        self.interrupt()


class OrderFullLifecycleJourney(SequentialTaskSet):
    """Create Order -> Confirm -> Payment Pending -> Payment Success ->
    Processing -> Ship -> Deliver -> Complete.

    The happy path: a full order lifecycle from creation to completion.
    Generates 8 events exercising the order state machine end-to-end.
    """

    def on_start(self):
        self.state = OrderState()

    @task
    def create_order(self):
        payload = order_data()
        with self.client.post(
            "/orders",
            json=payload,
            catch_response=True,
            name="POST /orders",
        ) as resp:
            if resp.status_code == 201:
                self.state.order_id = resp.json()["order_id"]
            else:
                resp.failure(f"Create order failed: {resp.status_code} — {extract_error_detail(resp)}")
                self.interrupt()

    @task
    def confirm_order(self):
        with self.client.put(
            f"/orders/{self.state.order_id}/confirm",
            catch_response=True,
            name="PUT /orders/{id}/confirm",
        ) as resp:
            if resp.status_code == 200:
                self.state.current_status = "Confirmed"
            else:
                resp.failure(f"Confirm failed: {resp.status_code} — {extract_error_detail(resp)}")
                self.interrupt()

    @task
    def record_payment_pending(self):
        self.state.payment_id = f"pay-{uuid.uuid4().hex[:8]}"
        with self.client.put(
            f"/orders/{self.state.order_id}/payment/pending",
            json={
                "payment_id": self.state.payment_id,
                "payment_method": "credit_card",
            },
            catch_response=True,
            name="PUT /orders/{id}/payment/pending",
        ) as resp:
            if resp.status_code == 200:
                self.state.current_status = "PaymentPending"
            else:
                resp.failure(f"Payment pending failed: {resp.status_code} — {extract_error_detail(resp)}")
                self.interrupt()

    @task
    def record_payment_success(self):
        with self.client.put(
            f"/orders/{self.state.order_id}/payment/success",
            json={
                "payment_id": self.state.payment_id,
                "amount": round(random.uniform(29.99, 299.99), 2),
                "payment_method": "credit_card",
            },
            catch_response=True,
            name="PUT /orders/{id}/payment/success",
        ) as resp:
            if resp.status_code == 200:
                self.state.current_status = "Paid"
            else:
                resp.failure(f"Payment success failed: {resp.status_code} — {extract_error_detail(resp)}")
                self.interrupt()

    @task
    def mark_processing(self):
        with self.client.put(
            f"/orders/{self.state.order_id}/processing",
            catch_response=True,
            name="PUT /orders/{id}/processing",
        ) as resp:
            if resp.status_code == 200:
                self.state.current_status = "Processing"
            else:
                resp.failure(f"Mark processing failed: {resp.status_code} — {extract_error_detail(resp)}")

    @task
    def record_shipment(self):
        with self.client.put(
            f"/orders/{self.state.order_id}/ship",
            json=shipment_data(),
            catch_response=True,
            name="PUT /orders/{id}/ship",
        ) as resp:
            if resp.status_code == 200:
                self.state.current_status = "Shipped"
            else:
                resp.failure(f"Ship failed: {resp.status_code} — {extract_error_detail(resp)}")

    @task
    def record_delivery(self):
        with self.client.put(
            f"/orders/{self.state.order_id}/deliver",
            catch_response=True,
            name="PUT /orders/{id}/deliver",
        ) as resp:
            if resp.status_code == 200:
                self.state.current_status = "Delivered"
            else:
                resp.failure(f"Deliver failed: {resp.status_code} — {extract_error_detail(resp)}")

    @task
    def complete_order(self):
        with self.client.put(
            f"/orders/{self.state.order_id}/complete",
            catch_response=True,
            name="PUT /orders/{id}/complete",
        ) as resp:
            if resp.status_code == 200:
                self.state.current_status = "Completed"
            else:
                resp.failure(f"Complete failed: {resp.status_code} — {extract_error_detail(resp)}")

    @task
    def get_order_detail(self):
        """Verify OrderDetail projection is populated."""
        with self.client.get(
            f"/orders/{self.state.order_id}",
            catch_response=True,
            name="GET /orders/{id}",
        ) as resp:
            if resp.status_code in (200, 404):
                resp.success()
            else:
                resp.failure(f"Get order detail failed: {resp.status_code} — {extract_error_detail(resp)}")

    @task
    def get_order_timeline(self):
        """Verify OrderTimeline projection is populated."""
        with self.client.get(
            f"/orders/{self.state.order_id}/timeline",
            catch_response=True,
            name="GET /orders/{id}/timeline",
        ) as resp:
            if resp.status_code in (200, 404):
                resp.success()
            else:
                resp.failure(f"Get order timeline failed: {resp.status_code} — {extract_error_detail(resp)}")

    @task
    def done(self):
        self.interrupt()


class OrderCancellationJourney(SequentialTaskSet):
    """Create Order -> Confirm -> Payment Pending -> Cancel -> Refund.

    Models a customer who cancels during payment processing.
    Tests the cancellation + refund path of the order state machine.
    """

    def on_start(self):
        self.state = OrderState()

    @task
    def create_order(self):
        payload = order_data()
        with self.client.post(
            "/orders",
            json=payload,
            catch_response=True,
            name="POST /orders",
        ) as resp:
            if resp.status_code == 201:
                self.state.order_id = resp.json()["order_id"]
            else:
                resp.failure(f"Create order failed: {resp.status_code} — {extract_error_detail(resp)}")
                self.interrupt()

    @task
    def confirm_order(self):
        with self.client.put(
            f"/orders/{self.state.order_id}/confirm",
            catch_response=True,
            name="PUT /orders/{id}/confirm",
        ) as resp:
            if resp.status_code == 200:
                self.state.current_status = "Confirmed"
            else:
                resp.failure(f"Confirm failed: {resp.status_code} — {extract_error_detail(resp)}")
                self.interrupt()

    @task
    def record_payment_pending(self):
        self.state.payment_id = f"pay-{uuid.uuid4().hex[:8]}"
        with self.client.put(
            f"/orders/{self.state.order_id}/payment/pending",
            json={
                "payment_id": self.state.payment_id,
                "payment_method": "credit_card",
            },
            catch_response=True,
            name="PUT /orders/{id}/payment/pending",
        ) as resp:
            if resp.status_code == 200:
                self.state.current_status = "PaymentPending"
            else:
                resp.failure(f"Payment pending failed: {resp.status_code} — {extract_error_detail(resp)}")
                self.interrupt()

    @task
    def cancel_order(self):
        with self.client.put(
            f"/orders/{self.state.order_id}/cancel",
            json={
                "reason": "Changed my mind",
                "cancelled_by": "customer",
            },
            catch_response=True,
            name="PUT /orders/{id}/cancel",
        ) as resp:
            if resp.status_code == 200:
                self.state.current_status = "Cancelled"
            else:
                resp.failure(f"Cancel failed: {resp.status_code} — {extract_error_detail(resp)}")

    @task
    def refund_order(self):
        with self.client.put(
            f"/orders/{self.state.order_id}/refund",
            json={"refund_amount": None},
            catch_response=True,
            name="PUT /orders/{id}/refund",
        ) as resp:
            if resp.status_code == 200:
                self.state.current_status = "Refunded"
            else:
                # Refund may fail if payment wasn't captured — that's expected
                pass

    @task
    def done(self):
        self.interrupt()


class CartToCheckoutJourney(SequentialTaskSet):
    """Create Cart -> Add Items -> Checkout -> order created.

    Models the cart-to-order conversion flow — the most common
    e-commerce purchase path.
    """

    def on_start(self):
        self.state = CartState()

    @task
    def create_cart(self):
        payload = cart_data()
        with self.client.post(
            "/carts",
            json=payload,
            catch_response=True,
            name="POST /carts",
        ) as resp:
            if resp.status_code == 201:
                self.state.cart_id = resp.json()["cart_id"]
            else:
                resp.failure(f"Create cart failed: {resp.status_code} — {extract_error_detail(resp)}")
                self.interrupt()

    @task
    def add_items(self):
        for _ in range(random.randint(1, 3)):
            with self.client.post(
                f"/carts/{self.state.cart_id}/items",
                json=cart_item_data(),
                catch_response=True,
                name="POST /carts/{id}/items",
            ) as resp:
                if resp.status_code == 200:
                    self.state.item_count += 1
                else:
                    resp.failure(f"Add item failed: {resp.status_code} — {extract_error_detail(resp)}")
                    return

    @task
    def checkout(self):
        with self.client.post(
            f"/carts/{self.state.cart_id}/checkout",
            json=checkout_data(),
            catch_response=True,
            name="POST /carts/{id}/checkout",
        ) as resp:
            if resp.status_code == 201:
                pass  # Order created
            else:
                resp.failure(f"Checkout failed: {resp.status_code} — {extract_error_detail(resp)}")

    @task
    def done(self):
        self.interrupt()


class OrderReturnJourney(SequentialTaskSet):
    """Create -> Confirm -> Pay -> Ship -> Deliver -> Request Return -> Approve -> Record Return.

    Models the full return path after delivery.
    """

    def on_start(self):
        self.state = OrderState()

    @task
    def create_order(self):
        payload = order_data()
        with self.client.post(
            "/orders",
            json=payload,
            catch_response=True,
            name="POST /orders",
        ) as resp:
            if resp.status_code == 201:
                self.state.order_id = resp.json()["order_id"]
            else:
                resp.failure(f"Create order failed: {resp.status_code} — {extract_error_detail(resp)}")
                self.interrupt()

    @task
    def confirm(self):
        with self.client.put(
            f"/orders/{self.state.order_id}/confirm",
            catch_response=True,
            name="PUT /orders/{id}/confirm",
        ) as resp:
            if resp.status_code != 200:
                resp.failure(f"Confirm failed: {extract_error_detail(resp)}")
                self.interrupt()

    @task
    def payment_pending(self):
        self.state.payment_id = f"pay-{uuid.uuid4().hex[:8]}"
        with self.client.put(
            f"/orders/{self.state.order_id}/payment/pending",
            json={"payment_id": self.state.payment_id, "payment_method": "credit_card"},
            catch_response=True,
            name="PUT /orders/{id}/payment/pending",
        ) as resp:
            if resp.status_code != 200:
                resp.failure(f"Payment pending failed: {extract_error_detail(resp)}")
                self.interrupt()

    @task
    def payment_success(self):
        with self.client.put(
            f"/orders/{self.state.order_id}/payment/success",
            json={
                "payment_id": self.state.payment_id,
                "amount": round(random.uniform(29.99, 199.99), 2),
                "payment_method": "credit_card",
            },
            catch_response=True,
            name="PUT /orders/{id}/payment/success",
        ) as resp:
            if resp.status_code != 200:
                resp.failure(f"Payment success failed: {extract_error_detail(resp)}")
                self.interrupt()

    @task
    def ship(self):
        with self.client.put(
            f"/orders/{self.state.order_id}/ship",
            json=shipment_data(),
            catch_response=True,
            name="PUT /orders/{id}/ship",
        ) as resp:
            if resp.status_code != 200:
                resp.failure(f"Ship failed: {extract_error_detail(resp)}")

    @task
    def deliver(self):
        with self.client.put(
            f"/orders/{self.state.order_id}/deliver",
            catch_response=True,
            name="PUT /orders/{id}/deliver",
        ) as resp:
            if resp.status_code != 200:
                resp.failure(f"Deliver failed: {extract_error_detail(resp)}")

    @task
    def request_return(self):
        with self.client.put(
            f"/orders/{self.state.order_id}/return/request",
            json={"reason": "Item damaged in transit"},
            catch_response=True,
            name="PUT /orders/{id}/return/request",
        ) as resp:
            if resp.status_code != 200:
                resp.failure(f"Return request failed: {extract_error_detail(resp)}")

    @task
    def approve_return(self):
        with self.client.put(
            f"/orders/{self.state.order_id}/return/approve",
            catch_response=True,
            name="PUT /orders/{id}/return/approve",
        ) as resp:
            if resp.status_code != 200:
                resp.failure(f"Return approve failed: {extract_error_detail(resp)}")

    @task
    def record_return(self):
        with self.client.put(
            f"/orders/{self.state.order_id}/return/record",
            json={"returned_item_ids": None},
            catch_response=True,
            name="PUT /orders/{id}/return/record",
        ) as resp:
            if resp.status_code != 200:
                resp.failure(f"Record return failed: {extract_error_detail(resp)}")

    @task
    def done(self):
        self.interrupt()


class OrderCheckoutSagaJourney(SequentialTaskSet):
    """Cart -> Checkout -> Confirm -> Pay -> Ship -> Deliver -> Complete.

    The most realistic e-commerce flow: a customer builds a cart, checks out
    (which creates an order via cart conversion), then the order flows through
    the OrderCheckoutSaga — confirm, payment, fulfillment, delivery, completion.

    70% of journeys complete the happy path (payment succeeds).
    30% simulate payment failure with compensation (cancel order).

    Exercises: Ordering (cart + order), Payments (webhook), and the
    OrderCheckoutSaga process manager coordination.
    """

    def on_start(self):
        self.state = OrderState()
        self.cart_id = None
        self.payment_succeeds = random.random() < 0.7

    @task
    def create_cart(self):
        payload = cart_data()
        self.state.customer_id = payload["customer_id"]
        with self.client.post(
            "/carts",
            json=payload,
            catch_response=True,
            name="[SAGA] POST /carts",
        ) as resp:
            if resp.status_code == 201:
                self.cart_id = resp.json()["cart_id"]
            else:
                resp.failure(f"Create cart failed: {resp.status_code} — {extract_error_detail(resp)}")
                self.interrupt()

    @task
    def add_items(self):
        for _ in range(random.randint(1, 3)):
            with self.client.post(
                f"/carts/{self.cart_id}/items",
                json=cart_item_data(),
                catch_response=True,
                name="[SAGA] POST /carts/{id}/items",
            ) as resp:
                if resp.status_code != 200:
                    resp.failure(f"Add item failed: {resp.status_code} — {extract_error_detail(resp)}")
                    return

    @task
    def checkout(self):
        with self.client.post(
            f"/carts/{self.cart_id}/checkout",
            json=checkout_data(),
            catch_response=True,
            name="[SAGA] POST /carts/{id}/checkout",
        ) as resp:
            if resp.status_code == 201:
                self.state.order_id = resp.json()["order_id"]
            else:
                resp.failure(f"Checkout failed: {resp.status_code} — {extract_error_detail(resp)}")
                self.interrupt()

    @task
    def confirm_order(self):
        with self.client.put(
            f"/orders/{self.state.order_id}/confirm",
            catch_response=True,
            name="[SAGA] PUT /orders/{id}/confirm",
        ) as resp:
            if resp.status_code != 200:
                resp.failure(f"Confirm failed: {resp.status_code} — {extract_error_detail(resp)}")
                self.interrupt()

    @task
    def record_payment_pending(self):
        self.state.payment_id = f"pay-{uuid.uuid4().hex[:8]}"
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
                resp.failure(f"Payment pending failed: {resp.status_code} — {extract_error_detail(resp)}")
                self.interrupt()

    @task
    def payment_result(self):
        """Payment gateway webhook — 70% success, 30% failure."""
        if self.payment_succeeds:
            payload = webhook_data_success(self.state.payment_id)
            with self.client.post(
                "/payments/webhook",
                json=payload,
                headers={"X-Gateway-Signature": "test-signature"},
                catch_response=True,
                name="[SAGA] POST /payments/webhook (success)",
            ) as resp:
                if resp.status_code not in (200, 404):
                    resp.failure(f"Webhook failed: {resp.status_code} — {extract_error_detail(resp)}")
                elif resp.status_code == 404:
                    # Payment wasn't created via Payments domain — expected in ordering-only test
                    resp.success()

            with self.client.put(
                f"/orders/{self.state.order_id}/payment/success",
                json={
                    "payment_id": self.state.payment_id,
                    "amount": round(random.uniform(29.99, 299.99), 2),
                    "payment_method": "credit_card",
                },
                catch_response=True,
                name="[SAGA] PUT /orders/{id}/payment/success",
            ) as resp:
                if resp.status_code != 200:
                    resp.failure(f"Payment success failed: {resp.status_code} — {extract_error_detail(resp)}")
                    self.interrupt()
        else:
            # Failure path: payment fails → cancel order (compensation)
            payload = webhook_data_failure(self.state.payment_id)
            with self.client.post(
                "/payments/webhook",
                json=payload,
                headers={"X-Gateway-Signature": "test-signature"},
                catch_response=True,
                name="[SAGA] POST /payments/webhook (failure)",
            ) as resp:
                if resp.status_code not in (200, 404):
                    resp.failure(f"Webhook failed: {resp.status_code} — {extract_error_detail(resp)}")
                elif resp.status_code == 404:
                    resp.success()

            with self.client.put(
                f"/orders/{self.state.order_id}/cancel",
                json={"reason": "Payment failed", "cancelled_by": "system"},
                catch_response=True,
                name="[SAGA] PUT /orders/{id}/cancel (compensation)",
            ) as resp:
                if resp.status_code != 200:
                    resp.failure(f"Cancel failed: {resp.status_code} — {extract_error_detail(resp)}")
            self.interrupt()  # End journey on failure path

    @task
    def mark_processing(self):
        with self.client.put(
            f"/orders/{self.state.order_id}/processing",
            catch_response=True,
            name="[SAGA] PUT /orders/{id}/processing",
        ) as resp:
            if resp.status_code != 200:
                resp.failure(f"Processing failed: {resp.status_code} — {extract_error_detail(resp)}")

    @task
    def ship_order(self):
        with self.client.put(
            f"/orders/{self.state.order_id}/ship",
            json=shipment_data(),
            catch_response=True,
            name="[SAGA] PUT /orders/{id}/ship",
        ) as resp:
            if resp.status_code != 200:
                resp.failure(f"Ship failed: {resp.status_code} — {extract_error_detail(resp)}")

    @task
    def deliver_order(self):
        with self.client.put(
            f"/orders/{self.state.order_id}/deliver",
            catch_response=True,
            name="[SAGA] PUT /orders/{id}/deliver",
        ) as resp:
            if resp.status_code != 200:
                resp.failure(f"Deliver failed: {resp.status_code} — {extract_error_detail(resp)}")

    @task
    def complete_order(self):
        with self.client.put(
            f"/orders/{self.state.order_id}/complete",
            catch_response=True,
            name="[SAGA] PUT /orders/{id}/complete",
        ) as resp:
            if resp.status_code != 200:
                resp.failure(f"Complete failed: {resp.status_code} — {extract_error_detail(resp)}")

    @task
    def done(self):
        self.interrupt()


class OrderingUser(HttpUser):
    """Locust user simulating Ordering domain interactions.

    Weighted distribution:
    - 25% Cart lifecycle (browsing, abandonment)
    - 20% Full order lifecycle (happy path)
    - 20% Checkout saga (cart → checkout → pay → ship → deliver)
    - 15% Cart to checkout conversion
    - 10% Order cancellation + refund
    - 10% Order return flow
    """

    wait_time = between(0.5, 2.0)
    tasks = {
        CartLifecycleJourney: 5,
        OrderFullLifecycleJourney: 4,
        OrderCheckoutSagaJourney: 4,
        CartToCheckoutJourney: 3,
        OrderCancellationJourney: 2,
        OrderReturnJourney: 2,
    }
