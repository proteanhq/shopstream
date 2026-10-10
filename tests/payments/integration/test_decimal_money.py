"""Exact money round-trips through the payments projections, Postgres and the API.

As floats, 0.1 + 0.2 is 0.30000000000000004. The projections that keep running
money totals use ``Decimal(precision=19, scale=4)``, so the same sum is exactly
0.3 in the store and ``"0.3000"`` in the API response. The Postgres-only tests
skip under ``--protean-env memory``.
"""

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from protean import current_domain
from sqlalchemy import text

from payments.api.routes import payment_router
from payments.payment.events import PaymentSucceeded, RefundCompleted
from payments.payment.initiation import InitiatePayment
from payments.payment.payment import Payment
from payments.payment.refund import ProcessRefundWebhook, RequestRefund
from payments.payment.webhook import ProcessPaymentWebhook
from payments.projections.daily_revenue import DailyRevenue, DailyRevenueProjector
from payments.projections.payment_status import PaymentStatusView

_DAY = datetime(2026, 1, 15, 12, 0, tzinfo=UTC)


def _require_postgres(projection):
    provider = current_domain.repository_for(projection)._provider
    if provider.__class__.__database__ != "postgresql":
        pytest.skip("NUMERIC columns are only observable under the Postgres env")
    return provider


def _pay_and_refund_tenths(payment_amount=10.0):
    """Pay ``payment_amount``, then complete refunds of 0.1 and 0.2."""
    return _pay_and_refund(payment_amount, (0.1, 0.2))


def _pay_and_refund(payment_amount, refunds):
    payment_id = current_domain.process(
        InitiatePayment(
            order_id="ord-decimal-001",
            customer_id="cust-decimal-001",
            amount=payment_amount,
            currency="USD",
            payment_method_type="credit_card",
            last4="4242",
            idempotency_key=f"decimal-idem-{payment_amount}",
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
    for index, amount in enumerate(refunds):
        current_domain.process(
            RequestRefund(payment_id=payment_id, amount=amount, reason="Partial"),
            asynchronous=False,
        )
        refund_id = str(current_domain.repository_for(Payment).get(payment_id).refunds[index].id)
        current_domain.process(
            ProcessRefundWebhook(
                payment_id=payment_id,
                refund_id=refund_id,
                gateway_refund_id=f"gw-decimal-{index}",
            ),
            asynchronous=False,
        )
    return payment_id


def _column_types(provider, table_name, columns):
    with provider._engine.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT column_name, data_type, numeric_precision, numeric_scale "
                "FROM information_schema.columns "
                "WHERE table_name = :table AND column_name = ANY(:columns)"
            ),
            {"table": table_name, "columns": list(columns)},
        ).all()
    return {row.column_name: (row.data_type, row.numeric_precision, row.numeric_scale) for row in rows}


@pytest.fixture()
def client():
    app = FastAPI()
    app.include_router(payment_router)
    return TestClient(app)


