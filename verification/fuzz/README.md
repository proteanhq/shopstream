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

**Investigated further — CORRECTED by T2.5 (see verification/conformance/):**
- `GET /reviews/ratings/{id}` 500s with `UndefinedColumn: product_rating.
  counted_reviews`. T2.4 originally speculated this was a "Dict projection field
  gets no column" schema-generation gap. **That was wrong.** The T2.5 conformance
  harness proves a `Dict()` field DOES get a column on a freshly created table, on
  both postgresql and sqlite, for aggregates AND projections. The real cause is a
  **stale table**: `protean db setup` / `create_all` creates only MISSING tables
  and does not ALTER an existing one to add a newly-declared column, so the
  `product_rating` table (created before `counted_reviews` was added) never gained
  the column. That's a no-auto-migration property of `create_all` (drop + recreate,
  or a real migration, is needed), not a Dict-type bug.

**Lower-priority (documentation, not crashes):**
- Many "undocumented HTTP status code" and "API rejected schema-compliant request"
  findings = the OpenAPI schema under-documents 4xx (400/404/422) responses. Real
  contract-doc gaps, but not runtime bugs; deferred.
