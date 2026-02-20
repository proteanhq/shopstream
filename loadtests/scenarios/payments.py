"""Payments domain load test scenarios.

Three stateful SequentialTaskSet journeys covering payment initiation
with webhook success, payment failure with retry, and invoice lifecycle.
"""

import uuid

from locust import HttpUser, SequentialTaskSet, between, task

from loadtests.data_generators import (
    invoice_data,
    payment_data,
    webhook_data_failure,
    webhook_data_success,
)
from loadtests.helpers.response import extract_error_detail
from loadtests.helpers.state import PaymentState


class PaymentSuccessJourney(SequentialTaskSet):
    """Initiate Payment -> Webhook Success.

    The happy path: payment is initiated and the gateway returns success.
    Generates events: PaymentInitiated, PaymentSucceeded.
    """

    def on_start(self):
        self.state = PaymentState()

    @task
    def initiate_payment(self):
        payload = payment_data()
        self.state.order_id = payload["order_id"]
        self.state.amount = payload["amount"]
        with self.client.post(
            "/payments",
            json=payload,
            catch_response=True,
            name="POST /payments",
        ) as resp:
            if resp.status_code == 201:
                self.state.payment_id = resp.json()["payment_id"]
                self.state.current_status = "pending"
            else:
                resp.failure(f"Initiate payment failed: {resp.status_code} — {extract_error_detail(resp)}")
                self.interrupt()

    @task
    def webhook_success(self):
        payload = webhook_data_success(self.state.payment_id)
        with self.client.post(
            "/payments/webhook",
            json=payload,
            catch_response=True,
            name="POST /payments/webhook (success)",
        ) as resp:
            if resp.status_code == 200:
                self.state.current_status = "succeeded"
            else:
                resp.failure(f"Webhook success failed: {resp.status_code} — {extract_error_detail(resp)}")

    @task
    def done(self):
        self.interrupt()


class PaymentFailureRetryJourney(SequentialTaskSet):
    """Initiate Payment -> Webhook Failure -> Retry -> Webhook Success.

    Models a payment that fails on first attempt, is retried, and succeeds.
    Generates events: PaymentInitiated, PaymentFailed, PaymentRetryInitiated, PaymentSucceeded.
    """

    def on_start(self):
        self.state = PaymentState()

    @task
    def initiate_payment(self):
        payload = payment_data()
        self.state.order_id = payload["order_id"]
        self.state.amount = payload["amount"]
        with self.client.post(
            "/payments",
            json=payload,
            catch_response=True,
            name="POST /payments",
        ) as resp:
            if resp.status_code == 201:
                self.state.payment_id = resp.json()["payment_id"]
            else:
                resp.failure(f"Initiate payment failed: {resp.status_code} — {extract_error_detail(resp)}")
                self.interrupt()

    @task
    def webhook_failure(self):
        payload = webhook_data_failure(self.state.payment_id)
        with self.client.post(
            "/payments/webhook",
            json=payload,
            catch_response=True,
            name="POST /payments/webhook (failure)",
        ) as resp:
            if resp.status_code == 200:
                self.state.current_status = "failed"
            else:
                resp.failure(f"Webhook failure failed: {resp.status_code} — {extract_error_detail(resp)}")

    @task
    def retry_payment(self):
        with self.client.post(
            f"/payments/{self.state.payment_id}/retry",
            catch_response=True,
            name="POST /payments/{id}/retry",
        ) as resp:
            if resp.status_code == 200:
                self.state.current_status = "retry_initiated"
            else:
                resp.failure(f"Retry failed: {resp.status_code} — {extract_error_detail(resp)}")

    @task
    def webhook_success_after_retry(self):
        payload = webhook_data_success(self.state.payment_id)
        with self.client.post(
            "/payments/webhook",
            json=payload,
            catch_response=True,
            name="POST /payments/webhook (success after retry)",
        ) as resp:
            if resp.status_code == 200:
                self.state.current_status = "succeeded"
            else:
                resp.failure(f"Webhook success after retry failed: {resp.status_code} — {extract_error_detail(resp)}")

    @task
    def done(self):
        self.interrupt()