class TestPaymentStatusRoundTrip:
    def test_refunds_of_tenths_sum_exactly(self):
        payment_id = _pay_and_refund_tenths()

        view = current_domain.repository_for(PaymentStatusView).get(payment_id)
        assert isinstance(view.total_refunded, Decimal)
        assert view.total_refunded == Decimal("0.3")
        assert isinstance(view.amount, Decimal)
        assert view.amount == Decimal("10")
        assert view.status == "Partially_Refunded"

    def test_view_rounds_float_artifacts_in_the_payment_amount(self):
        # 0.1 + 0.2 is 0.30000000000000004 as a float.
        payment_id = _pay_and_refund(0.1 + 0.2, ())

        view = current_domain.repository_for(PaymentStatusView).get(payment_id)
        assert str(view.amount) == "0.3000"

    @pytest.mark.parametrize(
        ("payment_amount", "refunds", "status"),
        [
            (1.0, (0.3333, 0.3333, 0.3333), "Partially_Refunded"),
            (0.3, (0.1, 0.2), "Refunded"),
        ],
    )
    def test_aggregate_and_view_agree_on_the_status(self, payment_amount, refunds, status):
        payment_id = _pay_and_refund(payment_amount, refunds)

        payment = current_domain.repository_for(Payment).get(payment_id)
        view = current_domain.repository_for(PaymentStatusView).get(payment_id)
        assert payment.status == status
        assert view.status == status

    def test_api_sends_money_as_strings_with_four_places(self, client):
        payment_id = _pay_and_refund_tenths()

        resp = client.get(f"/payments/{payment_id}")

        assert resp.status_code == 200
        body = resp.json()
        assert body["total_refunded"] == "0.3000"
        assert body["amount"] == "10.0000"

    def test_api_sends_a_fresh_zero_total_with_four_places(self, client):
        payment_id = current_domain.process(
            InitiatePayment(
                order_id="ord-decimal-002",
                customer_id="cust-decimal-002",
                amount=25.5,
                currency="USD",
                payment_method_type="credit_card",
                idempotency_key="decimal-idem-fresh",
            ),
            asynchronous=False,
        )

        body = client.get(f"/payments/{payment_id}").json()

        assert body["total_refunded"] == "0.0000"
        assert body["amount"] == "25.5000"

    def test_refunds_of_tenths_fully_refund_a_payment_of_the_same_sum(self):
        payment_id = _pay_and_refund_tenths(payment_amount=0.3)

        view = current_domain.repository_for(PaymentStatusView).get(payment_id)
        assert view.total_refunded == Decimal("0.3")
        assert view.status == "Refunded"

    def test_round_trip_through_postgres_numeric_columns(self, client):
        provider = _require_postgres(PaymentStatusView)
        payment_id = _pay_and_refund_tenths()

        view = current_domain.repository_for(PaymentStatusView).get(payment_id)
        assert view.total_refunded == Decimal("0.3")
        assert client.get(f"/payments/{payment_id}").json()["total_refunded"] == "0.3000"

        table = current_domain.repository_for(PaymentStatusView)._database_model.__table__.name
        types = _column_types(provider, table, ("amount", "total_refunded"))
        assert types == {
            "amount": ("numeric", 19, 4),
            "total_refunded": ("numeric", 19, 4),
        }


class TestDailyRevenueDecimal:
    def test_projector_sums_tenths_exactly(self):
        projector = DailyRevenueProjector()
        for index, amount in enumerate((0.1, 0.2)):
            projector.on_payment_succeeded(
                PaymentSucceeded(
                    payment_id=f"pay-decimal-{index}",
                    order_id=f"ord-decimal-{index}",
                    customer_id="cust-decimal",
                    amount=amount,
                    currency="USD",
                    gateway_transaction_id=f"txn-decimal-{index}",
                    succeeded_at=_DAY,
                )
            )
        projector.on_refund_completed(
            RefundCompleted(
                payment_id="pay-decimal-0",
                refund_id="ref-decimal-0",
                order_id="ord-decimal-0",
                customer_id="cust-decimal",
                amount=0.1,
                gateway_refund_id="gw-decimal-0",
                completed_at=_DAY,
            )
        )

        record = current_domain.repository_for(DailyRevenue).get("2026-01-15")
        assert isinstance(record.total_revenue, Decimal)
        assert record.total_revenue == Decimal("0.3")
        assert record.total_refunded == Decimal("0.1")
        assert record.net_revenue == Decimal("0.2")
        assert record.transaction_count == 2
        assert record.refund_count == 1

    def test_save_and_load_on_postgres_numeric_columns(self):
        provider = _require_postgres(DailyRevenue)
        repo = current_domain.repository_for(DailyRevenue)
        repo.add(
            DailyRevenue(
                date="2026-01-15",
                total_revenue=Decimal("0.1") + Decimal("0.2"),
                total_refunded=Decimal("0.1"),
                net_revenue=Decimal("0.2"),
            )
        )

        loaded = repo.get("2026-01-15")
        assert isinstance(loaded.total_revenue, Decimal)
        assert loaded.total_revenue == Decimal("0.3")
        assert loaded.total_refunded == Decimal("0.1")
        assert loaded.net_revenue == Decimal("0.2")

        table = repo._database_model.__table__.name
        types = _column_types(provider, table, ("total_revenue", "total_refunded", "net_revenue"))
        assert len(types) == 3, f"Expected three money columns in {table}, got {types}"
        for column, column_type in types.items():
            assert column_type == ("numeric", 19, 4), column
