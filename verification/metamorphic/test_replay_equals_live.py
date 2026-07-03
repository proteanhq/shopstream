"""P10 - rebuilding an aggregate from its events equals its live state.

WHAT THIS CHECKS
    Every event-sourced aggregate in ShopStream keeps state in two places that
    must never disagree:

      * LIVE     - the in-memory instance a business method just mutated. Each
                   `self.raise_(Event)` applies the event inline (via the
                   aggregate's @apply handler) to advance state, then queues it.
      * REPLAYED - the instance `repository.get(id)` reconstructs by reading the
                   persisted event stream back out of the event store and folding
                   it through the SAME @apply handlers (`from_events`).

    Property P10: after persisting, `repository.get(id)` must equal the live
    instance field-for-field (including version, value objects and child
    entities).

WHAT IT CAN AND CANNOT CATCH
    This is a metamorphic ("two paths must agree") check, source B - weaker than
    the hand-computed oracles. It only catches bugs where the two paths DIVERGE:

      * an @apply handler whose result depends on transient in-memory state that
        is not carried on the event (so replay reconstructs something different);
      * a value object / entity that does not round-trip through
        serialize -> event store -> deserialize (this is exactly the shape of
        proteanhq/protean#1078, an all-default StockLevels VO decoding to None);
      * a field the factory sets directly instead of through an event, so it is
        absent on replay.

    It CANNOT catch a bug both paths share (e.g. an @apply handler that computes
    the wrong value the same way live and on replay) - that is what the type-A
    model oracle (verification/model/) is for.

COVERAGE
    Parameterized over EVERY event-sourced aggregate (see ES_CASES). Adding a new
    event-sourced aggregate is a one-row change here plus its `*_bed` fixture in
    verification/conftest.py - so new domains are covered by construction.

RUN (no Docker):
    .venv/bin/python -m pytest \
        verification/metamorphic/test_replay_equals_live.py --protean-env memory -q
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import pytest
from protean import current_domain


@dataclass(frozen=True)
class ESCase:
    """One event-sourced aggregate to exercise.

    `bed_fixture` names the session-scoped DomainFixture in conftest.py; the
    `es_ctx` fixture activates its domain context before `build` runs. `build`
    returns a live aggregate assembled through its factory + business methods
    (so several events are raised) - it must run with the domain context active.
    The aggregate class is taken from the built instance, so no case needs to
    name it separately.
    """

    id: str
    bed_fixture: str
    build: Callable[[], Any]


# --- builders: drive each aggregate through a few real transitions ----------
# Each raises multiple events and touches its value objects / child entities,
# so the round-trip actually exercises serialization, not just scalar fields.


def _build_inventory_item():
    from inventory.stock.stock import InventoryItem

    item = InventoryItem.create(
        product_id="prod-m10",
        variant_id="var-m10",
        warehouse_id="wh-m10",
        sku="SKU-M10",
        initial_quantity=20,
    )
    item.receive_stock(quantity=5)  # StockLevels VO mutates
    item.reserve(order_id="order-m10", quantity=3)  # Reservation entity (HasMany)
    return item


def _build_order():
    from ordering.order.order import Order

    order = Order.create(
        customer_id="cust-m10",
        items_data=[
            {
                "product_id": "prod-m10",
                "variant_id": "var-m10",
                "sku": "SKU-M10",
                "title": "Metamorphic Widget",
                "quantity": 2,
                "unit_price": 29.99,
            }
        ],
        shipping_address={
            "street": "1 Replay Way",
            "city": "Springfield",
            "state": "IL",
            "postal_code": "62701",
            "country": "US",
        },
        billing_address={
            "street": "1 Replay Way",
            "city": "Springfield",
            "state": "IL",
            "postal_code": "62701",
            "country": "US",
        },
        pricing={
            "subtotal": 59.98,
            "shipping_cost": 5.99,
            "tax_total": 4.80,
            "discount_total": 0.0,
            "grand_total": 70.77,
            "currency": "USD",
        },
    )
    order.add_item(  # ItemAdded: OrderItem entity + recomputed OrderPricing VO
        product_id="prod-m10b",
        variant_id="var-m10b",
        sku="SKU-M10B",
        title="Second Widget",
        quantity=1,
        unit_price=10.00,
    )
    order.confirm()  # a plain state transition
    return order


def _build_payment():
    from payments.payment.payment import Payment

    payment = Payment.create(
        order_id="order-m10",
        customer_id="cust-m10",
        amount=70.77,
        currency="USD",
        payment_method_type="credit_card",
        last4="4242",
        gateway_name="fake",
        idempotency_key="idem-m10",
    )
    payment.record_processing()  # PaymentAttempt entity (HasMany)
    payment.record_success(gateway_transaction_id="txn-m10")
    return payment


def _build_campaign():
    from loyalty.campaign.campaign import PromoCampaign

    campaign = PromoCampaign.launch(
        campaign_code="M10",
        name="Metamorphic Days",
        discount_type="points_multiplier",
        discount_value=2,
    )
    campaign.activate()
    campaign.pause(reason="scheduled break")
    return campaign


ES_CASES = [
    ESCase("inventory_item", "inventory_bed", _build_inventory_item),
    ESCase("order", "ordering_bed", _build_order),
    ESCase("payment", "payments_bed", _build_payment),
    ESCase("promo_campaign", "loyalty_bed", _build_campaign),
]

# --- regression guards -------------------------------------------------------
# This check FOUND (and now guards against the return of) a Payment replay bug:
# PaymentAttempt carried no identity on its events (PaymentInitiated /
# PaymentRetryInitiated), so `_on_payment_initiated` did add_attempts(Payment
# Attempt(...)) with no id and Protean minted a FRESH uuid4 on every replay - the
# child entity's identity was non-deterministic across reconstruction, violating
# event-sourcing replay determinism and the aggregate's "complete audit trail of
# every charge" promise. Fixed by pre-generating attempt_id and carrying it on the
# events (mirroring how Order carries OrderItem ids on OrderCreated, and how
# Payment already carries refund_id on RefundRequested). The `payment` case below
# is now a passing guard; if the id is ever dropped from the events again it fails.
_XFAIL: dict = {}


@pytest.fixture()
def es_ctx(request):
    """Activate the domain context for the parameterized case, then yield it."""
    case: ESCase = request.param
    bed = request.getfixturevalue(case.bed_fixture)
    with bed.domain_context():
        yield case


_PARAMS = [pytest.param(c, id=c.id, marks=_XFAIL.get(c.id, ())) for c in ES_CASES]


@pytest.mark.parametrize("es_ctx", _PARAMS, indirect=True)
def test_replay_equals_live(es_ctx):
    case = es_ctx

    live = case.build()
    repo = current_domain.repository_for(type(live))
    repo.add(live)

    replayed = repo.get(live.id)

    # Full-state comparison: to_dict() includes _version, value objects and
    # child-entity lists, so a round-trip that drops or mangles any of them
    # shows up here. Any divergence is a real P10 violation.
    assert replayed.to_dict() == live.to_dict()
