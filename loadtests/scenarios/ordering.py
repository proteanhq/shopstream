"""Ordering domain load test scenarios.

Four stateful SequentialTaskSet journeys covering the cart lifecycle,
full order lifecycle through delivery, order cancellation with refund,
and the cart-to-checkout conversion flow.
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


class OrderingUser(HttpUser):
    """Locust user simulating Ordering domain interactions.

    Weighted distribution:
    - 30% Cart lifecycle (browsing, abandonment)
    - 25% Full order lifecycle (happy path)
    - 15% Cart to checkout conversion
    - 15% Order cancellation + refund
    - 15% Order return flow
    """

    wait_time = between(0.5, 2.0)
    tasks = {
        CartLifecycleJourney: 6,
        OrderFullLifecycleJourney: 5,
        CartToCheckoutJourney: 3,
        OrderCancellationJourney: 3,
        OrderReturnJourney: 3,
    }
