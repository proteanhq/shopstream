# ShopStream as Protean's verification surface

This document explains how ShopStream is used to check that Protean works
correctly, and how to grow that into a release gate for Protean.

It is written to be read by anyone. No jargon where plain words work.

---

## 1. What we are trying to do

ShopStream is a real app built on Protean. We want to use it for three things at
once:

1. **Reference app** - clean, readable code people read to learn Protean.
2. **Test surface** - exercise every Protean feature and catch bugs.
3. **Release gate** - before Protean ships a release, run ShopStream against it;
   if a real guarantee broke, block the release.

Most "example apps" only do #1. The goal here is to do all three without letting
#2 and #3 ruin #1.

---

## 2. The one idea that matters: where a test gets its "right answer"

Every test compares what the system did against some "right answer." The value
of a test depends entirely on **where that right answer comes from**. There are
three sources, from strongest to weakest:

| Source of the right answer | How strong | Example |
|---|---|---|
| **A. Independent** - computed by hand, or by a different system (real Postgres), or from an injected fault with a known outcome | Strongest. Catches bugs even when the same wrong code is on both sides. | "One review was approved, so the count must be 1" (computed by hand, not by replaying events). |
| **B. Two Protean paths must agree** | Good, but blind when both paths share the same bug. | "Rebuilding a projection from events must equal the live projection." If both use the same broken math, they agree and the test passes. |
| **C. Protean's own data is the answer** | Weak. Only catches broken structure, not wrong values. | "The causation graph has no dangling links." If the graph is wrong-but-well-formed, this passes. |

**Rule we follow:** the release gate is built only from **A** checks. **B**
checks are useful but we never claim they prove correctness. **C** checks are
cheap sanity checks only.

