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

**T1.1 - Concurrency check: no lost updates (P2)** `[A]` `[gate]`
- On REAL Postgres, multi-process: fire N concurrent commands at one aggregate;
  assert final version == number of successes, failures == N - successes, and a
  counter field == sum of applied deltas.
- Use Inventory `Stock.reserve()` on one SKU.
- Done when: the check passes on Postgres and FAILS if version_retry is disabled.
- Note: must NOT run in memory mode (memory transactions are fake).

**T1.2 - Exactly-one outbox row (P4)** `[A]` `[gate]`
- Extend `tests/integration/test_event_publishing.py`: after a published-event
  command, assert one row per expected (message_id, target_broker), and that a
  forced duplicate insert raises IntegrityError.

**T1.3 - Crash-window check (P21)** `[A]` `[nightly]`
- Kill the process between the DB commit and the event-store append
  (`unit_of_work.py:281`/`:286`); after restart, assert no event-sourced aggregate
  is missing events. (This will likely fail - it is Protean gap G4.)

**T1.4 - Concurrency model with Hypothesis (P2/P4)** `[A]` `[nightly]`
- A Hypothesis state machine driving random valid command sequences against one
  aggregate, checked against a hand-written plain-Python model (not Protean).
- Only worth it with an independent model; do it for Stock and one event-sourced
  aggregate, not all.

**T1.5 - Regression set habit** `[A]` `[gate]`
- Every Protean bug ShopStream finds becomes one permanent, named test under
  `verification/oracles/`. Seed it with the issues already filed (G1-G5, the
  outbox composite-index fix, the ordering finding).

**T1.6 - Generate docs from the IR** `[A]`
- Render `docs/<domain>/catalog.md` from the live domain elements so docs cannot
  claim a feature the code lacks. Add doctest on the value objects (Money, SKU,
  Rating).

---

## Phase 2 - breadth and depth

**T2.1 - Metamorphic checks (P9/P10/P11)** `[B]` `[gate]`
- projection == fold(events); from_events == live; snapshot == replay; sync == async.
- Parameterize over the domain list so new domains are covered automatically.
- Label clearly: these only catch bugs that differ between the two paths.

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
