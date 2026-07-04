"""Aggregates exercised by the adapter-conformance harness.

Defined once against a definitions-only domain, then RE-REGISTERED on a fresh
per-provider domain by the conftest (one provider per `pytest --db` run). Kept
deliberately tiny and free of ShopStream domain logic — this is about Protean's
persistence adapters, nothing else.
"""

from protean import Domain
from protean.fields import Dict, Identifier, Integer, String

conformance_defs = Domain(name="conformance_defs")


@conformance_defs.aggregate
class ConfItem:
    """Scalar fields — the bread-and-butter of the query/DAO conformance cases."""

    name = String(max_length=50, required=True)
    score = Integer(default=0)
    category = String(max_length=30)


@conformance_defs.aggregate
class UniqueItem:
    """A unique field — exercises unique-index enforcement across adapters."""

    code = String(max_length=20, unique=True)
    label = String(max_length=50)


@conformance_defs.aggregate
class DictItem:
    """A `Dict()` field on an AGGREGATE — structured-value round-tripping."""

    name = String(max_length=50)
    payload = Dict()


@conformance_defs.projection
class DictProjection:
    """A `Dict()` field on a PROJECTION — the exact shape of the T2.4 finding
    (reviews.ProductRating.counted_reviews). Proves a Dict projection field DOES
    get a column on a freshly created SQL table, refuting the 'no column' theory."""

    key = Identifier(identifier=True, required=True)
    payload = Dict()


CONFORMANCE_ELEMENTS = [ConfItem, UniqueItem, DictItem, DictProjection]
