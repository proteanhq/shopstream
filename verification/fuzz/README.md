# API fuzzing (schemathesis) — T2.4

Property: the API should never return a **500** (unhandled exception) on any
input the OpenAPI schema allows. A 500 is a shallow contract bug — a crash where
a 4xx (validation / not-found) was the right answer. schemathesis generates
thousands of schema-valid-and-invalid requests per operation and reports crashes.

This is `[nightly]`/local, NOT part of CI: it needs the full running stack, and
its findings depend on the database being freshly provisioned (a stale schema
produces `UndefinedColumn`/`no such table` 500s that are provisioning artifacts,
not code bugs).

## Run it

```bash
# 1. Install the tool (opt-in; deliberately NOT added to uv.lock — see below)
make fuzz-install

# 2. Bring up a CLEAN stack (fresh schema is essential for trustworthy findings)
make docker-up && make drop-db && make setup-db && make truncate-db
make api                                                  # :8000
make engine-ordering & make engine-inventory & make engine-payments &

# 3. Fuzz for server errors (the signal that matters)
make fuzz            # --checks not_a_server_error
make fuzz-full       # everything (adds schema-conformance + undocumented-4xx noise)
```

Why `fuzz-install` uses `uv pip install` and not a `[dependency-groups]` entry:
adding a group forces a `uv lock`, which re-resolves protean's `rev=main` pin and
would silently bump it off the committed commit. Until that pin is frozen, the
fuzz tool is installed into the venv on demand. (The deferred `[verification]`
dependency group from T0.4 lands with a lock refresh, separately.)

## Findings (first run, 140 operations, ~3.3k cases)

**Fixed in this change:**
- **Pagination overflow → 500.** List endpoints (`GET /orders`, `/products`,
  `/reviews`, `/reviews/customer/{id}`) declared `page: int = 1, page_size:
  int = 20` with no bounds. A huge `page` × huge `page_size` makes
  `offset = (page-1)*page_size` overflow Postgres `bigint` →
  `NumericValueOutOfRange` → 500. Fixed by bounding both with FastAPI `Query`
  (`page` 1..1_000_000, `page_size` 1..100) → out-of-range now returns 422.

**Filed / candidate (NOT a fix here):**
- **`ProductRating.counted_reviews` (a `Dict()` projection field) gets no DB
  column.** `protean db setup` materializes `product_rating` without a
  `counted_reviews` column, so any query touching it (`GET /reviews/ratings/{id}`)
  500s with `UndefinedColumn`. Reproduces on a freshly provisioned base-env DB, so
  it is a real schema-generation gap for `Dict` projection fields, not a stale-env
  artifact — candidate Protean issue. Tracked, not fixed in T2.4.

**Lower-priority (documentation, not crashes):**
- Many "undocumented HTTP status code" and "API rejected schema-compliant request"
  findings = the OpenAPI schema under-documents 4xx (400/404/422) responses. Real
  contract-doc gaps, but not runtime bugs; deferred.
