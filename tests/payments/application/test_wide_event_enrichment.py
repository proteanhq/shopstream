"""Wide-event enrichment test (Protean 0.16 observability).

`InitiatePaymentHandler` calls `bind_event_context(...)` to add business
dimensions (order_id, amount, currency, payment_method) to the per-message
`protean.access` wide event. This asserts those fields land on the emitted
log record during synchronous command processing.
"""

import logging

from protean import current_domain

from payments.payment.initiation import InitiatePayment


def _initiate(**overrides):
    defaults = {
        "order_id": "ord-wide-001",
        "customer_id": "cust-001",
        "amount": 123.45,
        "currency": "USD",
        "payment_method_type": "credit_card",
        "last4": "4242",
        "idempotency_key": "idem-wide-001",
    }
    defaults.update(overrides)
    return current_domain.process(InitiatePayment(**defaults), asynchronous=False)


def _access_records(caplog):
    return [
        r
        for r in caplog.records
        if r.name == "protean.access" and getattr(r, "handler", "").startswith("InitiatePaymentHandler")
    ]


class TestPaymentWideEventEnrichment:
    def test_business_dimensions_on_wide_event(self, caplog):
        with caplog.at_level(logging.INFO, logger="protean.access"):
            _initiate(order_id="ord-xyz", amount=99.5)

        records = _access_records(caplog)
        assert records, "no protean.access wide event emitted for InitiatePaymentHandler"
        rec = records[-1]
        assert getattr(rec, "order_id", None) == "ord-xyz"
        assert getattr(rec, "amount", None) == 99.5
        assert getattr(rec, "currency", None) == "USD"
        assert getattr(rec, "payment_method", None) == "credit_card"

    def test_wide_event_carries_framework_fields(self, caplog):
        """The enrichment coexists with the framework-populated fields."""
        with caplog.at_level(logging.INFO, logger="protean.access"):
            _initiate(idempotency_key="idem-wide-fw")

        rec = _access_records(caplog)[-1]
        assert getattr(rec, "status", None) == "ok"
        assert getattr(rec, "aggregate", None) == "Payment"