class PaymentRefundJourney(SequentialTaskSet):
    """Initiate -> Webhook Success -> Request Refund -> Refund Webhook.

    Models a payment that succeeds and then is refunded.
    """

    def on_start(self):
        self.state = PaymentState()

    @task
    def initiate_payment(self):
        payload = payment_data()
        self.state.order_id = payload["order_id"]
        self.state.amount = payload["amount"]
        with self.client.post(
            "/payments",
            json=payload,
            catch_response=True,
            name="POST /payments",
        ) as resp:
            if resp.status_code == 201:
                self.state.payment_id = resp.json()["payment_id"]
            else:
                resp.failure(f"Initiate payment failed: {extract_error_detail(resp)}")
                self.interrupt()

    @task
    def webhook_success(self):
        payload = webhook_data_success(self.state.payment_id)
        with self.client.post(
            "/payments/webhook",
            json=payload,
            catch_response=True,
            name="POST /payments/webhook (success)",
        ) as resp:
            if resp.status_code != 200:
                resp.failure(f"Webhook failed: {extract_error_detail(resp)}")
                self.interrupt()

    @task
    def request_refund(self):
        with self.client.post(
            f"/payments/{self.state.payment_id}/refund",
            json={
                "amount": self.state.amount,
                "reason": "Customer requested cancellation",
            },
            catch_response=True,
            name="POST /payments/{id}/refund",
        ) as resp:
            if resp.status_code != 200:
                resp.failure(f"Refund request failed: {extract_error_detail(resp)}")

    @task
    def refund_webhook(self):
        refund_id = f"ref-{uuid.uuid4().hex[:8]}"
        with self.client.post(
            "/payments/refund/webhook",
            json={
                "payment_id": self.state.payment_id,
                "refund_id": refund_id,
                "gateway_refund_id": f"gref-{uuid.uuid4().hex[:12]}",
            },
            catch_response=True,
            name="POST /payments/refund/webhook",
        ) as resp:
            if resp.status_code != 200:
                resp.failure(f"Refund webhook failed: {extract_error_detail(resp)}")

    @task
    def done(self):
        self.interrupt()


class InvoiceJourney(SequentialTaskSet):
    """Generate Invoice -> Void Invoice.

    Models the invoice lifecycle: created for a paid order, then voided
    if the order is cancelled/refunded.
    """

    def on_start(self):
        self.invoice_id = None

    @task
    def generate_invoice(self):
        payload = invoice_data()
        with self.client.post(
            "/invoices",
            json=payload,
            catch_response=True,
            name="POST /invoices",
        ) as resp:
            if resp.status_code == 201:
                self.invoice_id = resp.json()["invoice_id"]
            else:
                resp.failure(f"Generate invoice failed: {resp.status_code} — {extract_error_detail(resp)}")
                self.interrupt()

    @task
    def void_invoice(self):
        with self.client.put(
            f"/invoices/{self.invoice_id}/void",
            json={"reason": "Order cancelled by customer"},
            catch_response=True,
            name="PUT /invoices/{id}/void",
        ) as resp:
            if resp.status_code != 200:
                resp.failure(f"Void invoice failed: {resp.status_code} — {extract_error_detail(resp)}")

    @task
    def done(self):
        self.interrupt()


class PaymentsUser(HttpUser):
    """Locust user simulating Payments domain interactions.

    Weighted distribution:
    - 40% Payment success (most common)
    - 20% Payment failure + retry
    - 20% Payment refund
    - 20% Invoice lifecycle
    """

    wait_time = between(0.5, 2.0)
    tasks = {
        PaymentSuccessJourney: 8,
        PaymentFailureRetryJourney: 4,
        PaymentRefundJourney: 4,
        InvoiceJourney: 4,
    }
