# Protean Capability Coverage

ShopStream exists to **test and verify Protean** (see `CLAUDE.md`). This document maps every
Protean capability to where it is exercised, so we can tell at a glance whether the proving
ground still covers the framework. The `loyalty` bounded context is a deliberate **showcase
domain** added to exercise capabilities that have no natural home in the other seven contexts.

Legend: ✅ exercised · ⚠️ partial · ⛔ blocked by a Protean bug (xfail) · 🚧 follow-up · N/A intentionally not covered.

## Elements

| Capability | Status | Where |
|---|---|---|
| `@aggregate` (state-based) | ✅ | identity Customer, catalogue Product, loyalty RewardAccount, … |
| `@aggregate(is_event_sourced=True)` + `@apply` | ✅ | ordering Order, payments Payment, inventory InventoryItem, loyalty PromoCampaign |
| `@aggregate(abstract=True)` + inheritance | ✅ | loyalty `Auditable` → RewardAccount |
| `@aggregate(fact_events=True)` | ✅ | loyalty PromoCampaign (`PromoCampaignFactEvent`) |
| `@entity` | ✅ | loyalty MembershipCard, PointsLedgerEntry; OrderItem; … |
| `@value_object` | ✅ | Money, SKU, Rating, Email, … |
| `@command` + `@command_handler` | ✅ | ~94 across domains; loyalty enrollment/points |
| `@event` (delta) | ✅ | widespread |
| `@event` fact events | ✅ | loyalty PromoCampaign |
| `@event(published=True)` | ✅ | cross-domain bus events |
| in-domain `@event_handler` | ✅ | inventory `EventAuditHandler` (+ notifications) |
| `@handle("$any")` wildcard | ✅ | inventory `EventAuditHandler` (sync + direct dispatch; **#1023** fixed on main) |
| `@projection` + `@projector` (DB) | ✅ | ~48; loyalty RewardAccountView |
| `@projection(cache=...)` | ✅ (memory) | loyalty PointsLeaderboard (`cache="loyalty"`) — write via `cache_for().add()`, read via `view_for().get()`. Postgres DB setup blocked by **#1034** (see below); covered by the memory CI job |
| `@query` + `@query_handler` (`@read`) | ✅ | reviews/ordering/fulfillment/identity `*_queries.py` |
| `@subscriber` pattern A (→ command) | ✅ | inventory/ordering/payments/… ACL subscribers |
| `@subscriber` pattern B (direct mutation) | ✅ | loyalty `OrderDeliveredSubscriber` |
| `@repository` (custom, Q/F/lookups) | ✅ | loyalty `RewardAccountRepository` |
| `@domain_service` (cross-aggregate, pre/post) | ✅ | loyalty `TransferPoints` |
| `@application_service` + `@use_case` | ✅ | loyalty `LoyaltyService.transfer_points` |
| `@upcaster` (single step) | ✅ | ordering OrderCreated v1→v2 |
| `@upcaster` (multi-step chain) | ✅ | loyalty CampaignLaunched v1→v2→v3 |
| `@process_manager` (saga) | ⚠️ 🚧 | ordering `OrderCheckoutSaga` (string correlate). A 2nd saga with dict-correlate + compensation + `end` is a follow-up |
| event/command enrichers | ✅ | all domains (`register_command_enricher` / `register_event_enricher`) + `bind_event_context` (payments/reviews) |
| `@database_model` (custom ORM) | 🚧 | follow-up — Postgres-specific, not exercised in memory tests |
| `@email` / `send_email`, `ReadView` element | N/A | notifications uses bespoke channel ports; `view_for()` covers projection reads |

## Fields & validation

| Capability | Status | Where |
|---|---|---|
| String/Text/Integer/Float/Boolean/DateTime/Identifier/List/Dict/ValueObject | ✅ | widespread |
| `Status` field w/ transitions | ✅ | Customer, Order, … |
| `Date` | ✅ | identity Profile, loyalty RewardAccount/PromoCampaign |
| non-Enum `choices` (list) | ✅ | loyalty tier, discount_type, entry_type |
| `Auto(increment=True)` | 🚧 | works in memory, but the generated value is not reflected back onto the instance after `add` (stays `None`); contrived in loyalty — follow-up |
| custom field validators (RegexValidator + custom class, composed) | ✅ | loyalty `member_code` |
| optional field + `validators=` (skipped on `None`) | ✅ | loyalty `referral_code` (**#1025** fixed on main) |
| `@invariant.post` | ✅ | widespread |
| `@invariant.pre` | ✅ | loyalty RewardAccount (`closed_accounts_are_immutable`) |
| `atomic_change` | ✅ | identity `add_address` |
| portable `Index` on projections | ✅ | ordering/fulfillment/reviews (added in PR #8) |

## Event sourcing / messaging / persistence

| Capability | Status | Where |
|---|---|---|
| `@apply`, `from_events`, `_create_new`, `_version` | ✅ | Order/Payment/InventoryItem/PromoCampaign |
| snapshots — `snapshot_threshold` + `create_snapshot` | ✅ | loyalty (`snapshot_threshold=5`) |
| bulk `create_snapshots()` | ✅ | loyalty PromoCampaign (**#1028** fixed on main) |
| command `deadline` + `CommandExpiredError` | ✅ | payments (PR #8) |
| handler `retries`/`backoff`/`retry_exceptions` + `transient_retry` | ✅ | payments (PR #8) |
| `Q` / `F` / lookups (gte/in/…) | ✅ | loyalty `RewardAccountRepository` |
| cache provider (`[caches.*]`) | ✅ | loyalty `[caches.loyalty]` |
| `value_object_from_entity` | ✅ | payments invoice (PR #8) |
| async command processing (`asynchronous=True`) | 🚧 | follow-up |
| multiple providers (sqlite/elasticsearch) | 🚧 | open question / follow-up |
| DLQ deliberate exercise | 🚧 | open question / follow-up |

## Protean bugs surfaced (filed; milestone 0.16.1)

This branch pins Protean to git `main`, which carries all three fixes.

| Issue | Status | Summary |
|---|---|---|
| [#1023](https://github.com/proteanhq/protean/issues/1023) | ✅ fixed on main | `@handle("$any")` event handlers silently skipped under `event_processing="sync"` (`handlers_for` ignored `$any`) |
| [#1025](https://github.com/proteanhq/protean/issues/1025) | ✅ fixed on main | per-field `validators=` ran against `None` on optional fields (AfterValidator omitted empty-value short-circuit) |
| [#1028](https://github.com/proteanhq/protean/issues/1028) | ✅ fixed on main | bulk `create_snapshots()` failed for `fact_events=True` aggregates (`-fact-` streams mistaken for instances) |
| [#1034](https://github.com/proteanhq/protean/issues/1034) | ⛔ open | cache-backed projection breaks SQLAlchemy DB setup (`_create_database_artifacts` doesn't skip cache projections). loyalty is excluded from the Postgres CI job until fixed; it runs in the memory CI job |

Minor DX note (not filed): `repository_for()` gives a confusing `provider=None` error for cache-backed
projections — the working API is `cache_for().add()` / `view_for().get()`.

## Follow-ups (need design or infrastructure)

- **Process manager #2** — a loyalty `RedemptionSaga` exercising dict `correlate`, compensation, and `end`.
- **`database_model`** — custom ORM model (Postgres; not exercised by memory tests).
- **`Auto(increment)`** — a clean home + the id-reflection wart (see above).
- **Infra wiring** — loyalty is wired into `app.py`, the `make test-memory*` targets, and CI
  (`src/loyalty/create_db.sh` + a "Set up loyalty database" step + `--cov=src/loyalty`). Still
  pending (needs a local `loyalty_local` DB, since registering before the DB exists makes the
  `protean-check-staleness` pre-commit hook fail): register loyalty in `.protean/config.toml [domains]`,
  generate `.protean/loyalty/ir.json` via `make ir`, add it to the Makefile IR/`domain-check`/per-domain
  DB test loops, and add a `make engine-loyalty` target.