This rule is what kills two tempting-but-weak ideas: a custom in-memory
"simulator," and a "causation graph oracle" as the centerpiece. Both are mostly
type **C** (they trust Protean's own output), so they cannot be the foundation.

A worked example of a type-A check is in
`verification/oracles/test_p20_projector_idempotency.py`. It found a real bug.

---

## 3. How the repo is organized

Keep the code you read to learn separate from the heavy test machinery.

```
src/                    Reference code. Clean and idiomatic. NO test or
                        fault-injection code here, ever. (Enforce with a
                        CI lint that blocks test imports under src/.)

tests/<domain>/         The teaching tests: domain / application / integration /
  domain/               bdd. This is what a contributor writes and what a
  application/          newcomer reads. The bar to add a feature stays exactly
  integration/          where it is today: write these four, run
  bdd/                  `make test-memory-fast` (under a minute).

docs/<domain>/          Capability docs. Should be GENERATED from the live
                        domain (the IR), so they cannot claim a feature the code
                        does not have. (Today loyalty's docstrings claim a saga
                        and Auto-increment IDs that do not exist - generated docs
                        prevent that.)

verification/           The heavy checks. Separate dependency group so the
  oracles/              normal test run does not need Hypothesis, Toxiproxy, etc.
  metamorphic/          Parameterized over the domain list (the IR) so a new
  contracts/            domain is picked up automatically - the author writes no
  resilience/           check code here.
  conformance/
  capabilities.yaml     Maps each capability to: the file that teaches it, the
                        check that guards it, and the property it must satisfy.
```

`loadtests/` already follows this separation (it lives outside `tests/`). We
extend the same discipline to all the checks.

---

## 4. What must always be true (the properties)

These are the things a Protean app must be able to rely on. The full list is
below; the **8 most important** are marked **(KEY)** - these are the ones whose
failure is most damaging and most likely to slip by unnoticed, so they get
type-A checks on real infrastructure.

| ID | Property (must always hold) | Check source | Runs on |
|---|---|---|---|
| P1 | Aggregate state and its outbox rows are written together or not at all | A | Postgres |
| **P2 (KEY)** | Concurrent writes to one aggregate never lose an update; version retry converges | **A** (hand-written model) | **Postgres, multi-process** |
| P3 | Version-retry is bounded (never spins or runs past a deadline) | A | any |
| **P4 (KEY)** | Exactly one outbox row per (message_id, target_broker) | **A** (DB rejects duplicate) | Postgres |
| P5 | Outbox rows advance through states correctly; published exactly once per broker | A | Postgres |
| P6 | Every event reaches each handler at least once | A | Docker |
| **P20 (KEY, was missing)** | **Delivering one event N times leaves the read model the same as delivering it once (idempotent projectors)** | **A** (count by hand, no duplicate) | **real Redis, forced redelivery** |
| **P9 (KEY)** | After things settle, projection equals the fold of its events | B | any |
| P7 | A projector applies one aggregate's events in version order | A/B | known gap (#830) |
| P8 | Read models never go backwards | B | any |
| **P10/P11 (KEY)** | Rebuilding an aggregate from events equals its live state; snapshot load equals full replay | B | any |
| **P21 (KEY, was missing)** | **Aggregate+outbox and the event store stay consistent if the process crashes between them** (today the event-store append happens AFTER the DB commit, outside the transaction) | **A** (kill in the window) | Docker |
| P12 | A fact event carries the complete current aggregate state | B | any |
| P13 | Old-version events upcast and replay correctly | A | any |
| **P14/P15 (KEY)** | IR diff flags breaking changes correctly; cross-domain event payloads match what subscribers read | A-ish (see governance) | CI |
| P16 (KEY) | Every saga reaches a terminal state; failures trigger compensation | A | Docker |
| P17 | An expired command is skipped, never executed | A | any |
| P18 | A poison message goes to the DLQ after N retries and can be replayed | A | Docker |
| P19 | An aggregate never persists in a state that breaks its own invariants | A | any |

---

## 5. The checks we will build (ranked)

We are NOT building 11 different test frameworks. We build a small set, in order
of value. Each is tagged with where its right answer comes from (A/B/C).

| Order | Check | Source | Catches | Notes |
|---|---|---|---|---|
| 1 | **`process_and_wait(command)`** helper, shipped in Protean | enabler | flaky async tests | Fire a command, block until the outbox drains and projectors catch up, return the response + the events that fired. Everything async needs this. Build it first. |
| 2 | **Contract gate** | A/C | broken upgrades, changed event payloads | IR diff as a real CI failure (today it ends in `\|\| true` and never fails). Plus saved snapshots of every cross-domain event payload. |
| 3 | **Same-event-twice checks (P20)** | **A** | non-idempotent projectors | The single highest-value new check. Prototype already exists and found a bug. |
| 4 | **Concurrency checks (P2, P4)** with a hand-written model, on real Postgres | **A** | lost updates, duplicate publishes | The one real "find an unknown bug" investment. Must run on Postgres, not memory. |
| 5 | **Crash-window check (P21)** | **A** | event-store / outbox divergence | Kill the process between DB commit and event-store append. |
| 6 | **Metamorphic checks** | B | pipeline bugs that differ between two paths | projection==fold, snapshot==replay, sync==async. Label honestly: these only catch bugs that show up differently on the two paths. |
| 7 | **Regression set** | A | bugs coming back | Every Protean bug we find becomes one permanent, named test here. This is the part that keeps paying off. |
| 8 | **Adapter check (conformance)** | A | Postgres vs memory differences | Same behavior run on several adapters, compared. Keep small; push upstream into Protean since it is about Protean's adapters, not ShopStream's domains. Track how many cases are skipped. |
| 9 | schemathesis API fuzzing | A | crashes/contract breaks at the HTTP edge | One command against the OpenAPI spec. Quick win. |
| 10 | Living docs: BDD features + doctest on value objects | A | docs that lie | These double as documentation. |

---

## 6. What we will NOT build (and why)

- **A custom in-memory simulator ("VOPR").** It would test the in-memory adapter,
  which nobody runs in production, and the memory adapter is not faithful
  (transactions are fake, no real serialization, Python-side sorting). High cost,
  tests the wrong thing. If we ever need full deterministic simulation, run the
  real Docker stack under Antithesis instead.
- **A "causation graph" as the main check.** It trusts Protean's own metadata, so
  it can only catch broken structure, not wrong values. Keep a tiny version (no
  dangling links, no cycles) and nothing more.
- **A public mutation-score badge.** Mutation testing is a useful quarterly audit,
  but a public number pushes people to write tests that game the number. Run it
  occasionally, read the report, never gate on it.
- **Running the random load test as the fault-injection workload.** Random load +
  random faults = a test that fails intermittently for unclear reasons, which
  people learn to ignore. Fault injection needs a small, fixed workload with a
  known correct end state.
- **A giant "every property x every check x every adapter" matrix as a hard gate.**
  It will never be fully green and a gate that is never green gets bypassed.

---

## 7. How the release gate works (so it does not rot)

A gate is only trusted if it is small, fast, and almost never wrong by mistake.

1. **Only type-A checks block a release.** Everything else runs nightly and
   reports, but does not block.
2. **Tell apart "a guarantee broke" from "a detail changed."** If Protean
   legitimately changes an event's shape, that should auto-open a PR to update
   the saved snapshot, NOT block the release. Only a broken guarantee blocks. If
   you cannot tell these apart automatically, people will bypass the gate.
3. **Quarantine flaky checks immediately.** A check that fails intermittently is
   auto-moved out of the blocking set with a tracking issue and a 2-week
   fix-or-delete deadline. The blocking set has a zero-flake bar.
4. **The contribution bar does not rise.** Adding a feature still means: the four
   test tiers + a BDD feature. The heavy checks pick up the new domain
   automatically. New contributors never touch `verification/`.

---

## 8. Build order

- **Phase 0 (first):** `process_and_wait`; contract gate (remove `|| true`); the
  P20 same-event-twice check (done - prototype exists); fix loyalty's false
  docstrings; set up the `verification/` tree + the `src/` lint.
- **Phase 1:** P2/P4 concurrency checks on real Postgres; P21 crash window; the
  regression-set habit; generate docs from the IR.
- **Phase 2:** adapter conformance (upstream), schemathesis, Toxiproxy on a fixed
  workload, quarterly mutation audit.
- **Later, only if earned:** Antithesis on the real Docker stack.

---

## 9. Protean gaps found while writing this

These are real issues in Protean itself, found during this analysis and filed
upstream. They are exactly the kind of thing this surface exists to catch.

| # | Gap | Issue | Why it matters |
|---|---|---|---|
| G1 | **No `Decimal` field type** - money is `Float` everywhere | [#1038](https://github.com/proteanhq/protean/issues/1038) | Floating-point money drifts (0.1 + 0.2). The convergence check (P9) can't see it because both write and read paths use the same float math. |
| G2 | **No consume-side idempotency** - projectors get events at least once with no dedup | [#1042](https://github.com/proteanhq/protean/issues/1042) | A redelivered event double-counts. This is the most likely bug to ship unnoticed. The P20 check exists to catch it. |
| G3 | **Datetime payloads serialized with `str()`**, not `.isoformat()`, and not normalized to UTC | [#1039](https://github.com/proteanhq/protean/issues/1039) | Naive datetimes silently lose timezone; payload and metadata use different formats. |
| G4 | **Event-store append happens after the DB commit, outside the transaction** (`unit_of_work.py:281` commit, `:286` append) | [#1040](https://github.com/proteanhq/protean/issues/1040) | A crash in between leaves the aggregate and outbox committed but the event missing from the store - corrupts event-sourced replay. |
| G5 | **`target_broker` is nullable with no NOT NULL constraint** | [#1041](https://github.com/proteanhq/protean/issues/1041) | The (message_id, target_broker) unique index relies on it being set; a NULL row silently bypasses the uniqueness guarantee. |
