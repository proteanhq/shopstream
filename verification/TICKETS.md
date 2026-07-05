# Verification tickets

Work items to build ShopStream into Protean's verification surface, in priority
order. Each ticket lists what to do, how to know it is done, where the check's
answer comes from (A strongest, see VERIFICATION_STRATEGY.md section 2), and
whether it gates PRs / nightly / releases.

`[A]/[B]/[C]` = answer source. `[gate]` = blocks releases. `[nightly]` = reports only.

---

## Phase 0 - foundation (do first)

**T0.1 - `process_and_wait(command)` helper** `[A]` `[gate]` - DONE (local seed; upstream filed)
- `verification/support/processing.py` ships `process_and_wait(command, domain)`
  and the `drain(domain, until=...)` primitive under it. Same test body works
  whether events fire inline (sync: memory/test env) or via a background engine
  (async): sync returns as soon as the handler does; async drains the engine.
- Sync contract is covered end to end in CI (`verification/support/test_processing.py`,
  memory mode); the async control flow (cycle count, early stop, max-cycle bound,
  sync-vs-async branching) is covered there too with a stubbed engine. The real
  engine path is exercised by the DLQ test, now refactored onto `drain`
  (`tests/loyalty/integration/test_dlq.py`) — validated locally against Redis.
- The richer version — one that also returns the events that fired and any
  handler error without reaching into framework internals — belongs in
  `protean.testing`. Filed upstream as proteanhq/protean#1065. When it lands,
  swap this seed for it and migrate the remaining `loadtests/` `time.sleep`s.

**T0.2 - Turn the IR diff into a real gate** `[A/C]` `[gate]` - DONE
- `.protean/config.toml` strictness set to `strict` (breaking changes now exit 1).
- New `make ir-gate` target fails on a breaking IR change vs the committed
  baseline (non-breaking drift is a note, not a failure).
- CI (`.github/workflows/ci.yml`) runs `make ir-gate` on every push.
- Negative test `verification/contracts/test_ir_gate.py` proves a breaking
  removal exits 1 and no-change exits 0 (guards against strictness silently
  reverting to `warn`).
- Baselines refreshed to current Protean main in the same change.

**T0.3 - P20 same-event-twice check** `[A]` `[gate]` - DONE
- `verification/oracles/test_p20_projector_idempotency.py` — the check.
- `ProductRatingProjector` made idempotent: it records counted reviews
  (`counted_reviews`) and treats a redelivered event as a no-op; stats are
  derived from that set. The xfail is removed — the check now passes.
- The framework-level fix (consume-side dedup) is separate: proteanhq/protean#1042.
- Follow-up: extend the same check to the other accumulating projectors.

**T0.4 - Set up the `verification/` tree and the `src/` lint** `[-]` - DONE
- The `verification/` tree exists (oracles/, contracts/, conftest).
- `make check-src-clean` fails if reference code (`src/`) imports a
  test/verification tool (pytest/hypothesis/schemathesis/toxiproxy); wired into
  CI ("Reference code is test-tool free"). Verified it catches a violation.
- Deferred: the `[verification]` optional dependency group — the suite uses no
  heavy tools yet; add it when Phase 2 introduces schemathesis/Toxiproxy.

