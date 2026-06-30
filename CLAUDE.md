# ShopStream

E-Commerce platform built on [Protean](https://github.com/proteanhq/protean), a Domain-Driven Design framework for Python.

## Purpose

ShopStream exists primarily to **test and verify Protean** in a realistic, multi-domain application. Treat issues discovered in Protean very seriously — surface them, fix them upstream (in the [Protean repo](https://github.com/proteanhq/protean)), re-test here, and iterate. ShopStream is the proving ground that keeps Protean honest.

## Architecture

Multi-domain CQRS with nine bounded contexts sharing a single FastAPI server:

- **Identity** (`src/identity/`) — Customer accounts, profiles, addresses, tiers
- **Catalogue** (`src/catalogue/`) — Products, variants, categories, pricing
- **Ordering** (`src/ordering/`) — Shopping carts, order lifecycle (event-sourced), checkout
- **Inventory** (`src/inventory/`) — Stock levels, reservations, warehouse management
- **Payments** (`src/payments/`) — Payment processing, refunds, transaction records
- **Fulfillment** (`src/fulfillment/`) — Shipping, delivery tracking, logistics
- **Reviews** (`src/reviews/`) — Product reviews, ratings, moderation, voting, seller replies
- **Notifications** (`src/notifications/`) — Multi-channel notifications (email/SMS/push/Slack), preferences; cross-domain event consumer hub
- **Loyalty** (`src/loyalty/`) — Reward accounts, points, tiers, membership cards (CQRS) + event-sourced promo campaigns; Protean capability showcase

Commands are processed synchronously via FastAPI. Internal events flow asynchronously through the outbox pattern and domain-specific Redis Streams, with Engine workers maintaining read-model projections. Cross-domain events are published to a shared external Redis bus (DB 15) and consumed by `@domain.subscriber` classes that translate raw payloads into internal domain commands (ACL pattern).

### Process Model

| Process | Command | Port | Purpose |
|---------|---------|------|---------|
| Web Server | `make api` | 8000 | Synchronous command processing |
| Identity Engine | `make engine-identity` | — | Async event processing for Identity |
| Catalogue Engine | `make engine-catalogue` | — | Async event processing for Catalogue |
| Ordering Engine | `make engine-ordering` | — | Async event processing for Ordering |
| Inventory Engine | `make engine-inventory` | — | Async event processing for Inventory |
| Payments Engine | `make engine-payments` | — | Async event processing for Payments |
| Fulfillment Engine | `make engine-fulfillment` | — | Async event processing for Fulfillment |
| Reviews Engine | `make engine-reviews` | — | Async event processing for Reviews |
| Notifications Engine | `make engine-notifications` | — | Async event processing for Notifications |
| Loyalty Engine | `make engine-loyalty` | — | Async event processing for Loyalty |
| Observatory | `make observatory` | 9000 | Live message flow dashboard + Prometheus metrics |

### Event Flow

**Internal (within a domain):**
1. HTTP request hits FastAPI → command handler mutates aggregate → raises domain events
2. UoW commit writes aggregate state + outbox records **atomically**
3. HTTP response returns to client
4. Engine's OutboxProcessor picks up pending outbox records → publishes to domain's Redis DB
5. Engine's StreamSubscription reads from Redis → invokes projectors to update read models

**Cross-domain (published events):**
1. Events marked `published=True` are dual-written: one outbox row for the internal broker, one for the external bus (`brokers.global`, Redis DB 15)
2. Engine's external OutboxProcessor publishes to DB 15 with the same stream names
3. Consuming domain's `@domain.subscriber(broker="global", stream="source::aggregate")` receives raw dict payloads
4. Subscriber translates payload into internal domain commands — this is the ACL boundary

### Redis DB Mapping

| DB | Domain |
|----|--------|
| 0 | Identity |
| 1 | Catalogue |
| 2 | Ordering |
| 3 | Inventory |
| 4 | Payments |
| 5 | Fulfillment |
| 6 | Reviews |
| 7 | Notifications |
| 8 | Loyalty |
| 9 | Loyalty cache (`[caches.loyalty]`, PointsLeaderboard projection) |
| 15 | External bus (shared, cross-domain published events) |

## Project Structure

```
src/
├── app.py                    # FastAPI web server (multi-domain middleware)
├── shared/                   # Cross-cutting utilities
│   ├── api/                  # Shared API helpers
│   └── enrichment.py         # Event enrichment utilities
├── identity/                 # Identity bounded context
│   ├── domain.py             # Domain composition root
│   ├── domain.toml           # Config (DB, broker, event store, env overlays)
│   ├── customer/             # Customer aggregate module
│   ├── projections/          # Read models + projectors
│   ├── api/                  # FastAPI routes + Pydantic schemas
│   ├── shared/               # Shared value objects (EmailAddress, PhoneNumber)
│   └── utils/                # DB, logging, exceptions
├── catalogue/                # Catalogue bounded context
│   ├── domain.py
│   ├── domain.toml
│   ├── product/              # Product aggregate module
│   ├── category/             # Category aggregate module
│   ├── projections/          # Read models + projectors
│   ├── api/                  # FastAPI routes + Pydantic schemas
│   ├── shared/               # Shared value objects (SKU, Money)
│   └── utils/
├── ordering/                 # Ordering bounded context
│   ├── domain.py
│   ├── domain.toml
│   ├── cart/                 # ShoppingCart aggregate module (CQRS)
│   ├── order/                # Order aggregate module (event-sourced)
│   ├── projections/          # Read models + projectors
│   ├── api/                  # FastAPI routes + Pydantic schemas
│   └── utils/
├── inventory/                # Inventory bounded context
│   ├── domain.py
│   ├── domain.toml
│   ├── stock/                # Stock aggregate module
│   ├── projections/
│   └── api/
├── payments/                 # Payments bounded context
│   ├── domain.py
│   ├── domain.toml
│   ├── payment/              # Payment aggregate module
│   ├── projections/
│   └── api/
├── fulfillment/              # Fulfillment bounded context
│   ├── domain.py
│   ├── domain.toml
│   ├── fulfillment/          # Fulfillment aggregate module
│   ├── projections/
│   └── api/
├── reviews/                  # Reviews & Ratings bounded context (CQRS)
│   ├── domain.py
│   ├── domain.toml
│   ├── review/               # Review aggregate (Rating VO, HelpfulVote/SellerReply/ReviewImage entities)
│   │   ├── review.py         # Aggregate + state machine (PENDING→PUBLISHED|REJECTED, etc.)
│   │   ├── events.py         # 8 domain events
│   │   └── ...               # submission/editing/moderation/voting/reporting/removal/reply + ordering_subscriber
│   ├── projections/          # 6 read models
│   └── api/                  # 7 REST endpoints (/reviews)
├── notifications/            # Notifications bounded context (CQRS) — event-consumer hub
│   ├── domain.py
│   ├── domain.toml
│   ├── notification/         # Notification aggregate + dispatch handler + 8 ACL subscribers + helpers
│   ├── preference/           # NotificationPreference aggregate + commands
│   ├── channel/              # Email/SMS/Push/Slack ports + fake adapters + get_channel registry
│   ├── templates/            # Per-NotificationType template classes
│   ├── projections/          # 5 read models
│   └── api/                  # REST endpoints (/notifications)
└── loyalty/                  # Loyalty & Rewards bounded context — Protean capability showcase
    ├── domain.py
    ├── domain.toml           # Redis DB 8, cache DB 9, snapshot_threshold=5
    ├── reward/               # RewardAccount (CQRS): aggregate + abstract base + entities + validators,
    │                         #   events, enrollment/points commands, transfer (domain service),
    │                         #   services (application service @use_case), repository (Q/F), ordering_subscriber (pattern B)
    ├── campaign/             # PromoCampaign (event-sourced + fact_events): aggregate, events, upcasters (v1→v2→v3)
    └── projections/          # RewardAccountView (DB) + PointsLeaderboard (cache)

tests/
├── conftest.py               # Auto-marks tests by directory, --env option
├── identity/
├── catalogue/
├── ordering/
├── inventory/
├── payments/
├── fulfillment/
├── reviews/                  # 232 tests (99.4% coverage)
│   ├── domain/               # Pure aggregate behavior (116 tests)
│   ├── application/          # Command handler tests (32 tests)
│   ├── integration/          # API + projection tests (71 tests)
│   └── bdd/                  # BDD scenarios (13 tests)
└── integration/              # Cross-domain event tests
```

## Domain Module Pattern

Each domain follows this structure per aggregate:

```
<aggregate>/
├── <aggregate>.py            # Aggregate root + entities + value objects + enums
├── events.py                 # Domain events (past tense, versioned)
├── <feature>.py              # Commands + command handlers (one file per use case)
└── ...
```

## Key Conventions

### Domain Composition Root
Each domain is a `protean.Domain` instance in `domain.py`. All domain elements register against it via decorators (`@identity.aggregate`, `@identity.command(part_of="Customer")`, etc.).

### API Layer (Anti-Corruption Pattern)
API request/response models (Pydantic `BaseModel` in `api/schemas.py`) are **separate** from Protean commands. The API layer is the external contract; commands are internal domain concepts. Routes in `api/routes.py` translate between them:
```python
@router.post("", status_code=201, response_model=CustomerIdResponse)
async def register_customer(body: RegisterCustomerRequest) -> CustomerIdResponse:
    command = RegisterCustomer(external_id=body.external_id, ...)
    result = current_domain.process(command, asynchronous=False)
    return CustomerIdResponse(customer_id=result)
```

### Multi-Domain Context Middleware
`src/app.py` maps URL prefixes to domains (`/customers` → identity, `/products` → catalogue, `/categories` → catalogue, `/carts` → ordering, `/orders` → ordering, `/inventory` → inventory, `/payments` → payments, `/fulfillments` → fulfillment, `/reviews` → reviews). A middleware pushes the correct `domain_context()` per request, keeping a single unified OpenAPI schema.

### Protean Decorators
- `@<domain>.aggregate` — Aggregate root
- `@<domain>.entity(part_of="<Aggregate>")` — Child entity
- `@<domain>.value_object(part_of="<Aggregate>")` — Value object
- `@<domain>.command(part_of="<Aggregate>")` — Command DTO
- `@<domain>.command_handler(part_of=<Aggregate>)` — Command handler
- `@<domain>.event(part_of="<Aggregate>")` — Domain event
- `@<domain>.event(part_of="<Aggregate>", published=True)` — Published event (dual-written to external bus)
- `@<domain>.projection` — Read model
- `@<domain>.projector(projector_for=<Projection>, aggregates=[<Aggregate>])` — Event projector
- `@<domain>.subscriber(broker="global", stream="source::aggregate")` — Cross-domain event subscriber (ACL)

### Command Processing
Commands are processed via `current_domain.process(command, asynchronous=False)`. Handlers are thin: load aggregate → invoke method → persist via repository.

### Cross-Domain Events
Domains communicate via the external Redis bus (DB 15). Source domains mark events with `published=True`; the outbox dual-writes them to the domain's internal broker and the shared `brokers.global`. Consuming domains define `@domain.subscriber(broker="global", stream="source::aggregate")` classes that receive raw dict payloads and translate them into internal domain commands — this is the anti-corruption layer (ACL) boundary. Subscribers never import typed event classes from other domains.

```python
@reviews.subscriber(broker="global", stream="ordering::order")
class OrderDeliveredSubscriber:
    def __call__(self, payload: dict) -> None:
        event_type = payload["metadata"]["headers"]["type"]
        if "OrderDelivered" not in event_type:
            return
        data = payload["data"]
        # Translate to domain-local side effect...
```

## Environment Configuration

Controlled by `PROTEAN_ENV` and `domain.toml` overlays:

| Environment | DB naming pattern | `event_processing` |
|---|---|---|
| _(unset)_ — dev | `<domain>_local` | sync |
| `test` | `<domain>_test` | sync |
| `memory` | in-memory | sync |
| `production` | `<domain>` | async |

Test and dev use separate databases so tests never destroy dev data. Memory mode uses in-memory adapters (no Docker needed) for fast feedback.

## Common Commands

```bash
make install              # Install dependencies
make dev                  # docker-up + setup-db
make api                  # FastAPI server (port 8000, Scalar docs at /docs)
make observatory          # Observatory dashboard (port 9000, live message flow + Prometheus)
make test                 # All tests (requires Docker infrastructure)
make test-domain          # Pure business logic (no DB)
make test-application     # Command handler tests (with DB)
make test-integration     # Cross-domain outbox/event tests
make test-memory          # All tests with in-memory adapters (no Docker needed)
make test-memory-fast     # Fast memory tests (domain + application, excludes slow)
make test-<domain>        # Per-domain tests (e.g., make test-reviews, make test-ordering)
make test-<domain>-domain # Per-domain domain tests
make test-<domain>-cov    # Per-domain coverage report
make lint                 # Ruff linting
make format               # Ruff formatting
make typecheck            # MyPy type checking
make ir                   # Regenerate IR baselines for all domains
make ir-check             # Check IR staleness for all domains
make ir-diff              # Diff live IR against saved baselines
make domain-check         # Run protean check on all domains
make verify-observatory   # Verify Observatory Timeline + Causation Graph (~66 API checks)
make verify-loyalty       # Verify Loyalty end-to-end (account/points/transfer/campaign/redemption)
```

## Observatory Verification

`scripts/verify-observatory.sh` — End-to-end verification of the Protean Observatory Event Timeline (Epic 6.2) and Causation Graph (Epic 6.3) features against a running ShopStream stack. Seeds test data across all domains (Identity, Catalogue, Inventory, Ordering, Payments, Fulfillment), then validates Timeline API endpoints (stats, event list, pagination, filtering, single detail, correlation chain, aggregate history), Trace API endpoints (recent traces, trace search, enriched causation tree fields), edge cases, parameter validation, and UI smoke checks (Traces tab, D3 causation graph JS). Run after any Protean upgrade that touches the Observatory.

```bash
make verify-observatory              # Full run: seed + ~66 API checks (requires running stack)
make verify-observatory-skip-seed    # Skip seeding, reuse existing data
./scripts/verify-observatory.sh --seed-only  # Seed data only
```

Requires: `make docker-up && make setup-db && make truncate-db`, API server (`make api`), Observatory (`make observatory`), and at least the ordering + identity + inventory engines.

## Load Testing

Locust-based suite in `loadtests/` exercising all bounded contexts through the full CQRS pipeline (HTTP → outbox → Redis Streams → projectors). See `loadtests/README.md` for full documentation.

### Quick Reference

```bash
make loadtest-install         # Install Locust (one-time)
make loadtest                 # Web UI at :8089 (all default scenarios)
make loadtest-mixed           # MixedWorkloadUser only
make loadtest-headless        # CI mode: 50 users, 5/sec, 5 min → results/
make loadtest-stack           # One-command: Docker + API + engines + Observatory + Locust
make loadtest-seed            # Seed baseline data (customers, products, inventory)
make loadtest-clean           # Truncate all data between runs
```

### Scenario Tiers

**Default scenarios** (safe, no expected failures — included in `make loadtest`):
- `IdentityUser`, `CatalogueUser`, `OrderingUser`, `InventoryUser`, `PaymentsUser` — per-domain journeys
- `FulfillmentUser`, `ReviewsUser`, `NotificationsUser` — per-domain journeys
- `SubscriberUser` — happy-path cross-domain subscriber ACL flows
- `MixedWorkloadUser` — realistic mixed traffic across all domains
- `EventFloodUser` — pipeline saturation stress test

**Specialty scenarios** (generate expected failures — run explicitly):
- `CrossDomainUser`, `FlashSaleUser`, `RaceConditionUser` — race conditions and saga timing
- `OrderingSagaUser` — saga vs direct API race
- `FulfillmentTrackingUser` — tracking before shipment (state machine violations)
- `NotificationsCancelUser` — cancel vs process-scheduled race
- `InventoryMaintenanceUser` — global expire-reservations (run with `-u 1`)
- `SpikeUser` — burst traffic (20 req/sec/user)
- Priority lane scenarios — run via `loadtests/scenarios/priority_lanes.py`

### Monitoring

| Dashboard | URL | Shows |
|-----------|-----|-------|
| Locust | :8089 | Request rate, p50/p95/p99 latency, failures |
| Observatory | :9000 | Live message flow, outbox depth, stream health |
| Prometheus | :9000/metrics | Raw metrics for scraping |

### Known API Limitations (affect scenario coverage)

- `POST /fulfillments` doesn't return internal `FulfillmentItem` IDs — the pick endpoint requires item IDs, but `GET /fulfillments/{id}` now exposes them

## Infrastructure

- PostgreSQL (5432) — aggregate storage, outbox tables
- Redis (6379) — message broker (Redis Streams)
- Message DB (5433) — event store
- Docker Compose manages all services: `make docker-up`

## Dependencies

- Python 3.11+ with uv
- Protean (git main) with postgresql, message-db, redis extras
- FastAPI + Uvicorn
- scalar-fastapi (API docs at /docs)
- Ruff (lint/format), MyPy (types), pytest (testing)

### Switching to Local Protean for Development

When testing Protean changes locally, build the wheel manually and install it directly. Do NOT use `uv pip install -e` (hatchling copies files, creating stale snapshots) or `uv lock && uv sync` with `file://` (uv caches wheels by path, not content, so changes are ignored).

**Initial setup (once):**
```bash
# No pyproject.toml changes needed
cd /Users/subhashb/wspace/proteanhq/protean && uv build --wheel
cd /Users/subhashb/wspace/proteanhq/shopstream && uv pip install --reinstall protean/dist/protean-*.whl
```

**After each Protean change:**
```bash
cd /Users/subhashb/wspace/proteanhq/protean && uv build --wheel
cd /Users/subhashb/wspace/proteanhq/shopstream && uv pip install --reinstall /Users/subhashb/wspace/proteanhq/protean/dist/protean-0.15.0rc1-py3-none-any.whl
```

**Running servers:** Use `.venv/bin/protean` directly, NOT `uv run` (which triggers `uv sync` and overwrites the manual install with a stale cached version):
```bash
cd src && ../.venv/bin/protean observatory --domain ordering.domain ...
```
For the API server, `uv run uvicorn` is fine since it doesn't rebuild protean.

**Reverting:** `uv lock && uv sync` restores the git-pinned version. Don't commit pyproject.toml or uv.lock changes.

## Git & PR Rules

- Never merge PRs. Only create them. Leave reviewing, approving, and merging entirely to the user.
- Never add "Co-Authored-By" lines at the end of commit messages.
