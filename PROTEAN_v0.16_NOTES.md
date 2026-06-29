# Protean v0.16 — Improvement Notes (from ShopStream sync)

Running list of snags and rough edges found while syncing ShopStream to Protean
v0.16.0. Intended to be taken forward in a dedicated Protean session. Each item
notes what was observed and a suggested direction.

Date started: 2026-06-29 (ShopStream → 0.16.0 sync)

## Status

**Update:** the patch-scope fixes below (items 2, 3, 7) are now **fixed and merged
into Protean `main`**. ShopStream pins Protean to git `main` and the full suite is
green against it (2410 passed, 98.82%). v0.16.1 is **not released yet** — the
proving-ground work continues, so more issues may surface before a patch is cut;
repin to `==0.16.1` once it ships.

| # | Item | Status |
|---|------|--------|
| 2 | Outbox composite-index fix (blocker) | ✅ Fixed + regression test + changelog fragment (`changes/944.fixed.md`) + doc update |
| 3 | `assert_invalid`/`assert_valid` removal undocumented | ✅ Backfilled `### Removed` into 0.16.0 CHANGELOG with migration |
| 7 | CLI logs corrupt machine stdout (`ir show`) | ✅ Fixed — console logs now go to stderr (`utils/logging.py`); 738 logging+cli tests pass |
| 4 | `ir check` vs `ir diff` staleness inconsistency | ⏳ Deferred to 0.17 (not patch-scope) |
| 5 | `PROJECTION_WITHOUT_PROJECTOR` false-positive | ⏳ Deferred to 0.17 |
| 6 | Health-server bind/port defaults (multi-engine) | ⏳ Deferred to 0.17; ShopStream works around via per-domain ports |
| 1 | Default CLI log verbosity (DEBUG) | ⏳ Soft — now on stderr so no longer corrupts output |

**0.16.1 (patch) scope:** items 2, 3, 7 (regressions/bugs) — **merged to `main`**.
Items 1, 4, 5, 6 are design/UX changes better suited to 0.17.

### Filed as GitHub issues (proteanhq/protean)

