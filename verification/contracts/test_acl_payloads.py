"""P15 - cross-domain event payload contracts (producer <-> ACL subscriber).

WHAT THIS CHECKS
    ShopStream domains talk to each other over a shared external bus. A producing
    domain marks an event `published=True`; the outbox serializes it to an
    external envelope and publishes it on a stream (e.g. `ordering::order`). A
    consuming domain's `@domain.subscriber(broker="global", stream=...)` receives
    that raw dict and translates it into a domain-local action (the ACL boundary).

    The contract: every subscriber on a stream must survive EVERY `published=True`
    event on that stream. If a producer drops or renames a field that a subscriber
    reads out of `payload["data"]`, the subscriber raises KeyError at runtime -
    silent in tests until it happens in production.

    Property P15: for every (published event, subscriber-on-its-stream) pair,
    feeding the producer's real external payload through the subscriber's
    `__call__` must not raise KeyError.

WHY THIS IS TYPE-A (the answer is independent of the consumer)
    The payload is built from the PRODUCER: a real event instance is constructed
    from its own declared fields and serialized exactly as the outbox does
    (`event.to_dict()` minus `_metadata` -> the `data` block). The subscriber then
    reads whatever keys it wants out of that. Neither side is told what the other
    expects; a rename on either side makes a key a subscriber hard-reads vanish
    from the producer payload, and the check fails. The expected answer (payload
    shape) comes from the producer, not from the system-under-test agreeing with
    itself.

SCOPE / HONEST LIMITATION
    We assert specifically on KeyError, per the property. Subscribers in
    ShopStream are written defensively - most reads are `data.get(key)`, which
    returns None instead of raising when a field is absent. This check CANNOT see
    a field a subscriber reads via `.get()` and silently degrades on (e.g.
    `OrderDelivered` carries no `items`, so reviews' VerifiedPurchases is never
    populated from the real event - see TICKETS T2.2). It catches the hard
    `data[key]` reads, which are the ones that actually crash a consumer. Downstream
    business failures (a dispatched command hitting a missing aggregate) are NOT
    contract violations and are tolerated - only the payload translation is under
    test.

COVERAGE
    Full cross-product per stream: every published event on a stream is fed to
    every subscriber on that stream (a subscriber must cleanly IGNORE the event
    types it does not handle, too). Adding a published event or a subscriber is a
    one-line change in STREAMS below.

RUN (no Docker):
    .venv/bin/python -m pytest \
        verification/contracts/test_acl_payloads.py --protean-env memory -q
"""

from __future__ import annotations

import itertools
import types
import typing
from dataclasses import dataclass
from datetime import UTC, date, datetime

import pytest
from protean.utils.reflection import declared_fields

# --- building a faithful external payload from a typed event -----------------

_token = itertools.count(1)


def _dummy(field):
    """A schema-valid value for a field, inferred from its resolved python type.

    Values are placeholders - the contract check cares about which KEYS end up in
    the payload, not their contents. String/Identifier values are unique so that
    a subscriber that dispatches a command does not collide across cases.
    """
    pt = field._python_type
    # Optional[T] / T | None -> unwrap to the first real type.
    if isinstance(pt, types.UnionType) or typing.get_origin(pt) is typing.Union:
        args = [a for a in typing.get_args(pt) if a is not type(None)]
        pt = args[0] if args else str
    origin = typing.get_origin(pt)  # list[str] -> list, dict[..] -> dict
    if origin is list:
        return []
    if origin is dict:
        return {}
    if pt is bool:
        return True
    if pt is int:
        return 1
    if pt is float:
        return 1.0
    if pt is datetime:
        return datetime.now(UTC)
    if pt is date:
        return date(2026, 1, 1)
    if pt is list:
        return []
    if pt is dict:
        return {}
    return f"acl-{next(_token)}"  # String / Identifier / Text


def _event_type(producer: str, event_cls) -> str:
    """The `metadata.headers.type` string the real outbox stamps on the event.

    Format is `<CamelDomain>.<EventClass>.v<version>` (protean type_manager);
    subscribers filter by substring on the class name.
    """
    version = getattr(event_cls.meta_, "version", None) or 1
    return f"{producer.capitalize()}.{event_cls.__name__}.v{version}"


def build_payload(producer: str, event_cls, *, drop: str | None = None) -> dict:
    """Construct a real event and wrap it in the external-bus envelope.

    Must run with the producer domain's context active. `drop` removes one data
    key (used by the falsification test to simulate a producer dropping a field).
    """
    event = event_cls(**{name: _dummy(f) for name, f in declared_fields(event_cls).items()})
    data = {k: v for k, v in event.to_dict().items() if k != "_metadata"}
    if drop is not None:
        data.pop(drop, None)
    return {"metadata": {"headers": {"type": _event_type(producer, event_cls)}}, "data": data}


# --- the producer -> stream -> consumer map (mirrors the ACL wiring) ---------


@dataclass(frozen=True)
class Event:
    module: str
    cls: str


