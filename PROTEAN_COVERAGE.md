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
| `@event(published=True)` | ✅ | cross-domain bus events; loyalty **produces** `PointsEarned`/`PointsRedeemed`/`TierUpgraded`/`RewardAccountEnrolled` (dual-write asserted in `tests/integration/test_event_publishing.py`) → Notifications reacts |
| in-domain `@event_handler` | ✅ | inventory `EventAuditHandler` (+ notifications) |
| `@handle("$any")` wildcard | ✅ | inventory `EventAuditHandler` (sync + direct dispatch; **#1023** fixed on main) |
| `@projection` + `@projector` (DB) | ✅ | ~48; loyalty RewardAccountView, CampaignCatalog (projects the event-sourced PromoCampaign) |
| `@projection(cache=...)` | ✅ | loyalty PointsLeaderboard (`cache="loyalty"`) — write via `cache_for().add()`, read via `view_for().get()` (runs on Postgres + memory; **#1034** fixed on main) |
| `@query` + `@query_handler` (`@read`) | ✅ | reviews/ordering/fulfillment/identity + loyalty `*_queries.py` (incl. `campaign_catalog_queries.py` filtered/ordered list) |
| cross-aggregate read in a write handler | ✅ | loyalty `PointsHandler.earn` reads `CampaignCatalog` (active points-multiplier) via `campaign/multiplier.py` |
| `@subscriber` pattern A (→ command) | ✅ | inventory/ordering/payments/… ACL subscribers |
| `@subscriber` pattern B (direct mutation) | ✅ | loyalty `OrderDeliveredSubscriber`, `ReviewApprovedSubscriber` (review bonus), `PaymentRefundedSubscriber` (refund clawback) |
| `@repository` (custom, Q/F/lookups) | ✅ | loyalty `RewardAccountRepository` |
| `@domain_service` (cross-aggregate, pre/post) | ✅ | loyalty `TransferPoints` |
| `@application_service` + `@use_case` | ✅ | loyalty `LoyaltyService.transfer_points` |
| `@upcaster` (single step) | ✅ | ordering OrderCreated v1→v2 |
| `@upcaster` (multi-step chain) | ✅ | loyalty CampaignLaunched v1→v2→v3 |
| `@process_manager` (saga, string correlate) | ✅ | ordering `OrderCheckoutSaga` |
| `@process_manager` (dict correlate + compensation + `end`) | ✅ | loyalty `RedemptionSaga` — reserve → issue → complete, compensating (refund) on voucher failure; `correlate={"redemption_id": ...}`, `end=True` + `mark_as_complete()` |
| event/command enrichers | ✅ | all domains (`register_command_enricher` / `register_event_enricher`) + `bind_event_context` (payments/reviews) |
| `@database_model` (custom ORM) | ✅ | loyalty `RewardAccountViewPostgresModel` (`projections/reward_account_view_model.py`) — hand-written SQLAlchemy model overriding `RewardAccountView`'s columns (`Text` + indexed `customer_id`), registered `database="postgresql"` so Postgres uses it and the memory provider falls back to the auto-generated model; both paths asserted in `tests/loyalty/integration/test_custom_database_model.py` |
| `@email` / `send_email`, `ReadView` element | N/A | notifications uses bespoke channel ports; `view_for()` covers projection reads |

## Fields & validation

| Capability | Status | Where |
|---|---|---|
| String/Text/Integer/Float/Boolean/DateTime/Identifier/List/Dict/ValueObject | ✅ | widespread |
| `Status` field w/ transitions | ✅ | Customer, Order, … |
| `Date` | ✅ | identity Profile, loyalty RewardAccount/PromoCampaign |
| `Date` on a **command/event** payload | ✅ | loyalty `LaunchCampaign.starts_on/ends_on` — campaign date windows flow through end-to-end (**#1046** fixed on main) |
| non-Enum `choices` (list) | ✅ | loyalty tier, discount_type, entry_type |
| `Auto(increment=True)` | 🚧 | [proteanhq/protean#1056](https://github.com/proteanhq/protean/issues/1056) is fixed on main: `repository.add()` now reflects the generated value back onto the aggregate. ShopStream has no `increment=True` usage yet; the follow-up is a loyalty exerciser + regression test |
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
| async command processing (`asynchronous=True`) | ✅ | loyalty `POST /loyalty/accounts/{id}/earn-async` (202; engine drains the command queue) |
| multiple database providers in one domain | ✅ | loyalty runs **two** providers: default PostgreSQL + a `[databases.reporting]` **SQLite** store backing `CampaignCatalog` (`@loyalty.projection(provider="reporting")`). SQLite is embedded so both CI jobs exercise it (Postgres job = real Postgres + real SQLite; memory job = both in-memory). Routing + round-trip asserted in `tests/loyalty/integration/test_second_provider.py` |
| DLQ deliberate exercise + replay | ✅ | loyalty `PoisonPill` failing handler → `tests/loyalty/integration/test_dlq.py` drives `Engine(test_mode)` → message lands in `loyalty::poison_pill:dlq`, then `broker.dlq_replay` (Redis-only, `@pytest.mark.engine`; **runs locally only** — the engine is unreliable in CI, filed as [proteanhq/protean#1055](https://github.com/proteanhq/protean/issues/1055); CI deselects via `-m "not engine"`) |
| temporal / point-in-time (as-of) event-store queries | 🚧 | claimed in `ordering`/`inventory` aggregate docstrings; no as-of replay query API is actually exercised (the `as_of` uses in cart/stock/notifications are datetime business logic). The follow-up is a real point-in-time read |

## Server & async runtime

| Capability | Status | Where |
|---|---|---|
| the Engine (per-domain workers) | ✅ | `make engine-<domain>` (OutboxProcessor + StreamSubscriptions); scaled variants `engine-<domain>-scaled` |
| stream subscriptions (outbox-backed) | ✅ | `[server] default_subscription_type = "stream"` in every domain.toml |
| the outbox (atomic write + dual-write) | ✅ | `[outbox]` in every domain.toml; exactly-once guarded by `verification/oracles/test_outbox_exactly_once.py` |
| stream categories | ✅ | `stream_categories=[...]` on `OrderCheckoutSaga` and `RedemptionSaga` |
| priority lanes (primary vs backfill) | ✅ | `[server.priority_lanes]` in identity/catalogue/ordering/inventory/payments; `docs/priority-lanes.md`; `loadtests/scenarios/priority_lanes.py`; `scripts/migration_demo.py` |
| version-retry (OCC auto-retry) | ✅ | `[server.version_retry]` in ordering/payments; guarded by `verification/oracles/test_no_lost_updates.py` (multi-process Postgres) |
| external Redis bus (shared, DB 15) | ✅ | `[brokers.global]` per domain.toml; `[outbox] external_brokers = ["global"]` |
| `sequential_by` partitioned/ordered consumer | 🚧 | absent. ShopStream reproduces per-stream out-of-order delivery under concurrent load (`PROTEAN_v0.16_NOTES.md` item 9) and does not yet adopt `sequential_by` (Protean #830, epic #826). Highest-value gap |
| circuit breaker | 🚧 | absent. `transient_retry` (payments) and `version_retry` (ordering/payments) are the only resilience knobs wired. The follow-up is a breaker exerciser |
| stream retention / trimming (MAXLEN) | 🚧 | absent. No stream-trim configuration on any broker; streams grow unbounded in the demo. The follow-up is a retention exerciser |
| custom subscription profiles | 🚧 | absent. Only `default_subscription_type` and priority-lane routing are configured; no per-subscription profile. The follow-up is a profile exerciser |
| CloudEvents envelope format | 🚧 | absent. Cross-domain events use Protean's native metadata-headers dict payload; the CloudEvents serialization is not exercised. The follow-up is a CloudEvents exerciser |

## Observability & diagnostics

| Capability | Status | Where |
|---|---|---|
| OpenTelemetry (OTLP HTTP spans) | ⚠️ | wired via `instrument_app(...)` in `src/app.py`; `[production.telemetry]` production overlay; no dedicated assertion found |
| structured logging + correlation processor | ⚠️ | wired via `configure_logging(extra_processors=[protean_correlation_processor])`; `logging.toml`; no dedicated assertion found |
| correlation & causation identity | ✅ | `src/shared/enrichment.py`; verified E2E by `scripts/verify-observatory.sh` (correlation chain + causation tree) |
| Observatory (timeline, causation graph, domain visualizer) | ✅ | `make observatory`; `scripts/verify-observatory.sh` (~66 checks); `scripts/verify-domain-visualizer.sh` |
| message tracing | ✅ | Observatory Trace API (recent, search, causation tree) checked in `scripts/verify-observatory.sh` |
| Prometheus metrics | ⚠️ | Observatory `/metrics` (`protean_outbox_messages`, `protean_stream_messages`, `protean_stream_processed_total`); scraped in load tests; no unit assertion |
| `protean check` (typed diagnostics) | ✅ | `make domain-check` / `domain-check-<domain>` |
| the IR + baselines + backward-compat gate | ✅ | `.protean/<domain>/ir.json`; `make ir`/`ir-check`/`ir-diff`; `verification/contracts/test_ir_gate.py` + `make ir-gate` |
| docs generated from the IR | ✅ | `make docs-generate`; committed `docs/<domain>/catalog.md`; `make docs-check` CI gate |
| fitness functions | 🚧 | absent. Architectural discipline is enforced through `make check-src-clean` and the IR gate; no Protean fitness-function element is used. The follow-up is a fitness-function exerciser |
| `protean verify` subcommand | 🚧 | absent. The `make verify-*` targets are ShopStream shell scripts; the follow-up is to wire the real `protean verify` (init + check + tests) in |

## Protean bugs surfaced (filed; milestone 0.16.1)

This branch pins Protean to git `main`. #1023/#1025/#1028/#1034/#1046 are fixed there, and the
pin was bumped to Protean main `c79c497`, which also lands #1048 (sync PM cascade) and #1056
(Auto-increment) — the loyalty `RedemptionSaga` now cascades to completion synchronously and its
completion tests are permanent guards (no longer `xfail`).

| Issue | Status | Summary |
|---|---|---|
| [#1023](https://github.com/proteanhq/protean/issues/1023) | ✅ fixed on main | `@handle("$any")` event handlers silently skipped under `event_processing="sync"` (`handlers_for` ignored `$any`) |
| [#1025](https://github.com/proteanhq/protean/issues/1025) | ✅ fixed on main | per-field `validators=` ran against `None` on optional fields (AfterValidator omitted empty-value short-circuit) |
| [#1028](https://github.com/proteanhq/protean/issues/1028) | ✅ fixed on main | bulk `create_snapshots()` failed for `fact_events=True` aggregates (`-fact-` streams mistaken for instances) |
| [#1034](https://github.com/proteanhq/protean/issues/1034) | ✅ fixed on main | cache-backed projection broke SQLAlchemy DB setup (`_create_database_artifacts` didn't skip cache projections); loyalty now runs in the Postgres CI job too |
| [#1046](https://github.com/proteanhq/protean/issues/1046) | ✅ fixed on main | a `Date` field on a command/event broke the message checksum (`ResolvedField.as_dict` had no `date` branch → `json.dumps` raised); campaign date windows now work end-to-end |
| [#1048](https://github.com/proteanhq/protean/issues/1048) | ✅ fixed on main | multi-step process managers now cascade under `event_processing="sync"`; loyalty `RedemptionSaga` runs to a terminal state synchronously (completion/compensation tests are guards) |
| [#1055](https://github.com/proteanhq/protean/issues/1055) | 🐞 filed (0.17.0) | `Engine(test_mode=True).run()` against a Redis broker is unreliable in CI — the engine's async poll loops drop their (sync) Redis connections mid-read (`Connection closed by server` → `redis_instance` becomes `None`), so the async pipeline never completes. Reproduces only in CI, not locally. The loyalty DLQ test (`@pytest.mark.engine`) runs **locally only**; **revisit when #1055 is fixed** — then re-add an engine CI job (deselected today via `-m "not engine"`) |
| [#1056](https://github.com/proteanhq/protean/issues/1056) | ✅ fixed on main | `repository.add()` now reflects an `Auto(increment=True)` generated value back onto the aggregate (the in-memory provider reflects it; relational adapters assign it). ShopStream has no `increment=True` usage to exercise it |

Minor DX note (not filed): `repository_for()` gives a confusing `provider=None` error for cache-backed
projections — the working API is `cache_for().add()` / `view_for().get()`.

Process-manager note ([#1048](https://github.com/proteanhq/protean/issues/1048), fixed on main):
multi-step PMs now cascade under `event_processing="sync"` — the start transition is persisted
before the next step re-enters, so the PM loads its own in-flight instance, and a nested event's
projector runs after the originating event's. The `RedemptionSaga` runs reserve → issue → complete
(or compensates on voucher failure) in a single synchronous pass; its forward + compensation logic
is covered by `given()` unit tests and by end-to-end completion tests (now permanent guards, not
`xfail`). The `RedemptionView` projector still tolerates redelivery idempotently.

## Follow-ups (need design or infrastructure)

**Coverage-gap backlog** (the 🚧 rows in the tables above, features that still need a ShopStream example, mapped 2026-08-16): temporal queries, `sequential_by` partitioned consumer, circuit breaker, stream retention/trimming, custom subscription profiles, CloudEvents envelope, fitness functions, `protean verify`, plus `Auto(increment=True)`.

- **`Auto(increment)`**: a loyalty exerciser + regression test (see the table above; the id-reflection wart is fixed on main via #1056).
- **Infra wiring — done.** loyalty is fully wired: `app.py`, `.protean/config.toml [domains]`,
  `.protean/loyalty/ir.json` baseline, CI (Postgres + memory jobs, `create_db.sh`, `--cov=src/loyalty`),
  the Makefile (`test`/`test-domain`/`test-application`/`test-memory*`/per-domain `test-loyalty*`,
  IR/`domain-check`/`schemas`/`docs-generate` loops, `engine-loyalty`, `domain-check-loyalty`), and a
  `engine-loyalty` docker-compose service.
