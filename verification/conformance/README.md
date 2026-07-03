# Adapter conformance — T2.5

The same declarative persistence behaviors must hold on every Protean provider.
This harness runs one behavior per test across **memory / sqlite / postgresql**
and compares. It's `[nightly]`/local (needs Docker Postgres on :15432), and it's
deliberately built ON Protean's own adapter-conformance plugin — so the cases can
be pushed upstream into Protean's generic suite (which is exactly what T2.5 asks).

## How it works

Protean ships `protean.integrations.pytest.adapter_conformance` (the `--db`
option, a `test_domain` fixture, a `db` fixture that creates/drops artifacts,
capability markers, per-test resets). Our `conftest.py` overrides two of its
fixtures: `db_config` (point Postgres at :15432, SQLite at a temp file) and
`test_domain` (register the tiny `elements.py` aggregates/projection). Each
provider runs in its own invocation, so there are no cross-provider model clashes.

```bash
make conformance     # runs all three adapters and prints the skip-rate

# or one adapter at a time:
PYTHONPATH=src pytest verification/conformance/ \
    -p protean.integrations.pytest.adapter_conformance --db MEMORY -q
```

The harness is **excluded from the normal `pytest verification/` run** (a
`pytest_ignore_collect` guard in `verification/conftest.py` skips it unless `--db`
is on the command line), so it never breaks CI's memory/postgres jobs.

## What it checks (13 behaviors)

add/get, get-missing → `ObjectNotFoundError`, filter (exact + `gte`/`in`/`contains`
lookups), exclude, order_by (asc/desc), limit+offset pagination, count, update,
delete, unique-index enforcement, and `Dict()` round-trip on an aggregate AND a
projection.

## Result

**13/13 pass on all three adapters. Skip-rate: 0%** — every behavior here is
provider-agnostic by contract, so nothing skips today. Two cases are divergence
hunters:

- **unique-index enforcement** — asserts a duplicate on a unique field is rejected
  on every adapter. (Historically the in-memory adapter didn't — proteanhq/
  protean#1071, now fixed and separately guarded in `verification/regression/`.)
  The exception TYPE still differs across adapters (memory raises a Protean error,
  SQL an `IntegrityError`); the harness asserts *rejection*, not the type.

- **`Dict()` round-trip (aggregate + projection)** — passes on postgresql and
  sqlite. This **corrects the T2.4 finding.** T2.4 reported that
  `reviews.ProductRating.counted_reviews` (a `Dict()` projection field) 500'd with
  `UndefinedColumn`, and speculated a "Dict field gets no column" schema-generation
  gap. That was wrong: a `Dict` field DOES get a column on a freshly created table
  (proven here on both SQL adapters). The T2.4 500 was a **stale-table artifact** —
  `protean db setup` / `create_all` creates only MISSING tables and does not ALTER
  an existing one to add a newly-declared column, so the pre-existing
  `product_rating` table (created before `counted_reviews` was added) never gained
  the column. That's a no-auto-migration property (expected of `create_all`), not a
  Dict-type bug. T2.4's docs have been corrected accordingly.