@dataclass(frozen=True)
class Consumer:
    domain: str
    module: str
    cls: str


@dataclass(frozen=True)
class Stream:
    name: str
    producer: str  # domain that owns the stream
    events: tuple[Event, ...]
    consumers: tuple[Consumer, ...]


STREAMS: tuple[Stream, ...] = (
    Stream(
        "identity::customer",
        "identity",
        (
            Event("identity.customer.events", "CustomerRegistered"),
            Event("identity.customer.events", "AccountSuspended"),
            Event("identity.customer.events", "AccountReactivated"),
        ),
        (
            Consumer("ordering", "ordering.order.identity_subscriber", "IdentityEventsSubscriber"),
            Consumer("loyalty", "loyalty.reward.identity_subscriber", "CustomerRegisteredSubscriber"),
            Consumer("notifications", "notifications.notification.identity_subscriber", "IdentityEventsSubscriber"),
            Consumer("notifications", "notifications.preference.identity_subscriber", "PreferenceIdentitySubscriber"),
        ),
    ),
    Stream(
        "catalogue::product",
        "catalogue",
        (
            Event("catalogue.product.events", "ProductCreated"),
            Event("catalogue.product.events", "VariantAdded"),
            Event("catalogue.product.events", "ProductDiscontinued"),
        ),
        (
            Consumer("inventory", "inventory.stock.catalogue_subscriber", "CatalogueVariantSubscriber"),
            Consumer("ordering", "ordering.cart.catalogue_subscriber", "CatalogueEventsSubscriber"),
        ),
    ),
    Stream(
        "ordering::order",
        "ordering",
        (
            Event("ordering.order.events", "OrderCreated"),
            Event("ordering.order.events", "OrderConfirmed"),
            Event("ordering.order.events", "OrderDelivered"),
            Event("ordering.order.events", "OrderReturned"),
            Event("ordering.order.events", "OrderCancelled"),
        ),
        (
            Consumer("payments", "payments.payment.ordering_subscriber", "OrderReturnedSubscriber"),
            Consumer("fulfillment", "fulfillment.fulfillment.order_subscriber", "OrderEventsSubscriber"),
            Consumer("inventory", "inventory.stock.ordering_subscriber", "OrderingEventsSubscriber"),
            Consumer("reviews", "reviews.review.ordering_subscriber", "OrderDeliveredSubscriber"),
            Consumer("loyalty", "loyalty.reward.ordering_subscriber", "OrderDeliveredSubscriber"),
            Consumer("notifications", "notifications.notification.ordering_subscriber", "OrderingEventsSubscriber"),
        ),
    ),
    Stream(
        "ordering::cart",
        "ordering",
        (Event("ordering.cart.events", "CartAbandoned"),),
        (Consumer("notifications", "notifications.notification.cart_subscriber", "CartEventsSubscriber"),),
    ),
    Stream(
        "inventory::inventory_item",
        "inventory",
        (
            Event("inventory.stock.events", "StockReserved"),
            Event("inventory.stock.events", "ReservationReleased"),
            Event("inventory.stock.events", "LowStockDetected"),
        ),
        (
            Consumer("ordering", "ordering.checkout.inventory_subscriber", "InventoryEventsSubscriber"),
            Consumer("notifications", "notifications.notification.inventory_subscriber", "InventoryEventsSubscriber"),
        ),
    ),
    Stream(
        "payments::payment",
        "payments",
        (
            Event("payments.payment.events", "PaymentSucceeded"),
            Event("payments.payment.events", "PaymentFailed"),
            Event("payments.payment.events", "RefundCompleted"),
        ),
        (
            Consumer("ordering", "ordering.checkout.payment_subscriber", "PaymentEventsSubscriber"),
            Consumer("fulfillment", "fulfillment.fulfillment.payment_subscriber", "PaymentEventsSubscriber"),
            Consumer("loyalty", "loyalty.reward.payments_subscriber", "PaymentRefundedSubscriber"),
            Consumer("notifications", "notifications.notification.payment_subscriber", "PaymentEventsSubscriber"),
        ),
    ),
    Stream(
        "fulfillment::fulfillment",
        "fulfillment",
        (
            Event("fulfillment.fulfillment.events", "ShipmentHandedOff"),
            Event("fulfillment.fulfillment.events", "DeliveryConfirmed"),
            Event("fulfillment.fulfillment.events", "DeliveryException"),
        ),
        (
            Consumer("ordering", "ordering.order.fulfillment_subscriber", "FulfillmentEventsSubscriber"),
            Consumer("inventory", "inventory.stock.fulfillment_subscriber", "FulfillmentEventsSubscriber"),
            Consumer(
                "notifications", "notifications.notification.fulfillment_subscriber", "FulfillmentEventsSubscriber"
            ),
        ),
    ),
    Stream(
        "reviews::review",
        "reviews",
        (
            Event("reviews.review.events", "ReviewApproved"),
            Event("reviews.review.events", "ReviewRejected"),
        ),
        (
            Consumer("loyalty", "loyalty.reward.reviews_subscriber", "ReviewApprovedSubscriber"),
            Consumer("notifications", "notifications.notification.review_subscriber", "ReviewEventsSubscriber"),
        ),
    ),
    Stream(
        "loyalty::reward_account",
        "loyalty",
        (
            Event("loyalty.reward.events", "RewardAccountEnrolled"),
            Event("loyalty.reward.events", "PointsEarned"),
            Event("loyalty.reward.events", "PointsRedeemed"),
            Event("loyalty.reward.events", "TierUpgraded"),
        ),
        (Consumer("notifications", "notifications.notification.loyalty_subscriber", "LoyaltyEventsSubscriber"),),
    ),
)


