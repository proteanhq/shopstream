"""Integration tests for payment projections."""

from payments.payment.initiation import InitiatePayment
from payments.payment.payment import Payment
from payments.payment.refund import ProcessRefundWebhook, RequestRefund
from payments.payment.retry import RetryPayment
from payments.payment.webhook import ProcessPaymentWebhook
from payments.projections.daily_revenue import DailyRevenue
from payments.projections.failed_payments import FailedPayment
from payments.projections.payment_status import PaymentStatusView
from protean import current_domain

_idem_counter = 0


def _next_idem():
    global _idem_counter
    _idem_counter += 1
    return f"proj-idem-{_idem_counter:04d}"


def _create_and_succeed_payment(amount=75.00):
    payment_id = current_domain.process(
        InitiatePayment(
            order_id="ord-proj-001",
            customer_id="cust-proj-001",
            amount=amount,
            currency="USD",
            payment_method_type="credit_card",
            last4="4242",
            idempotency_key=_next_idem(),
        ),
        asynchronous=False,
    )
    current_domain.process(
        ProcessPaymentWebhook(
            payment_id=payment_id,
            gateway_transaction_id=f"txn-{payment_id}",
            gateway_status="succeeded",
        ),
        asynchronous=False,
    )
    return payment_id


def _create_failed_payment(amount=75.00):
    payment_id = current_domain.process(
        InitiatePayment(
            order_id="ord-proj-fail",
            customer_id="cust-proj-fail",
            amount=amount,
            currency="USD",
            payment_method_type="credit_card",
            last4="4242",
            idempotency_key=_next_idem(),
        ),
        asynchronous=False,
    )
    current_domain.process(
        ProcessPaymentWebhook(
            payment_id=payment_id,
            gateway_status="failed",
            failure_reason="Card declined",
        ),
        asynchronous=False,
    )
    return payment_id


class TestPaymentStatusProjection:
    def test_projection_created_on_initiate(self):
        payment_id = current_domain.process(
            InitiatePayment(
                order_id="ord-proj-002",
                customer_id="cust-proj-002",
                amount=50.00,
                currency="USD",
                payment_method_type="debit_card",
                idempotency_key=_next_idem(),
            ),
            asynchronous=False,
        )
        view = current_domain.repository_for(PaymentStatusView).get(payment_id)
        assert view.status == "Pending"
        assert view.amount == 50.00

    def test_projection_updated_on_success(self):
        payment_id = _create_and_succeed_payment()
        view = current_domain.repository_for(PaymentStatusView).get(payment_id)
        assert view.status == "Succeeded"
        assert view.gateway_transaction_id is not None

    def test_projection_partial_refund_status(self):
        payment_id = _create_and_succeed_payment(amount=100.00)

        # Request a partial refund
        current_domain.process(
            RequestRefund(
                payment_id=payment_id,
                amount=30.00,
                reason="Partial refund",
            ),
            asynchronous=False,
        )

        # Get refund_id and complete it
        payment = current_domain.repository_for(Payment).get(payment_id)
        refund_id = str(payment.refunds[0].id)
        current_domain.process(
            ProcessRefundWebhook(
                payment_id=payment_id,
                refund_id=refund_id,
                gateway_refund_id="gw-ref-partial-001",
            ),
            asynchronous=False,
        )

        view = current_domain.repository_for(PaymentStatusView).get(payment_id)
        assert view.status == "Partially_Refunded"
        assert view.total_refunded == 30.00


class TestFailedPaymentProjection:
    def test_failed_payment_record_created(self):
        payment_id = _create_failed_payment()
        record = current_domain.repository_for(FailedPayment).get(payment_id)
        assert record.status == "failed"
        assert record.reason == "Card declined"

    def test_failed_payment_retrying_status(self):
        payment_id = _create_failed_payment()

        # Retry the payment
        current_domain.process(
            RetryPayment(payment_id=payment_id),
            asynchronous=False,
        )

        record = current_domain.repository_for(FailedPayment).get(payment_id)
        assert record.status == "retrying"
        assert record.attempt_number == 2

    def test_failed_payment_recovered_status(self):
        payment_id = _create_failed_payment()

        # Retry
        current_domain.process(
            RetryPayment(payment_id=payment_id),
            asynchronous=False,
        )

        # Succeed on retry
        current_domain.process(
            ProcessPaymentWebhook(
                payment_id=payment_id,
                gateway_transaction_id=f"txn-recovered-{payment_id}",
                gateway_status="succeeded",
            ),
            asynchronous=False,
        )

        record = current_domain.repository_for(FailedPayment).get(payment_id)
        assert record.status == "recovered"


class TestDailyRevenueProjection:
    def test_revenue_recorded_on_success(self):
        _create_and_succeed_payment(amount=200.00)
        # DailyRevenue is keyed by date string; find the record
        repo = current_domain.repository_for(DailyRevenue)
        records = repo._dao.query.all().items
        assert len(records) > 0
        # At least one record should have revenue
        total = sum(r.total_revenue for r in records)
        assert total >= 200.00

    def test_refund_updates_daily_revenue(self):
        payment_id = _create_and_succeed_payment(amount=150.00)

        # Request and complete a refund
        current_domain.process(
            RequestRefund(
                payment_id=payment_id,
                amount=50.00,
                reason="Partial refund for revenue test",
            ),
            asynchronous=False,
        )
        payment = current_domain.repository_for(Payment).get(payment_id)
        refund_id = str(payment.refunds[0].id)
        current_domain.process(
            ProcessRefundWebhook(
                payment_id=payment_id,
                refund_id=refund_id,
                gateway_refund_id="gw-ref-rev-001",
            ),
            asynchronous=False,
        )

        # Check that refund was recorded in daily revenue
        repo = current_domain.repository_for(DailyRevenue)
        records = repo._dao.query.all().items
        total_refunded = sum(r.total_refunded for r in records)
        assert total_refunded >= 50.00
        # Net revenue should reflect the refund
        for record in records:
            if record.total_refunded and record.total_refunded > 0:
                assert record.refund_count >= 1
                assert record.net_revenue == record.total_revenue - record.total_refunded
