"""Application tests for the InitiatePayment command deadline and the
domain-wide transient-retry adoption (Protean 0.16 features).

Deadlines are enforced on the synchronous ``domain.process`` path, so they are
directly testable here. Transient-retry engages on the asynchronous Engine path
(projectors / cross-domain subscribers in production), so it is asserted at the
configuration level — its behavior is exercised by the load-test stack.
"""

from datetime import UTC, datetime, timedelta

import pytest
from protean import current_domain
from protean.exceptions import CommandExpiredError

from payments.payment.initiation import InitiatePayment
from payments.payment.payment import Payment, PaymentStatus


def _command(**overrides):
    defaults = {
        "order_id": "ord-001",
        "customer_id": "cust-001",
        "amount": 59.99,
        "currency": "USD",
        "payment_method_type": "credit_card",
        "last4": "4242",
        "idempotency_key": "idem-deadline-001",
    }
    defaults.update(overrides)
    return InitiatePayment(**defaults)


class TestPaymentCommandDeadline:
    def test_expired_deadline_rejects_with_command_expired(self):
        """A command past its deadline must not charge the customer."""
        past = datetime.now(UTC) - timedelta(seconds=1)
        with pytest.raises(CommandExpiredError):
            current_domain.process(_command(), asynchronous=False, deadline=past)

    def test_expired_deadline_does_not_persist_a_payment(self):
        past = datetime.now(UTC) - timedelta(seconds=1)
        with pytest.raises(CommandExpiredError):
            current_domain.process(
                _command(idempotency_key="idem-expired-nopersist"),
                asynchronous=False,
                deadline=past,
            )
        # The handler never ran, so no Payment event was written for this order.
        messages = current_domain.event_store.store.read("payments::payment")
        assert messages == []

    def test_future_deadline_processes_normally(self):
        future = datetime.now(UTC) + timedelta(minutes=5)
        payment_id = current_domain.process(
            _command(idempotency_key="idem-future"),
            asynchronous=False,
            deadline=future,
        )
        assert payment_id is not None

    def test_default_window_does_not_block_synchronous_flow(self):
        """The handler's 15-minute default timeout must not reject a freshly
        created command processed synchronously (no explicit deadline)."""
        payment_id = current_domain.process(_command(idempotency_key="idem-default-window"), asynchronous=False)
        payment = current_domain.repository_for(Payment).get(payment_id)
        assert payment.status == PaymentStatus.PENDING.value


FROZEN_NOW = datetime(2030, 6, 1, 12, 0, tzinfo=UTC)


class TestPaymentCommandDeadlineWithDomainClock:
    """The deadline check compares against the payments domain clock, not the wall clock."""

    def test_deadline_passed_by_the_clock_rejects_the_command(self, frozen_clock):
        from payments.domain import payments

        clock = frozen_clock(payments, FROZEN_NOW)
        clock.advance(timedelta(minutes=2))

        # The deadline is years ahead of the wall clock but behind the frozen clock.
        with pytest.raises(CommandExpiredError):
            current_domain.process(
                _command(idempotency_key="idem-clock-expired"),
                asynchronous=False,
                deadline=FROZEN_NOW + timedelta(minutes=1),
            )
        assert current_domain.event_store.store.read("payments::payment") == []

    def test_deadline_ahead_of_the_clock_processes_normally(self, frozen_clock):
        from payments.domain import payments

        frozen_clock(payments, FROZEN_NOW)

        payment_id = current_domain.process(
            _command(idempotency_key="idem-clock-ok"),
            asynchronous=False,
            deadline=FROZEN_NOW + timedelta(minutes=1),
        )
        assert current_domain.repository_for(Payment).get(payment_id).status == PaymentStatus.PENDING.value


class TestPaymentTransientRetryConfig:
    def test_transient_retry_enabled_for_payments(self):
        cfg = current_domain.config.get("server", {}).get("transient_retry", {})
        assert cfg.get("enabled") is True
        assert cfg.get("backoff") == "exponential"
