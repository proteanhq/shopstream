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

**T1.6 - Generate docs from the IR** `[A]`
- Render `docs/<domain>/catalog.md` from the live domain elements so docs cannot
  claim a feature the code lacks. Add doctest on the value objects (Money, SKU,
  Rating).

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
- **sync == async — DEFERRED to `[nightly]`/local.** Both CI envs (memory, test)
  are `event_processing="sync"`; a genuine sync-vs-async comparison needs the live
  engine + Redis, which is unreliable in CI (proteanhq/protean#1055, the same
  reason `test_dlq` is `@pytest.mark.engine` local-only). The `sync`/`async` test-
  body equivalence is already covered structurally by `process_and_wait`/`drain`
  (T0.1). A dedicated metamorphic sync==async harness belongs in the nightly engine
  lane; tracked, not built here.

**T2.2 - Cross-domain payload contracts (P15)** `[A]` `[gate]`
- Snapshot every `published=True` event's external payload; feed each saved
  payload through the real subscriber `__call__` and assert it translates with no
  KeyError. Catches a producer dropping/renaming a field a subscriber reads.

**T2.3 - Saga liveness + compensation (P16)** `[A]` `[nightly]`
- Force a payment failure x3 in the checkout saga; assert the order ends CANCELLED
  and the inventory reservation is released. Add a stuck-saga detector.

**T2.4 - schemathesis API fuzzing** `[A]` `[nightly]`
- `schemathesis run http://localhost:8000/openapi.json` with OpenAPI links for
  write-then-read flows. Quick to add, finds shallow contract/500 bugs.

**T2.5 - Adapter conformance (push upstream)** `[A]` `[nightly]`
- A small set of declarative behavior cases run across memory/postgres/sqlite and
  compared. Belongs in Protean (it is about Protean's adapters). Track skip-rate.

**T2.6 - Toxiproxy fault injection on a FIXED workload** `[A]` `[nightly]`
- Inject Redis/Postgres latency and partition during a small scripted workload
  with a known end state; assert the outbox drains to zero and projections
  converge. Do NOT use the random Locust load as the workload.

---

## Phase 3 - later / optional

**T3.1 - Quarterly mutation audit** `[A]` `[manual]`
- Run mutmut/cosmic-ray on Protean core; read the report; write targeted tests for
  surviving mutants in invariant/state-machine/outbox code. No public badge, no gate.

**T3.2 - Antithesis (optional)** `[A]`
- Run the real Docker stack under Antithesis for deterministic, reproducible fault
  testing - only if Phases 0-2 have proven their value.