def _import(module: str, cls: str):
    return getattr(__import__(module, fromlist=[cls]), cls)


@dataclass(frozen=True)
class Pair:
    stream: Stream
    event: Event
    consumer: Consumer

    @property
    def id(self) -> str:
        return f"{self.event.cls}->{self.consumer.domain}.{self.consumer.cls}"


PAIRS: list[Pair] = [
    Pair(stream, event, consumer)
    for stream in STREAMS
    for event, consumer in itertools.product(stream.events, stream.consumers)
]


@pytest.mark.parametrize("pair", PAIRS, ids=[p.id for p in PAIRS])
def test_acl_payload_translates_without_keyerror(pair: Pair, request):
    producer_bed = request.getfixturevalue(f"{pair.stream.producer}_bed")
    consumer_bed = request.getfixturevalue(f"{pair.consumer.domain}_bed")

    # Build the real external payload in the PRODUCER's context...
    with producer_bed.domain_context():
        payload = build_payload(pair.stream.producer, _import(pair.event.module, pair.event.cls))

    # ...then translate it through the real subscriber in the CONSUMER's context.
    with consumer_bed.domain_context():
        subscriber = _import(pair.consumer.module, pair.consumer.cls)()
        try:
            subscriber(payload)
        except KeyError as exc:
            pytest.fail(
                f"ACL contract violation: {pair.consumer.cls} read {exc} from the "
                f"{pair.event.cls} payload, but the producer does not emit that key. "
                f"A field was dropped/renamed on one side of {pair.stream.name}."
            )
        except Exception:
            # Downstream business/precondition failures (e.g. a dispatched command
            # with no target aggregate) are not payload-contract violations. The
            # translation itself succeeded - that is all P15 asserts.
            pass


# --- teeth: prove the check catches a dropped field a subscriber HARD-reads --

# Known hard `data[...]` reads (one per consumer domain, from the ACL wiring):
# (producer, Event, Consumer, the field the subscriber reads as data[field]).
# Dropping that field from the producer payload MUST make the subscriber KeyError,
# proving the contract check above is not passing vacuously.
_HARD_READS = [
    (
        "catalogue",
        Event("catalogue.product.events", "VariantAdded"),
        Consumer("inventory", "inventory.stock.catalogue_subscriber", "CatalogueVariantSubscriber"),
        "product_id",
    ),
    (
        "reviews",
        Event("reviews.review.events", "ReviewApproved"),
        Consumer("notifications", "notifications.notification.review_subscriber", "ReviewEventsSubscriber"),
        "review_id",
    ),
    (
        "payments",
        Event("payments.payment.events", "PaymentSucceeded"),
        Consumer("notifications", "notifications.notification.payment_subscriber", "PaymentEventsSubscriber"),
        "customer_id",
    ),
    (
        "ordering",
        Event("ordering.order.events", "OrderCreated"),
        Consumer("notifications", "notifications.notification.ordering_subscriber", "OrderingEventsSubscriber"),
        "order_id",
    ),
]


@pytest.mark.parametrize(
    "producer,event,consumer,field",
    _HARD_READS,
    ids=[f"{e.cls}.{fld}->{c.cls}" for _, e, c, fld in _HARD_READS],
)
def test_dropped_hard_read_field_is_caught(producer, event, consumer, field, request):
    """Falsification: dropping a field a subscriber hard-reads (`data[field]`) makes
    it KeyError - so the contract check has teeth for this pair, not a vacuous pass."""
    producer_bed = request.getfixturevalue(f"{producer}_bed")
    consumer_bed = request.getfixturevalue(f"{consumer.domain}_bed")

    with producer_bed.domain_context():
        event_cls = _import(event.module, event.cls)
        intact = build_payload(producer, event_cls)
        broken = build_payload(producer, event_cls, drop=field)

    with consumer_bed.domain_context():
        subscriber = _import(consumer.module, consumer.cls)()
        # Intact payload translates (may fail downstream, but never with KeyError).
        try:
            subscriber(intact)
        except KeyError:  # pragma: no cover - would mean the intact contract is broken
            pytest.fail(f"intact {event.cls} payload should not raise KeyError in {consumer.cls}")
        except Exception:
            pass
        # Dropping the hard-read field MUST surface as KeyError.
        with pytest.raises(KeyError):
            subscriber(broken)
