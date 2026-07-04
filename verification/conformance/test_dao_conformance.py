"""Adapter conformance — one declarative behavior per test, run across adapters.

Each test asserts a persistence behavior that MUST be identical on every Protean
provider. Run the whole file once per provider (`--db MEMORY|SQLITE|POSTGRESQL`);
`make conformance` runs all three and prints the skip-rate. A test that a provider
genuinely cannot satisfy should `skip` (tracked), not fail — the skip report is
the skip-rate. A test that FAILS on one provider but passes on another is a real
adapter divergence (a Protean bug worth filing — this harness is meant to be
pushed upstream).

The behaviors here are provider-agnostic by contract, so nothing skips today; the
two divergence-hunting cases (unique-index enforcement, Dict-field round-trip)
carry notes on what they'd reveal.
"""

import pytest
from protean.exceptions import ObjectNotFoundError

from verification.conformance.elements import ConfItem, DictItem, DictProjection, UniqueItem

# The `db` fixture (from Protean's adapter-conformance plugin) creates/drops the
# provider's tables around each test; apply it to every test in the module.
pytestmark = pytest.mark.usefixtures("db")


def _seed(test_domain, rows):
    repo = test_domain.repository_for(ConfItem)
    made = []
    for name, score, category in rows:
        item = ConfItem(name=name, score=score, category=category)
        repo.add(item)
        made.append(item)
    return repo, made


# --- add / get ---------------------------------------------------------------


def test_add_then_get_round_trips(test_domain):
    repo = test_domain.repository_for(ConfItem)
    item = ConfItem(name="alpha", score=5, category="x")
    repo.add(item)

    fetched = repo.get(item.id)
    assert fetched.id == item.id
    assert fetched.name == "alpha"
    assert fetched.score == 5


def test_get_missing_raises_object_not_found(test_domain):
    repo = test_domain.repository_for(ConfItem)
    try:
        repo.get("does-not-exist")
        raise AssertionError("expected ObjectNotFoundError for a missing id")
    except ObjectNotFoundError:
        pass


# --- query: filter / lookups / exclude ---------------------------------------


def test_filter_exact(test_domain):
    repo, _ = _seed(test_domain, [("a", 1, "red"), ("b", 2, "blue"), ("c", 3, "red")])
    rows = repo._dao.query.filter(category="red").all().items
    assert {r.name for r in rows} == {"a", "c"}


def test_filter_lookups_gte_in_contains(test_domain):
    repo, _ = _seed(test_domain, [("a", 1, "red"), ("b", 5, "blue"), ("c", 9, "green")])
    assert {r.name for r in repo._dao.query.filter(score__gte=5).all().items} == {"b", "c"}
    assert {r.name for r in repo._dao.query.filter(category__in=["red", "green"]).all().items} == {"a", "c"}
    assert {r.name for r in repo._dao.query.filter(name__contains="a").all().items} == {"a"}


def test_exclude(test_domain):
    repo, _ = _seed(test_domain, [("a", 1, "red"), ("b", 2, "blue")])
    rows = repo._dao.query.exclude(category="red").all().items
    assert {r.name for r in rows} == {"b"}


# --- ordering / pagination / count -------------------------------------------


def test_order_by_desc_and_asc(test_domain):
    repo, _ = _seed(test_domain, [("a", 1, "x"), ("b", 3, "x"), ("c", 2, "x")])
    desc = [r.name for r in repo._dao.query.order_by("-score").all().items]
    asc = [r.name for r in repo._dao.query.order_by("score").all().items]
    assert desc == ["b", "c", "a"]
    assert asc == ["a", "c", "b"]


def test_limit_offset_pagination(test_domain):
    repo, _ = _seed(test_domain, [(n, i, "x") for i, n in enumerate("abcde")])
    page = repo._dao.query.order_by("score").offset(1).limit(2).all()
    assert [r.name for r in page.items] == ["b", "c"]
    assert page.total == 5  # total ignores limit/offset


def test_count(test_domain):
    repo, _ = _seed(test_domain, [("a", 1, "red"), ("b", 2, "red"), ("c", 3, "blue")])
    assert repo._dao.query.all().total == 3
    assert repo._dao.query.filter(category="red").count() == 2


# --- update / delete ---------------------------------------------------------


def test_update_persists(test_domain):
    repo = test_domain.repository_for(ConfItem)
    item = ConfItem(name="alpha", score=1, category="x")
    repo.add(item)

    loaded = repo.get(item.id)
    loaded.score = 42
    repo.add(loaded)

    assert repo.get(item.id).score == 42


def test_delete_removes(test_domain):
    repo = test_domain.repository_for(ConfItem)
    item = ConfItem(name="alpha", score=1, category="x")
    repo.add(item)
    repo._dao.delete(repo.get(item.id))

    assert repo._dao.query.all().total == 0


# --- divergence hunters ------------------------------------------------------


def test_unique_index_is_enforced(test_domain):
    """Every adapter must reject a duplicate on a unique field. Historically the
    in-memory adapter did NOT (proteanhq/protean#1071, now fixed) — the exception
    TYPE still differs (memory raises a Protean error, SQL an IntegrityError), so
    we assert only that SOME error is raised, not which."""
    repo = test_domain.repository_for(UniqueItem)
    repo.add(UniqueItem(code="DUP", label="first"))
    try:
        repo.add(UniqueItem(code="DUP", label="second"))
    except Exception:  # noqa: BLE001 - any rejection is fine; the type differs across adapters
        return
    raise AssertionError("expected a duplicate 'code' to be rejected")


def test_dict_field_round_trips(test_domain):
    """A `Dict()` field must survive a persist/reload on every adapter. Memory
    stores dicts natively; the SQL adapters must generate a JSON-ish column. If
    this fails on postgresql/sqlite but passes on memory, it is the T2.4 finding
    (a Dict projection/aggregate field gets no DB column) surfaced as a
    conformance divergence."""
    repo = test_domain.repository_for(DictItem)
    item = DictItem(name="cfg", payload={"a": 1, "nested": {"b": [1, 2, 3]}})
    repo.add(item)

    reloaded = repo.get(item.id)
    assert reloaded.payload == {"a": 1, "nested": {"b": [1, 2, 3]}}


def test_dict_field_on_projection_round_trips(test_domain):
    """A `Dict()` field on a PROJECTION round-trips on every adapter when the table
    is freshly created. This is the exact shape of the T2.4 finding
    (reviews.ProductRating.counted_reviews 500'ing with UndefinedColumn) — and it
    PASSES here, on postgresql and sqlite. So that field DOES get a column on a
    fresh schema; the T2.4 500 was a stale-table artifact (`protean db setup` /
    create_all creates only MISSING tables and does not ALTER an existing one to
    add a newly-declared column), not a Dict-type schema-generation bug."""
    repo = test_domain.repository_for(DictProjection)
    repo.add(DictProjection(key="k1", payload={"count": 3, "ids": ["a", "b"]}))

    reloaded = repo.get("k1")
    assert reloaded.payload == {"count": 3, "ids": ["a", "b"]}