- [#1009](https://github.com/proteanhq/protean/issues/1009) — Outbox unique index breaks multi-broker dual-write (note #2, fix staged)
- [#1010](https://github.com/proteanhq/protean/issues/1010) — CLI logs corrupt machine stdout (notes #1/#7, fix staged)
- [#1011](https://github.com/proteanhq/protean/issues/1011) — `assert_invalid`/`assert_valid` removed without changelog (note #3, changelog backfilled)
- [#1012](https://github.com/proteanhq/protean/issues/1012) — `ir check` vs `ir diff` staleness inconsistency (note #4)
- [#1013](https://github.com/proteanhq/protean/issues/1013) — `PROJECTION_WITHOUT_PROJECTOR` false-positive (note #5)
- [#1014](https://github.com/proteanhq/protean/issues/1014) — Health-server multi-engine port collision (note #6)
- [#1015](https://github.com/proteanhq/protean/issues/1015) — Handler resilience options absent from IR (note #8)

---

## 1. CLI diagnostics are drowned out by default debug logging
- **Where:** `protean upgrade-check` (and CLI commands generally, e.g. `db setup`,
  `check`).
- **Observed:** Running `protean upgrade-check --domain x.domain` prints a large
  volume of `[debug] Loaded ... / Registered Element ...` domain-loading lines
  before the actual report. With `--format json`, the JSON is interleaved with
  framework debug logs, so the output is unparseable unless you add BOTH
  `PROTEAN_NO_AUTO_LOGGING=1` and `--log-level CRITICAL`.
- **Why it matters:** A read-only diagnostic's primary output is the report. The
  signal-to-noise ratio out of the box is poor; a user's first experience of the
  new upgrade tool is a wall of debug text.
- **Suggested direction:** Default CLI commands to WARNING+ on the console (auto
  logging at DEBUG feels like a dev-only default leaking into UX). At minimum,
  `--format json` should emit ONLY machine output to stdout and route all
  framework logs to stderr, so `... --format json 2>/dev/null` always yields clean
  JSON. Consider a `--quiet` global flag.

---

## 2. 🔴 BLOCKER BUG — unique `message_id` outbox index breaks multi-broker dual-write
- **Where:** `src/protean/utils/outbox.py:332` — `Index("message_id", unique=True)`
  (one of the new "recommended" outbox indexes added in 0.16, #944/#972).
- **Conflict with:** `src/protean/core/unit_of_work.py:235-264` — when an event is
  `published=True` and `[outbox].external_brokers` is set, Protean writes **N
  outbox rows for the same event** — one per target broker — *all sharing the same
  `message_id`* (`event._metadata.headers.id`), differentiated only by the
  `target_broker` column:
    - internal row: `message_id=<id>, target_broker="default"`
    - external row: `message_id=<id>, target_broker="global"`
- **Symptom:** Every `published=True` command flow fails at UoW commit with
  `psycopg2.errors.UniqueViolation: duplicate key value violates unique constraint
  "uq_outbox_message_id" ... Key (message_id)=(identity::customer-<id>-0.1) already
  exists.` This blocks ALL cross-domain published-event flows — i.e. the core ACL
  architecture — across every domain. Surfaced immediately in
  `tests/identity/application/` (24/24 DB-backed tests fail).
- **Root cause:** The unique index is on `message_id` alone, but the framework's own
  dual-write feature makes `message_id` non-unique by design. Uniqueness should be
  on the composite `(message_id, target_broker)`.
- **Suggested fix (upstream):** change outbox.py:332 to
  `Index("message_id", "target_broker", unique=True)`. Audit `find_by_message_id`
  (outbox.py:559) and any idempotency/claim logic that assumes one row per
  message_id — with dual-write there are legitimately multiple. Add a regression
  test with `external_brokers` configured. Candidate for a 0.16.1 patch.
- **Severity:** HIGH — makes 0.16 unusable for any domain that publishes events to
  an external bus (the documented cross-domain pattern).

---

## 3. 🟡 `assert_invalid` / `assert_valid` removed without a changelog "Removed" entry
- **Where:** removed in commit `6729ea14` ("Remove assert_valid and assert_invalid
  from testing DSL"). `protean.testing` went from a package exposing these helpers
  to a module that does not.
- **Observed:** ShopStream had 8 test modules importing
  `from protean.testing import assert_invalid` (27 call sites). On 0.16 these fail
  at collection time with `ImportError: cannot import name 'assert_invalid'`.
- **Gap:** The 0.16.0 CHANGELOG has **no `### Removed` section** and no mention of
  this removal. A public, documented testing helper disappeared with zero migration
  breadcrumb in the changelog (the rationale + replacement live only in the commit
  message: use `pytest.raises(ValidationError, match=...)`).
- **Suggested direction:** Add a `### Removed` (or `### Breaking`) changelog entry
  for any public-API removal, with the one-line migration (`assert_invalid(op,
  message=X)` → `pytest.raises(ValidationError, match=X)`). Consider a deprecation
  cycle (0.16 warn, 0.17 remove) for testing-DSL helpers, since they show up in
  every downstream test suite. The new `protean upgrade-check` could also flag
  removed-symbol imports it can detect.

---

## 4. 🟢 `ir check` flags staleness when only `generated_at` changed
- **Observed:** After upgrading 0.15→0.16, `protean ir check` reported every domain
  as "stale," but `protean ir diff` reported "No changes detected." Regenerating the
  baselines produced a one-line git diff per file — only the `generated_at`
  timestamp.
- **Inconsistency:** `ir check` (staleness) and `ir diff` (content) disagree. A
  staleness signal driven by a timestamp/version embedded in the materialized file
  creates churn with no real domain change, and is confusing right after an upgrade.
- **Suggested direction:** Base staleness on a content checksum that excludes
  volatile metadata (`generated_at`, framework version), so `ir check` and `ir diff`
  agree. Or have `ir check` print *why* it is stale (content vs. metadata/version).

## 5. 🟢 `PROJECTION_WITHOUT_PROJECTOR` warns on subscriber/ACL-populated projections
- **Observed:** `protean check` warns for `ordering.SuspendedAccount` and
  `reviews.VerifiedPurchases`: "Projection has no projector to populate it." Both are
  legitimately populated by cross-domain subscribers (the ACL pattern), not by an
  in-domain `@projector`.
- **Suggested direction:** Teach the check to recognize projections written by
  subscribers/handlers (e.g. detect `repository_for(<Projection>)` writes in
  subscriber/handler bodies), or provide an opt-out marker
  (`@domain.projection(externally_populated=True)`) to suppress the false positive.
  Minor: `protean check` exits non-zero on warnings-only, which trips
  `&&`-style scripting that treats warnings as failures.

## 6. 🟢 Health server + Observatory default-bind asymmetry
- **Observed:** 0.16 made `protean observatory` default to loopback (good, secure),
  but the new Engine health server (`[server.health]`) still defaults to
  `host = "0.0.0.0"` (config.py) — and ALSO defaults to a single fixed port 8080,
  which collides when running multiple engines on one host (ShopStream runs 8).
- **Suggested direction:** For consistency with the Observatory hardening, consider
  defaulting the health server to loopback too (it exposes liveness/readiness, less
  sensitive, but the asymmetry is surprising). More importantly, document/encourage
  per-domain port assignment for multi-engine single-host setups, or derive a
  non-colliding default. ShopStream worked around this by setting
  `[server.health] port` per domain (8081–8088).

## 7. 🟢 Noisy default logging on all CLI commands (broader than #1)
- `db setup`, `db drop`, `check`, `ir show` all emit verbose `[debug]`/`[info]`
  domain-load logs by default. For `ir show` this is actively harmful: the logs land
  on stdout and corrupt the JSON unless you pass `PROTEAN_NO_AUTO_LOGGING=1
  --log-level CRITICAL` AND redirect stderr. `ir show` (machine output) should never
  interleave logs into stdout.

---

## 8. 🟢 Handler resilience options absent from the IR
- **Observed:** Adding `@command_handler(timeout=…, retries=…, backoff=…)` to a
  handler does not change the materialized IR — none of `timeout`, `retries`,
  `backoff`, `retry_exceptions` appear in `protean ir show` output.
- **Why it matters:** These options change runtime behavior (deadline enforcement,
  transient-retry policy), but `ir diff` / staleness checks won't catch a change to
  them, and the Observatory Domain Visualizer can't display them.
- **Suggested direction:** Include the deadline/retry policy in the handler's IR
  node (alongside `part_of` and handled message types) so it is diffable and
  visualizable. Low priority.

---
<!-- Append new findings below as they come up. -->