**T0.5 - Fix loyalty's false docstrings** `[-]` - DONE (resolved by the loyalty buildout)
- The previously-false claims are now implemented and tested: the second saga
  (`redemption/saga.py`, PRs #16 — 3 tests) and the custom database model
  (`projections/reward_account_view_model.py`, PR #25 — `test_custom_database_model.py`).
  `Auto(increment)` is no longer claimed in the docstring (it's honestly listed as
  a follow-up in `PROTEAN_COVERAGE.md`, tied to proteanhq/protean#1056).
- Verified every `src/loyalty/domain.py` docstring claim maps to real code + a test.
- `PROTEAN_COVERAGE.md` is honest: deferred items and their Protean issues (#1048,
  #1056) are documented transparently, no overclaims.
- The durable guard against doc drift is T1.6 (generate docs from the IR).

---

## Phase 1 - the real bug-finders

**T1.1 - Concurrency check: no lost updates (P2)** `[A]` `[gate]` - DONE
- `verification/oracles/test_no_lost_updates.py` (+ `_concurrency_worker.py`):
  spawns WORKERS separate processes that each fire one `ReserveStock(qty=1)` at
  ONE `InventoryItem` seeded with N units, on real Postgres + Message-DB, aligned
  on a barrier for maximal contention.
- Safety gate (always holds): `successes <= N` (never over-reserve — the
  lost-update bug), `reserved == successes`, `available == N - successes >= 0`,
  reservation count == successes. Type-A: expected values are hand-computed, not
  folded from the event stream.
- Liveness (retry on): all N units sell; the extra writers fail with "insufficient
  stock", not a dropped write.
- Falsification (`test_version_retry_is_load_bearing`): with `version_retry`
  disabled, real `ExpectedVersionError`s surface and `successes < N`, while safety
  still holds — proving the oracle has teeth and OCC never corrupts.
- Skips under `--protean-env memory` (fake transactions); runs in CI's Postgres
  job via `pytest verification/ --protean-env test`. Empirically stable (9/9
  runs `successes == N` with retry on; 1-2 without).

**T1.2 - Exactly-one outbox row (P4)** `[A]` `[gate]` - DONE
- `verification/oracles/test_outbox_exactly_once.py` (placed with the other
  property oracles rather than in `tests/integration/`, for consistency with
  P2/P20; the tests/ file already covers the happy-path dual-write):
- Shape: a `published=True` event (loyalty `EarnPoints`) yields exactly one row
  per (message_id, target_broker) — one `default` + one `global`, same
  message_id, no duplicates. Runs on any adapter.
- Teeth: forcing a second row with the same (message_id, target_broker) raises
  `IntegrityError` — the DB, not just app code, prevents double-publishing.
  Type-A (probes the unique index directly).
- Finding: the in-memory adapter does NOT enforce `Index(unique=True)` — the
  duplicate is silently accepted there, so the teeth test is Postgres-only
  (skips under `--protean-env memory`). Candidate Protean fidelity note.

**T1.3 - Crash-window check (P21)** `[A]` `[nightly]` - DONE (gap confirmed + filed)
- `verification/oracles/test_crash_window_reconcile.py`. Note: per ADR-0015 the
  order is now event-store append FIRST, then relational commit — so an
  event-sourced aggregate is NOT missing events after a crash (the ticket's
  original framing). The real window is: the event is durable but its OUTBOX row
  (relational) rolled back → a durable event that is never published.
- Crash is simulated deterministically in-process: patch SQLAlchemy
  `Session.commit` to raise (Message-DB uses its own psycopg2 pool, so the append
  still lands), reproducing the ADR-0015 window with no process kill.
- `test_crash_leaves_event_durable_but_unpublished` PASSES: characterizes the
  window (StockReceived durable in the event store, its internal outbox row absent).
- `test_reconcile_restores_the_lost_outbox_row` XFAIL (strict): ADR-0015 promises
  `reconcile_outbox` repairs this on startup, but it is a **no-op against
  Message-DB** — `read_last_message("$all")` returns None, so the sweep returns 0
  and the lost row is never restored. Filed proteanhq/protean#1073; xfail flips
  when fixed.
- Postgres + Message-DB only (skips under `--protean-env memory`).

**T1.4 - Concurrency model with Hypothesis (P2/P4)** `[A]` `[nightly]` - DONE
- `verification/model/test_inventory_model.py` — a Hypothesis `RuleBasedStateMachine`
  drives random valid sequences (receive / reserve / release / confirm / adjust)
  at one event-sourced `InventoryItem` (Stock, which is both "Stock" and the
  event-sourced aggregate) and asserts its stock position matches an INDEPENDENT
  plain-Python model after every step.
- Drives the aggregate directly (methods apply events in-memory) rather than the
  full command→persist→project→replay path: the projector fan-out per command made
  that path minutes-slow (150×25 ≈ 47 min); the aggregate-level version runs the
  same coverage in ~1.7s. State-machine correctness is what this targets.
- Finding: an all-default `StockLevels` VO round-trips to None (surfaced while
  building this); filed proteanhq/protean#1078. The model mirrors the aggregate's
  own None-as-zeros handling.
- Note: not literal concurrency (that is T1.1, multi-process) — this explores
  sequential interleavings an example-based test would miss.

**T1.5 - Regression set habit** `[A]` `[gate]` - DONE
- `verification/regression/` — the habit + a manifest (`README.md`) mapping every
  Protean issue ShopStream has filed to its guard and state (guard / open /
  tripwire). Each bug flips through `xfail(strict)` → passing guard as its fix
  lands, so a fixed bug can never quietly regress.
- Seeded from the filed issues. Most are FIXED (G1-G5 #1038-#1042, #1046, #1048,
  #1056, #1065): several are already guarded by existing oracles — #1040 →
  `test_crash_window_reconcile` (append-first durability), #1041 →
  `test_outbox_exactly_once`, #1042 → `test_p20_projector_idempotency`.
- New named regressions in `test_protean_regressions.py`:
  - `test_1039_...` — datetime payloads are ISO-8601/UTC (guard, passes).
  - `test_1071_...` — in-memory adapter enforces `Index(unique=True)`; an UPGRADE
    TRIPWIRE (`xfail(strict)`): fixed upstream but not yet in ShopStream's Protean
    pin, so it flips when the pin is bumped.
- Still-open bugs carry live xfails: #1073 (`test_crash_window_reconcile`), #1055
  (engine CI, `test_dlq` local-only).
- Bugs with no natural ShopStream reproduction (#1038 Decimal, #1046 Date, #1056
  Auto-increment) are recorded in the manifest rather than force-fit.

**T1.6 - Generate docs from the IR** `[A]` - DONE
- `docs/<domain>/catalog.md` is generated from the live domain elements
  (`make docs-catalog` → `protean docs generate --type=catalog`), so it cannot
  claim a feature the code lacks.
- `make docs-check` is the enforcement: it regenerates every catalog and fails if
  a committed one drifts (verified it has teeth). Wired into CI. It immediately
  caught a stale `ordering` catalog, now regenerated.
- Doctests on the value objects (Money, SKU, Rating) — executable examples in the
  docstrings, run by `make doctest` (`pytest --doctest-modules`), wired into CI.
- Folded in: `make ir` now uses `--canonical` (sorted keys + no volatile
  `generated_at`), so IR baselines diff only on real changes — no key-reorder or
  timestamp churn between runs/versions. All 9 baselines regenerated canonically.

---

## Phase 2 - breadth and depth

**T2.1 - Metamorphic checks (P9/P10/P11)** `[B]` `[gate]` - MOSTLY DONE (3 of 4; sync==async deferred)
- New `verification/metamorphic/` tree. Every module docstring states the source-B
  caveat up front: these compare two folds of the SAME stream, so they only catch
  bugs that DIVERGE between the paths — not bugs both paths share (that is what the
  type-A oracles are for). Auto-collected by CI's existing `pytest verification/`
  jobs (memory + Postgres); no workflow change needed.
- **P10 — `test_replay_equals_live.py`**: `repository.get(id)` (replay via
  from_events) must equal the live in-memory aggregate, full `to_dict()` incl.
  version / VOs / child entities. Parameterized over ALL FOUR event-sourced
  aggregates (Order, InventoryItem, Payment, PromoCampaign) — adding an ES
  aggregate is a one-row change plus its `*_bed` fixture.
  - **Finding (this check caught it) — FIXED in the same change:** the **Payment**
    aggregate's `PaymentAttempt` child entity carried no identity on its events
    (`PaymentInitiated` / `PaymentRetryInitiated`); `_on_payment_initiated` did
    `add_attempts(PaymentAttempt(...))` with no id, so Protean minted a **fresh
    uuid4 on every replay** → replayed != live, and the "complete audit trail of
    every charge" promise broke. `Order` does it right (pre-generates `OrderItem`
    ids, carries them on `OrderCreated`); Payment already did it right for refunds
    (`refund_id` on `RefundRequested`). Fixed by pre-generating `attempt_id` in
    `create()`/`retry()`, carrying it on both events, and using
    `PaymentAttempt(id=event.attempt_id, ...)` in the @apply handlers; payments IR
    baseline regenerated; two event-construction unit tests updated. The `payment`
    case is now a **passing regression guard** (fails if the id is ever dropped
    again). ShopStream reference-code bug, no Protean issue (user code calling
    uuid4() in an @apply handler — the framework cannot detect this).
- **P11 — `test_snapshot_equals_replay.py`**: for PromoCampaign
  (`snapshot_threshold=5`, the only snapshot-configured aggregate), full replay
  (captured before any snapshot) == snapshot load (after `create_snapshot`), and a
  second test proves snapshot + post-snapshot tail == live.
- **P9 — `test_projection_equals_fold.py`**: a read model == its aggregate's
  replayed state (two independent folds of one stream). Seeded with
  `InventoryLevel` (mirrors the `StockLevels` VO one-for-one). Registry-shaped for
  more projections. Docstring is explicit that this is the WEAK check and points at
  `test_p20_projector_idempotency` for the duplicate-in-stream blind spot.
- **sync == async — DONE (was deferred).** `verification/metamorphic/
  test_sync_equals_async.py` runs one FIXED inventory workload (init 20, reserve 3)
  twice against the same real Postgres — once with `event_processing="sync"` (events
  fire inline) and once with `"async"` (outbox + `Engine.run()` drain) — and asserts
  the two InventoryLevel projections are identical (bar the row id/timestamp). Same
  events, same fold, so the read model must match whichever path ran. `make
  sync-async-verify`. `@pytest.mark.engine` + base(async) env (needs the live engine
  + Redis, #1055) — deselected in CI and skips cleanly under memory/test, so it
  never breaks the normal suite. (The helper-level `sync`/`async` equivalence stays
  covered by `process_and_wait`/`drain`, T0.1; this adds the end-to-end read-model
  equivalence.)

**T2.2 - Cross-domain payload contracts (P15)** `[A]` `[gate]` - DONE
- `verification/contracts/test_acl_payloads.py`. For every stream, a real instance
  of each `published=True` event is built from its own declared fields and
  serialized exactly as the outbox does (`to_dict()` minus `_metadata` -> the
  `data` block, wrapped in `{"metadata":{"headers":{"type": "<Camel>.<Event>.v<n>"}},
  "data": ...}`), then fed through EVERY real subscriber on that stream via the
  subscriber's `__call__`. Asserts no KeyError. Type-A: the payload shape comes
  from the producer, independent of what the consumer expects — a rename on either
  side drops a key a subscriber hard-reads and the check fails.
- Coverage: full producer×consumer cross-product per stream (84 pairs across the 9
  streams) — a subscriber must also cleanly IGNORE the event types it does not
  handle. New event/subscriber = one line in the `STREAMS` registry. Added the 4
  missing `*_bed`/`*_ctx` fixtures (identity, catalogue, fulfillment, notifications)
  to `verification/conftest.py`.
- Teeth: 4 falsifications (`test_dropped_hard_read_field_is_caught`) — dropping a
  field a subscriber HARD-reads (`data[field]`) across 4 consumer domains
  (inventory CatalogueVariantSubscriber/product_id, notifications review/review_id,
  notifications payment/customer_id, notifications ordering/order_id) MUST raise
  KeyError. Proves the oracle is not passing vacuously.
- Honest limitation (in the module docstring): asserts on KeyError only. ShopStream
  subscribers are defensive — most reads are `data.get(key)`, which returns None
  instead of raising, so this check cannot see a field read via `.get()` that
  silently degrades. It catches the hard `data[key]` reads (the ones that crash a
  consumer). Downstream business failures (a dispatched command with no target
  aggregate) are tolerated — only the payload translation is under test.
- Finding (soft gaps the map surfaced, not KeyErrors — candidate ShopStream bugs,
  NOT fixed here): `OrderDelivered` carries only `order_id/customer_id/delivered_at`
  but reviews' `OrderDeliveredSubscriber` wants `data.get("items")` to record
  VerifiedPurchases — so VerifiedPurchases is never populated from the real event.
  Similarly `CartAbandoned` has no `customer_id` (notifications cart subscriber
  no-ops) and `OrderCancelled`/fulfillment events lack `customer_id` (notifications
  handlers are log-only by design). These are graceful-by-design except the
  OrderDelivered→items one, which is worth a follow-up (add `items` to
  `OrderDelivered`, or have reviews read them another way).

**T2.3 - Saga liveness + compensation (P16)** `[A]` `[nightly]` - DONE
- `verification/resilience/test_saga_compensation.py`. Drives a REAL checkout over
  HTTP against the running async stack (api + ordering/inventory/payments engines),
  forces the payment to fail `MAX_PAYMENT_RETRIES` (3) times, and asserts the two
  P16 outcomes end to end:
  - **liveness + order compensation**: the saga reaches terminal `Cancelled`
    (`cancelled_by="System"`, reason "Payment failed: …") within a bounded poll;
  - **cross-domain compensation**: the inventory reservation the checkout was
    holding is `Released` (OrderCancelled → external bus → inventory
    `ReleaseReservation`), read in-process from the same `_local` DB the engine
    writes to;
  - **stuck-saga detector**: reads the saga's own event-sourced PM stream
    (`ordering::order_checkout_saga-<order_id>`) and asserts its last transition is
    `is_complete` with state `failed`. The bounded polls are the liveness
    enforcement — a saga that never reaches terminal fails with the last-seen state.
- The forced-failure loop the exploration nailed down (there is NO auto-wiring):
  confirm → `POST /inventory/{id}/reserve` (→ StockReserved → RecordPaymentPending →
  Payment_Pending) → for each of 3 attempts `POST /payments` + `POST /payments/webhook`
  with `gateway_status="failed"` (+ header `X-Gateway-Signature: test-signature`);
  between retries re-drive `PUT /orders/{id}/payment/pending`. Failure is forced via
  the WEBHOOK, not the gateway `should_succeed` flag (nothing calls `create_charge`
  at runtime).
- Must run against the async engine: the saga is a multi-step PM that hits
  proteanhq/protean#1048 under `event_processing="sync"` (no cascade), and the
  cross-domain hops need the engines + external Redis bus. So it is
  `@pytest.mark.engine` (deselected in CI via `-m "not engine"`, like `test_dlq`,
  and skips cleanly when the stack/base-env is absent — never breaks the memory/
  test suite). Run it in base (async) env: `--protean-env development` (no
  `[development]` overlay → base config, `_local` DBs) with the stack up. Validated
  locally: 3/3 stable runs.

**T2.4 - schemathesis API fuzzing** `[A]` `[nightly]` - DONE (harness + 1 bug fixed, 1 filed)
- Harness: `make fuzz` (server errors only) / `make fuzz-full`, `make fuzz-install`,
  documented in `verification/fuzz/README.md`. schemathesis runs against the live
  stack (140 operations, ~3.3k cases). Nightly/local — needs the running stack and
  a freshly provisioned DB (a stale schema yields provisioning-artifact 500s).
- schemathesis is installed via `uv pip install` (venv only), NOT added to
  `[dependency-groups]`, because a `uv lock` would re-resolve protean's `rev=main`
  pin and silently bump it off the committed commit. The deferred `[verification]`
  group (T0.4) lands with a separate lock refresh.
- **Bug found + FIXED here — pagination overflow → 500.** List endpoints
  (`GET /orders`, `/products`, `/reviews`, `/reviews/customer/{id}`) took unbounded
  `page`/`page_size`; a huge `page × page_size` overflowed Postgres `bigint`
  (`offset = (page-1)*page_size`) → `NumericValueOutOfRange` → 500. Fixed with
  FastAPI `Query` bounds (`page` 1..1_000_000, `page_size` 1..100) → 422. Verified
  against the live API (previously-500 cases now 422; normal pagination still 200).
- **Finding investigated — CORRECTED by T2.5.** `GET /reviews/ratings/{id}` 500s
  with `UndefinedColumn: product_rating.counted_reviews`. T2.4 first speculated a
  "Dict projection field gets no column" schema-generation gap; the T2.5
  conformance harness disproved that (a `Dict()` field DOES get a column on a fresh
  table, on postgresql+sqlite, aggregate + projection). Real cause: a **stale
  table** — `protean db setup`/`create_all` creates only MISSING tables and never
  ALTERs an existing one to add a newly-declared column, so `product_rating`
  (created before `counted_reviews` existed) never gained it. A no-auto-migration
  property of `create_all`, not a Dict-type bug. No upstream issue.
- Lower priority (deferred): 148 "undocumented status code" + 70 "schema-compliant
  rejected" findings = the OpenAPI spec under-documents 4xx responses (doc gap, not
  crashes). The "write-then-read via OpenAPI links" idea needs the schema to define
  `links` first; deferred with the doc work.

**T2.5 - Adapter conformance (push upstream)** `[A]` `[nightly]` - DONE
- `verification/conformance/` — 13 declarative persistence behaviors (add/get,
  get-missing→ObjectNotFoundError, filter + gte/in/contains lookups, exclude,
  order_by, limit+offset, count, update, delete, unique-index enforcement, Dict()
  round-trip on an aggregate AND a projection) run across memory / sqlite /
  postgresql and compared. `make conformance` runs all three and prints the
  skip-rate.
- Built ON Protean's OWN adapter-conformance plugin
  (`protean.integrations.pytest.adapter_conformance`: the `--db` option +
  `test_domain`/`db`/`store_config` fixtures + capability markers). Our conftest
  overrides `db_config` (Postgres :15432, temp SQLite file) and `test_domain`
  (registers the tiny `elements.py` aggregates). So the cases are directly
  contributable upstream — which is the "push upstream" intent. Note: Protean's
  generic conformance suite (`protean.testing.get_generic_test_dir()`) ships only
  with source installs, not the wheel we pin.
- **Result: 13/13 on all three adapters, skip-rate 0%** — every behavior here is
  provider-agnostic by contract. Excluded from the normal `pytest verification/`
  CI run via a `pytest_ignore_collect` guard (collected only when `--db` is on the
  CLI), so it never breaks the memory/postgres jobs.
- **Corrected the T2.4 finding.** The Dict()-round-trip cases pass on postgresql +
  sqlite for both an aggregate and a projection, proving a `Dict` field DOES get a
  column on a freshly created table. T2.4's `counted_reviews` 500 was therefore a
  stale-table artifact (`create_all` doesn't ALTER existing tables), not a
  Dict-schema-generation bug. T2.4's docs (fuzz README, TICKETS, capabilities)
  updated in this change.
- Divergence hunters kept for teeth: unique-index enforcement (asserts rejection,
  not the exception type — memory vs SQL differ, relates to #1071) and the Dict
  round-trip. Add more provider-incapable cases with capability markers
  (`native_json`, `native_array`, …) — those auto-skip and show up in the skip-rate.

**T2.6 - Toxiproxy fault injection on a FIXED workload** `[A]` `[nightly]` - DONE
- `verification/resilience/test_toxiproxy_convergence.py`. Toxiproxy sits in front
  of Redis (`make toxiproxy-up` runs the container + creates the `:26379 -> redis`
  proxy). The inventory broker is routed through it just by setting
  `REDIS_URL=redis://127.0.0.1:26379/3` — the domain.toml URI is `${REDIS_URL|...}`,
  so NO src change; Postgres + event store stay direct. A Redis toxic therefore
  stalls exactly the publish/consume steps.
- FIXED scripted workload with a hand-computed end state (init 20 units, reserve 3
  → reserved=3, available=17) — NOT the random Locust load. Driven in-process; the
  engine is drained with `Engine(inventory, test_mode=True).run()`.
- Guarded (passing) check — **latency**: an 80ms latency toxic on the Redis broker
  slows the pipeline but loses nothing — the fixed workload still drains the outbox
  to zero and InventoryLevel converges to reserved=3. Plus a fast durability sanity
  check (the workload's events are in the outbox pending, independent of the broker).
- Partition was ALSO injected during exploration and produced the findings below;
  full re-convergence after a HARD partition is not asserted because it is not
  reliable via an in-process `Engine.run()` drain — it needs the real engine
  process (the T2.3 pattern).
- **Findings (all proteanhq/protean#1055-class) — the async engine does not
  self-heal its broker connection under a partition:**
  1. Without a socket timeout on the broker (`REDIS_URL` needs
     `?socket_connect_timeout=1&socket_timeout=2`) the engine BLOCKS FOREVER on a
     Redis read during a partition instead of failing fast.
  2. After a partition, the broker's `redis_instance` is left `None`; the engine
     never re-establishes it, so post-heal passes crash with `AttributeError`
     until the harness calls `broker._ensure_connection()` itself (which pings and
     reconnects, preserving pool settings — a raw `from_url` drops them and then
     the engine's blocking reads time out).
  3. Messages already delivered-but-unacked when the partition hits can stay stuck
     in the consumer group's pending list; an in-process drain does not reclaim
     them, so the projection converges only partially (e.g. reserved=2 of 3).
  The outbox is durable so nothing is lost — but a real async worker would wedge
  or crash-loop under a broker partition rather than recover on its own. Worth
  surfacing upstream as a resilience default.
- `@pytest.mark.engine` (deselected in CI via `-m "not engine"`, like the saga +
  DLQ tests; #1055) and needs Docker + Toxiproxy + base(async) env. Run:
  `make docker-up && make toxiproxy-up && make toxiproxy-verify`.

---

## Phase 3 - later / optional

**T3.1 - Quarterly mutation audit** `[A]` `[manual]` - DONE (first run: outbox)
- `verification/mutation/README.md` — the audit report + reproduce steps. First run
  targets `protean.utils.outbox.py` (the outbox pattern ShopStream leans on hardest)
  at the pinned commit `c79c497`, in an isolated `git worktree` (dev's protean branch
  untouched), with mutmut 2.5.1 driven against Protean's fast outbox unit tests via
  ShopStream's own venv (no `uv sync` needed).
- **78% mutation score** (228/293 killed). Of the 65 survivors, ~50 are low-value
  (enum/result string constants, default tuning args, index defs) and ~12 are real
  boundary gaps in Protean's unit tests: retry-TIMING boundary (`current_time <
  next_retry_at`, both call sites — VERIFIED by hand), lock-expiry boundary in
  `_is_locked`, query `limit` boundaries (0 / >0 / <=0 across the fetch+claim paths),
  the reconcile-sweep window off-by-one (`max(0, tail - limit + 1)` — recovery, which
  T1.3/#1073 already flagged), and a dropped `target_broker` query filter. The report
  gives a proposed test for each.
- Per the T3.1 decision, findings/tests target the Protean repo but are documented
  here, not committed upstream in this change. No public badge, no gate; quarterly.
- Follow-ups: extend the audit to the state-machine (`Status` field transitions) and
  invariant machinery next quarter. `mutmut results` crashes on the current pony-orm
  (survivors read from `.mutmut-cache` directly) — note for anyone automating it.

**T3.2 - Antithesis (optional)** `[A]`
- Run the real Docker stack under Antithesis for deterministic, reproducible fault
  testing - only if Phases 0-2 have proven their value.
