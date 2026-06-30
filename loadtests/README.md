# Load Testing

Locust-based load testing suite for ShopStream. Simulates realistic e-commerce traffic across all nine bounded contexts (Identity, Catalogue, Ordering, Inventory, Payments, Fulfillment, Reviews, Notifications, Loyalty), exercising the full CQRS event pipeline — from HTTP command processing through outbox persistence, Redis Streams publishing, and projector consumption.

Includes targeted race condition scenarios based on the domain specification: concurrent checkout, flash sale stampede, cancel-during-payment, and concurrent order modification. Also includes subscriber ACL flow testing, saga-driven process manager journeys, and priority lane scenarios for migration vs production traffic.

## Table of Contents

- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Scenarios](#scenarios)
  - [Identity Domain](#identity-domain)
  - [Catalogue Domain](#catalogue-domain)
  - [Ordering Domain](#ordering-domain)
  - [Inventory Domain](#inventory-domain)
  - [Payments Domain](#payments-domain)
  - [Fulfillment Domain](#fulfillment-domain)
  - [Reviews Domain](#reviews-domain)
  - [Notifications Domain](#notifications-domain)
  - [Cross-Domain & Race Conditions](#cross-domain--race-conditions)
  - [Subscriber ACL Flows](#subscriber-acl-flows)
  - [Saga-Driven Journeys](#saga-driven-journeys)
  - [Mixed Workload](#mixed-workload)
  - [Stress & Spike](#stress--spike)
  - [Priority Lanes](#priority-lanes)
- [User Classes](#user-classes)
- [Test Profiles](#test-profiles)
- [Running Tests](#running-tests)
  - [Manual Setup](#manual-setup)
  - [Automated Stack](#automated-stack)
  - [Headless / CI](#headless--ci)
- [Monitoring During Tests](#monitoring-during-tests)
- [Data Generators](#data-generators)
- [Project Structure](#project-structure)
- [Extending Scenarios](#extending-scenarios)
- [Known API Limitations](#known-api-limitations)
- [Troubleshooting](#troubleshooting)

## Architecture

During a load test, the following processes run simultaneously:

```
┌─────────────────────┐     HTTP      ┌──────────────────────┐
│  Locust (:8089)     │──────────────▶│  FastAPI API (:8000)  │
│                     │  commands     │                      │
│  Simulated users    │               │  /customers/*        │
│  generate traffic   │               │  /products/*         │
│  across 8 domains   │               │  /orders/*           │
│                     │               │  /inventory/*        │
│                     │               │  /payments/*         │
│                     │               │  /fulfillments/*     │
│                     │               │  /reviews/*          │
│                     │               │  /notifications/*    │
└─────────────────────┘               └──────────┬───────────┘
                                                 │ atomic writes
                                                 ▼
┌─────────────────────┐               ┌──────────────────────┐
│  Observatory (:9000)│               │  PostgreSQL          │
│                     │◀ ─ ─ scrape ─ │  8 domain databases  │
│  Live dashboard     │               │  Outbox tables       │
│  Prometheus /metrics│               └──────────┬───────────┘
└─────────────────────┘                          │ drain
                                                 ▼
                                      ┌──────────────────────┐
                                      │  Engine Workers       │
                                      │  (8 domains)          │
                                      │  OutboxProcessor →    │
                                      │  Redis Streams →      │
                                      │  Projectors           │
                                      └──────────────────────┘
```

Each HTTP request creates an aggregate and raises domain events. The events are written atomically to the outbox table alongside the aggregate state. Engine workers drain the outbox, publish to Redis Streams, and projectors update read models. The load test stresses every layer of this pipeline.

## Prerequisites

- ShopStream dependencies installed (`make install`)
- Docker running (for PostgreSQL, Redis, Message DB)
- Load test dependencies:

```bash
make loadtest-install
```

This installs Locust into an optional dependency group.

## Quick Start

```bash
# Terminal 1: Start the full backend in Docker
make docker-dev

# Terminal 2: Start Observatory for monitoring
make observatory

# Terminal 3: Start Locust
make loadtest
```

Open **http://localhost:8089** in your browser. Select the user class (default: all), set user count and spawn rate, and click Start.

Or use the one-command automated stack:

```bash
make loadtest-stack           # Default: 1 engine per domain
make loadtest-stack-scaled    # Scaled: 3+2+2+2+2 engines across domains
```

## Scenarios

All scenarios use Locust's `SequentialTaskSet` — steps execute in strict order, and each step depends on the previous one succeeding. If any step fails, `self.interrupt()` aborts the remaining steps and the user restarts a fresh journey.

### Identity Domain

**`NewCustomerJourney`** — The most common user flow. Generates **5 domain events** + reads projections.

| Step | Endpoint | Event Raised |
|------|----------|-------------|
| 1. Register | `POST /customers` | `CustomerRegistered` |
| 2. Update profile | `PUT /customers/{id}/profile` | `ProfileUpdated` |
| 3. Add first address | `POST /customers/{id}/addresses` | `AddressAdded` |
| 4. Add second address | `POST /customers/{id}/addresses` | `AddressAdded` |
| 5. Upgrade tier | `PUT /customers/{id}/tier` | `TierUpgraded` |

**`AccountLifecycleJourney`** — Full account state machine. Generates **4 domain events**.

| Step | Endpoint | State Transition |
|------|----------|-----------------|
| 1. Register | `POST /customers` | → Active |
| 2. Suspend | `PUT /customers/{id}/suspend` | Active → Suspended |
| 3. Reactivate | `PUT /customers/{id}/reactivate` | Suspended → Active |
| 4. Close | `PUT /customers/{id}/close` | Active → Closed |

**`TierProgressionJourney`** — Full tier ladder. Generates **4 domain events** (STANDARD → SILVER → GOLD → PLATINUM).

### Catalogue Domain

**`ProductCatalogBuilder`** — Seller building a product listing. Generates **6 domain events** (Create → 2 Variants → 2 Images → Activate) + reads projections.

**`ProductLifecycleJourney`** — Full product state machine. Generates **5 domain events** (Draft → Active → Discontinued → Archived).

**`CategoryHierarchyBuilder`** — 3-level category tree with mutations. Generates **6 domain events** + reads projections.

### Ordering Domain

**`CartLifecycleJourney`** — Cart browsing and abandonment. Generates **5+ events** (Create → Add Items ×3 → Get Cart → Abandon).

**`OrderFullLifecycleJourney`** — Happy path order lifecycle. Generates **8 events** (Create → Confirm → Payment Pending → Payment Success → Processing → Ship → Deliver → Complete) + reads order detail and timeline projections.

**`CartToCheckoutJourney`** — Cart-to-order conversion. The most common purchase path.

**`OrderCancellationJourney`** — Cancel during payment + refund path. Tests compensation logic.

**`OrderReturnJourney`** — Full return flow (Create → ... → Deliver → Request Return → Approve → Record Return).

**`OrderCheckoutSagaJourney`** ⚠️ — **Specialty scenario** (excluded from defaults). Races the OrderCheckoutSaga process manager against direct API calls. Generates expected `RecordPaymentHandler` failures. Run via `OrderingSagaUser`.

### Inventory Domain

**`StockInitAndReceiveJourney`** — Warehouse setup: Create Warehouse → Initialize Stock → Receive → Adjust → Stock Check.

**`ReservationLifecycleJourney`** — Order-driven reservation: Init Stock → Reserve.

**`ReservationReleaseJourney`** — Cancelled order releasing stock: Init → Reserve → Release.

**`DamageWriteOffJourney`** — Damage reporting: Init → Mark Damaged → Write Off.

**`ReturnToStockJourney`** — Return processing: Init → Return to Stock.

**`WarehouseManagementJourney`** — Admin operations: Create → Update → Add Zones → Deactivate.

**`ExpireReservationsJourney`** ⚠️ — **Specialty scenario** (excluded from defaults). Global maintenance endpoint that expires reservations. Run with a single user (`-u 1`) via `InventoryMaintenanceUser` to avoid duplicate release failures.

### Payments Domain

**`PaymentSuccessJourney`** — Happy path: Initiate → Webhook Success.

**`PaymentFailureRetryJourney`** — Retry logic: Initiate → Webhook Failure → Retry → Webhook Success.

**`PaymentRefundJourney`** — Refund flow: Initiate → Success → Refund Request → Refund Webhook.

**`InvoiceJourney`** — Invoice lifecycle: Generate → Void.

### Fulfillment Domain

**`FulfillmentCreationJourney`** — Create → Assign Picker → Get Tracking projection.

**`FulfillmentCancellationJourney`** — Create → Assign Picker → Cancel (during picking phase).

**`FulfillmentPickerCancelJourney`** — Create (single item) → Assign Picker → Cancel during picking (operational issues).

**`FulfillmentTrackingWebhookJourney`** ⚠️ — **Specialty scenario** (excluded from defaults). Sends tracking webhooks to non-shipped fulfillments, generating expected `TrackingHandler` state machine violations. Run via `FulfillmentTrackingUser`.

### Reviews Domain

**`ReviewSubmitAndModerateJourney`** — Submit → Approve → Verify Published + reads 3 projections (ReviewDetail, ProductRating, ProductReviews, CustomerReviews).

**`ReviewVotingJourney`** — Submit → Approve → Vote Helpful → Verify vote count.

**`ReviewEditAndResubmitJourney`** — Submit → Reject → Edit → Approve → Verify. Models the rejection and re-submission flow.

**`ReviewSellerReplyJourney`** — Submit → Approve → Add Seller Reply → Verify reply.

**`ReviewReportAndRemoveJourney`** — Submit → Approve → Report → Remove. Content moderation flow.

### Notifications Domain

Each journey registers a customer via the Identity API first, waits for the Engine to process `CustomerRegistered` (which auto-creates notification preferences), then exercises notification endpoints.

**`PreferenceManagementJourney`** — Register → Update Preferences → Get → Set Quiet Hours → Verify.

**`QuietHoursLifecycleJourney`** — Register → Update Preferences → Set Quiet Hours → Remove → Verify.

**`UnsubscribeResubscribeJourney`** — Register → Update Preferences → Unsubscribe → Get History → Resubscribe.

**`NotificationCancelJourney`** ⚠️ — **Specialty scenario** (excluded from defaults). Races `process-scheduled` (which transitions to Sent) against cancel requests, generating expected `CancelNotificationHandler` failures. Run via `NotificationsCancelUser`.

### Loyalty Domain

Loyalty exposes a full HTTP API (`/loyalty`), so it can be load-tested directly **and** through cross-domain events.

**`LoyaltyUser`** ✅ — **Default scenario** (`loadtests/scenarios/loyalty.py`, `make loadtest-loyalty`). Drives the Loyalty HTTP API directly across four weighted journeys: a rewards account journey (enrol → earn → redeem, reading back the `RewardAccountView` DB projection and the `PointsLeaderboard` Redis-cache projection), a campaign multiplier journey (launch → activate a `points_multiplier` `PromoCampaign`, then enrol + earn so the cross-aggregate boost applies, plus a catalog list), a **redemption saga** journey (enrol → earn → request a points-for-voucher redemption, mixing a normal reward code with a `FAIL` code to exercise the `RedemptionSaga`'s compensation/refund branch), and a points transfer journey (the application-service path). Pure happy-path — no expected failures. With `make engine-loyalty` running, this also drives the `RedemptionSaga` to completion and the published producer events (`PointsEarned`/`PointsRedeemed`/`TierUpgraded`) onto the external bus.

**`LoyaltyRewardsUser`** ⚠️ — **Specialty scenario** (run explicitly via `make loadtest-loyalty-events`). Reuses the end-to-end order journey (register → … → ship → deliver) to generate loyalty's enrol + award load via events: `CustomerRegistered` auto-enrols a reward account (subscriber pattern A) and `OrderDelivered` awards a delivery bonus (subscriber pattern B). Like `CrossDomainUser`, the E2E lifecycle can race the `OrderCheckoutSaga` and produce the same expected ordering payment-handler failures — those are about ordering's saga, not loyalty. Loyalty is also exercised incidentally by any default scenario that registers customers (`IdentityUser`) and delivers orders (`SubscriberUser`, `MixedWorkloadUser`) whenever the Loyalty engine is running.

### Cross-Domain & Race Conditions

These scenarios are the primary reason for the load testing suite. They weave threads across multiple bounded contexts and deliberately create the race conditions described in the domain specification.

**`EndToEndOrderJourney`** — The complete happy path across 5 domains. Generates **15+ events**:

| Step | Domain | Action |
|------|--------|--------|
| 1 | Identity | Register customer |
| 2-4 | Catalogue | Create product + variant + activate |
| 5-6 | Inventory | Create warehouse + initialize stock |
| 7 | Ordering | Create order |
| 8 | Inventory | Reserve stock |
| 9 | Ordering | Confirm order |
| 10-11 | Payments | Initiate payment + record pending |
| 12 | Payments | Payment webhook success |
| 13 | Ordering | Record payment success |
| 14-15 | Ordering | Ship + deliver |
| 16 | Payments | Generate invoice |

**`FlashSaleStampede`** ⚡ — **Race Condition: Concurrent Inventory Reservation**

Per the domain spec (Phase 3 — Flash Sale Scenario): Multiple users compete for the last few units of a shared inventory item. The first user sets up an item with only **10 units**, then all users try to reserve simultaneously.

- Exercises optimistic locking version conflicts
- Expected: some succeed, some get `409 Conflict` or `400 Insufficient Stock`
- Key metric: zero overselling (available never goes negative)

**`CancelDuringPaymentJourney`** ⚡ — **Race Condition: Cancel vs Payment Webhook**

Per the domain spec (Phase 2 — Scenario 2): Customer cancels while payment gateway is processing. The cancel request and payment webhook hit the server near-simultaneously.

- Tests order state machine robustness
- Expected: either cancel wins (payment gets refunded) or payment wins (cancel rejected)
- Both outcomes are valid — the system must not enter an inconsistent state

**`ConcurrentOrderModificationJourney`** ⚡ — **Race Condition: Modify During Confirmation**

Per the domain spec (Phase 2 — Scenario 3): Multiple modifications and a confirmation hit the same event-sourced order simultaneously.

- Exercises optimistic locking on the Order aggregate
- Expected: version conflicts cause some operations to fail with 409/422

**`SagaOrderCheckoutJourney`** — **Order-Payment Saga (Manual Orchestration)**

Per the domain spec (Phase 4 — Order Checkout Saga): Coordinates Order, Inventory, and Payment domains. 70% of runs follow the happy path; 30% simulate payment failure with compensation (release stock → cancel order).

### Subscriber ACL Flows

These happy-path scenarios exercise the cross-domain subscriber (anti-corruption layer) pattern. No expected failures — safe to include in default discovery.

**`SubscriberVariantStockJourney`** — Catalogue → Inventory via `CatalogueVariantSubscriber`. Creates a product with variant and verifies subscriber auto-initializes inventory stock.

**`SubscriberOrderRefundJourney`** — Ordering → Payments via `OrderReturnedSubscriber`. Walks an order through the full lifecycle to Returned, triggering auto-refund initiation.

**`SubscriberVerifiedPurchaseJourney`** — Ordering → Reviews via `OrderDeliveredSubscriber`. Delivers an order then submits a review, verifying verified-purchase flagging.

### Saga-Driven Journeys

These scenarios exercise the `OrderCheckoutSaga` process manager through async Engine event flow rather than manual API orchestration.

**`SagaDrivenCheckoutJourney`** ⚠️ — Cart → Checkout → Confirm → Reserve Stock → Pay → Verify. Polls order status to verify saga-driven state transitions (`Payment_Pending` → `Paid`). Requires Ordering, Inventory, and Payments Engines running.

**`SagaDrivenCheckoutFailureJourney`** ⚠️ — Same as above but sends a payment failure webhook to exercise the saga's retry/compensation path.

Both are excluded from default discovery and included in `CrossDomainUser`.

### Mixed Workload

**`MixedWorkloadUser`** — The recommended scenario for load baseline testing. Combines journeys from all eight bounded contexts with weights that model realistic e-commerce traffic:

| Domain | Weight | Journeys |
|--------|--------|----------|
| Identity | 12% | NewCustomer (5), AccountLifecycle (2), TierProgression (1) |
| Catalogue | 10% | ProductCatalog (3), ProductLifecycle (2), CategoryHierarchy (2) |
| Ordering | 20% | CartLifecycle (5), OrderFull (4), CartToCheckout (3), Cancellation (1), Return (1) |
| Inventory | 12% | StockInit (3), Reservation (2), DamageWriteOff (1), ReturnToStock (1), WarehouseMgmt (1) |
| Payments | 12% | PaymentSuccess (4), FailureRetry (2), Refund (1), Invoice (1) |
| Fulfillment | 10% | Creation (3), Cancellation (2), PickerCancel (1) |
| Reviews | 10% | SubmitModerate (3), Voting (2), EditResubmit (1), SellerReply (1), ReportRemove (1) |
| Notifications | 8% | PreferenceMgmt (3), UnsubResubscribe (2), QuietHours (1) |

Excluded from MixedWorkloadUser (run via specialty scenarios):
- `OrderCheckoutSagaJourney` — saga timing races
- `ExpireReservationsJourney` — global maintenance endpoint
- `FulfillmentTrackingWebhookJourney` — expected handler failures
- `NotificationCancelJourney` — cancel vs process-scheduled race

### Stress & Spike

**`EventFloodUser`** — Maximum event throughput stress. ~10 req/sec per user. Each task creates a new aggregate to avoid contention. Weighted across Identity (5), Catalogue (9), Ordering (3), Inventory (5), Payments (2). Target: saturate the outbox to test Engine drain rate.

**`CrossDomainFloodUser`** — Even pressure across 5 core domains (Identity, Catalogue, Ordering, Inventory, Payments). ~10 req/sec per user. Equal weights. Useful for finding which domain's outbox drains slowest.

**`SpikeUser`** ⚠️ — Specialty scenario. Rapid-fire customer registration at ~20 req/sec per user. Run explicitly with high user count and instant spawn rate to simulate sudden traffic bursts.

### Priority Lanes

These scenarios test the priority-based event processing pipeline where production events are processed before migration/backfill events. Requires `priority_lanes.enabled = true` in `domain.toml`.

**`MigrationWithProductionTrafficUser`** — 70% migration bulk imports (with `X-Processing-Priority: low` header), 30% production checkout traffic. Verifies production event latency remains low while migration queues up.

**`BackfillDrainRateUser`** — Seeds 100 migration events in a burst on start, then generates light production traffic. Measures how fast the backfill lane drains.

**`PriorityStarvationTestUser`** — Aggressive production traffic (~10 req/sec) alongside low-volume migration. Verifies production starves backfill.

**`PriorityLanesDisabledBaseline`** — Same traffic mix as `MigrationWithProductionTrafficUser` but without priority headers. Baseline comparison for measuring lane separation impact.

## User Classes

### Default (included in `make loadtest`)

These are safe, happy-path scenarios with no expected failures:

| Class | Wait Time | Domains | Use Case |
|-------|-----------|---------|----------|
| `IdentityUser` | 0.5–2.0s | Identity | Per-domain journeys in isolation |
| `CatalogueUser` | 0.5–2.0s | Catalogue | Per-domain journeys in isolation |
| `OrderingUser` | 0.5–2.0s | Ordering | Per-domain journeys in isolation |
| `InventoryUser` | 0.5–2.0s | Inventory | Per-domain journeys in isolation |
| `PaymentsUser` | 0.5–2.0s | Payments | Per-domain journeys in isolation |
| `FulfillmentUser` | 0.5–2.0s | Fulfillment | Per-domain journeys in isolation |
| `ReviewsUser` | 0.5–2.0s | Reviews | Per-domain journeys in isolation |
| `NotificationsUser` | 0.5–2.0s | Notifications + Identity | Per-domain journeys (registers customers first) |
| `LoyaltyUser` | 0.5–2.0s | Loyalty | HTTP API: enrol/earn/redeem/transfer + promo-campaign lifecycle |
| `SubscriberUser` | 1.0–3.0s | Cross-domain | Happy-path subscriber ACL flows |
| `MixedWorkloadUser` | 0.5–3.0s | All 9 | Realistic cross-domain load baseline (incl. loyalty) |
| `EventFloodUser` | 0.1s (constant) | 5 core | Pipeline saturation / find breaking points |

### Specialty (run explicitly — generate expected failures)

| Class | Wait Time | Domains | Use Case |
|-------|-----------|---------|----------|
| `CrossDomainUser` | 1.0–3.0s | All 5 core | E2E journeys + saga + race conditions |
| `RaceConditionUser` | 0.3–1.0s | Ordering+Inventory+Payments | Targeted race condition testing |
| `FlashSaleUser` | 0.2s (constant) | Inventory | Flash sale stampede simulation |
| `OrderingSagaUser` | 0.5–2.0s | Ordering | Saga vs direct API race |
| `FulfillmentTrackingUser` | 0.5–2.0s | Fulfillment | Tracking before shipment (state machine violations) |
| `NotificationsCancelUser` | 0.5–2.0s | Notifications | Cancel vs process-scheduled race |
| `InventoryMaintenanceUser` | 0.5–2.0s | Inventory | Expire reservations (run with `-u 1`) |
| `SpikeUser` | 0.05s (constant) | Identity | Sudden traffic burst handling |
| `CrossDomainFloodUser` | 0.1s (constant) | 5 core | Even pressure across all domains |
| `LoyaltyRewardsUser` | 0.5–2.0s | Loyalty (event-driven) | Enrol-on-register + award-on-deliver; `make loadtest-loyalty-events`; needs `engine-loyalty` |

### Priority Lanes (run explicitly — require `priority_lanes.enabled = true`)

| Class | Wait Time | Use Case |
|-------|-----------|----------|
| `MigrationWithProductionTrafficUser` | 0.5–2.0s | Mixed migration + production traffic |
| `BackfillDrainRateUser` | 0.5s (constant) | Measure backfill drain rate after burst |
| `PriorityStarvationTestUser` | 0.1s (constant) | Verify production starves backfill |
| `PriorityLanesDisabledBaseline` | 0.5–2.0s | Baseline comparison without lanes |

## Test Profiles

| Profile | Users | Spawn Rate | Duration | Scenario | Purpose |
|---------|-------|-----------|----------|----------|---------|
| **Smoke** | 5 | 1/s | 60s | MixedWorkloadUser | Verify setup works, 0% failures expected |
| **Load** | 50 | 5/s | 5 min | MixedWorkloadUser | Normal load baseline, measure p95 latency |
| **Cross-Domain** | 30 | 3/s | 5 min | CrossDomainUser | End-to-end order lifecycle + saga + races |
| **Race Conditions** | 30 | 10/s | 3 min | RaceConditionUser | Targeted race condition testing |
| **Flash Sale** | 50 | 50/s | 2 min | FlashSaleUser | Concurrent inventory reservation |
| **Stress** | 200 | 20/s | 5 min | EventFloodUser | Find the breaking point |
| **Cross-Flood** | 100 | 10/s | 5 min | CrossDomainFloodUser | Even pressure across 5 core domains |
| **Spike** | 100 | 100/s | 2 min | SpikeUser | All users spawn instantly |
| **Priority** | 30 | 5/s | 3 min | MigrationWithProductionTrafficUser | Migration vs production lane separation |
| **Backfill Drain** | 10 | 10/s | 3 min | BackfillDrainRateUser | Measure backfill drain under light load |
| **Endurance** | 30 | 3/s | 30 min | MixedWorkloadUser | Memory leaks, connection pool exhaustion |

## Running Tests

### Manual Setup

Start each component in a separate terminal:

```bash
# Terminal 1: Backend (API + engines)
make docker-dev                     # Or: make docker-dev-scaled

# Terminal 2: Observatory
make observatory

# Terminal 3: Locust
make loadtest                       # All default user classes
make loadtest-mixed                 # MixedWorkloadUser only
make loadtest-stress                # EventFloodUser only
make loadtest-cross-domain          # CrossDomainUser only
make loadtest-race                  # RaceConditionUser only
make loadtest-flash-sale            # FlashSaleUser only
make loadtest-cross-flood           # CrossDomainFloodUser only
make loadtest-priority              # MigrationWithProductionTrafficUser only
```

### Automated Stack

A single command starts everything — Docker infrastructure, API, engines (all domains), Observatory, and Locust. Ctrl-C stops all processes cleanly.

```bash
make loadtest-stack                 # 1 engine per domain
make loadtest-stack-scaled          # 3 identity + 2 catalogue + 2 ordering + 2 inventory + 2 payments
```

The script (`scripts/loadtest-stack.sh`):
1. Starts Docker infrastructure (`make docker-up`)
2. Sets up and truncates databases (`make setup-db && make truncate-db`)
3. Starts API + engine containers via Docker Compose
4. Starts Observatory locally (background)
5. Starts Locust in the foreground

### Headless / CI

For automated runs without the web UI:

```bash
# Standard load test: 50 users, 5/sec spawn, 5 minutes
make loadtest-headless

# Spike test: 100 users, instant spawn, 2 minutes
make loadtest-spike

# Race condition test: 30 users, 10/sec spawn, 3 minutes
make loadtest-headless-race

# Flash sale test: 50 users, instant spawn, 2 minutes
make loadtest-headless-flash

# Priority lanes test: 30 users, 5/sec spawn, 3 minutes
make loadtest-priority-headless

# Backfill drain rate: 10 users, 3 minutes
make loadtest-backfill-drain
```

All produce reports in `results/`:
- `results/*_stats.csv` — per-endpoint statistics
- `results/*_stats_history.csv` — time-series data
- `results/*-report.html` — visual HTML report

### Resetting Between Runs

```bash
make loadtest-clean                 # Truncates all data, preserves schema
```

## Monitoring During Tests

Three dashboards provide complementary views during a load test:

| Dashboard | URL | What It Shows |
|-----------|-----|---------------|
| **Locust** | http://localhost:8089 | Request rate, response times (p50/p95/p99), failure rate, per-endpoint breakdown |
| **Observatory** | http://localhost:9000 | Live message flow across all 9 domains, outbox queue depth, stream health |
| **Prometheus** | http://localhost:9000/metrics | Raw Prometheus-format metrics for scraping or ad-hoc queries |

### Key Metrics to Correlate

| What to Watch | Locust Metric | Observatory Metric | Warning Sign |
|---------------|--------------|-------------------|-------------|
| **Event pipeline backlog** | Requests/sec | `protean_outbox_messages{status="PENDING"}` | Pending count grows unboundedly — engines cannot keep up |
| **Version conflicts** | 409 error count | `protean_stream_pending` | High conflict rate means heavy contention on same aggregate |
| **Broker health** | Response time p95 | `protean_broker_ops_per_sec` | High latency correlating with low broker ops |
| **Consumer lag** | — | `protean_stream_pending` | Pending stream messages growing — consumers falling behind |
| **Priority lane separation** | Production p95 vs migration p95 | `protean_outbox_messages{priority="low"}` | Production latency rising when migration traffic is active |

### Race Condition Monitoring

During race condition tests, watch for:

```bash
# Version conflicts (expected during flash sale / concurrent modification)
grep "409" results/race-test_stats.csv

# Monitor inventory consistency
watch -n 2 'curl -s http://localhost:9000/metrics | grep protean_outbox_messages'

# Watch for unprocessed events (saga compensation may be pending)
watch -n 2 'curl -s http://localhost:9000/metrics | grep protean_stream_pending'
```

## Data Generators

All test data is generated by `data_generators.py` using [Faker](https://faker.readthedocs.io/). Each generator produces payloads that pass the domain's validation rules and match the exact Pydantic request schema field names.

### Identity Domain

| Generator | Output | Validation Constraints |
|-----------|--------|----------------------|
| `unique_external_id()` | `"EXT-LT-a1b2c3d4"` | UUID-based, unique per call |
| `valid_email()` | `"jdoe.f8a2@gmail.com"` | Passes `EmailAddress` VO |
| `valid_phone()` | `"+1-555-234-5678"` | Passes `PhoneNumber` VO regex |
| `customer_name()` | `("Jane", "Doe")` | Truncated to 100 chars |
| `date_of_birth()` | `"1985-03-15"` | Age 18–80 |
| `address_data()` | `{label, street, city, ...}` | All fields within schema max lengths |

### Catalogue Domain

| Generator | Output | Validation Constraints |
|-----------|--------|----------------------|
| `valid_sku(prefix)` | `"PROD-A1B2C3D4"` | Passes `SKU` VO: 3–50 chars |
| `product_data()` | `{sku, title, brand, ...}` | Full `CreateProductRequest` payload |
| `variant_data()` | `{variant_sku, base_price, ...}` | Price 9.99–299.99 |
| `image_data()` | `{url, alt_text, is_primary}` | CDN-style URL |
| `category_name()` | `"Casual Footwear"` | Truncated to 100 chars |
| `category_attributes()` | `{season, gender}` | Valid enum values |

### Ordering Domain

| Generator | Output | Validation Constraints |
|-----------|--------|----------------------|
| `order_address()` | `{street, city, ...}` | `AddressSchema` compatible |
| `order_item()` | `{product_id, variant_id, ...}` | `OrderItemSchema` compatible |
| `order_data(customer_id)` | Full `CreateOrderRequest` | With computed totals |
| `cart_data()` | `{customer_id}` | `CreateCartRequest` |
| `cart_item_data()` | `{product_id, variant_id, qty}` | `AddToCartRequest` |
| `saga_cart_item_data(product_id, variant_id)` | `{product_id, variant_id, qty}` | References specific inventory |
| `checkout_data()` | `{shipping, billing, method}` | `CheckoutRequest` |
| `shipment_data()` | `{shipment_id, carrier, ...}` | `RecordShipmentRequest` |

### Inventory Domain

| Generator | Output | Validation Constraints |
|-----------|--------|----------------------|
| `warehouse_data()` | `{name, address, capacity}` | `CreateWarehouseRequest` |
| `initialize_stock_data()` | `{product_id, sku, qty, ...}` | `InitializeStockRequest` |
| `reserve_stock_data()` | `{order_id, quantity, expires}` | `ReserveStockRequest` |

### Payments Domain

| Generator | Output | Validation Constraints |
|-----------|--------|----------------------|
| `payment_data()` | `{order_id, amount, ...}` | `InitiatePaymentRequest` with idempotency key |
| `webhook_data_success(pid)` | `{payment_id, gateway_status}` | `ProcessWebhookRequest` (succeeded) |
| `webhook_data_failure(pid)` | `{payment_id, failure_reason}` | `ProcessWebhookRequest` (failed) |
| `invoice_data()` | `{order_id, line_items, tax}` | `GenerateInvoiceRequest` |

### Fulfillment Domain

| Generator | Output | Validation Constraints |
|-----------|--------|----------------------|
| `fulfillment_data()` | `{order_id, customer_id, items}` | `CreateFulfillmentRequest` |
| `fulfillment_item_data()` | `{order_item_id, product_id, ...}` | `FulfillmentItemRequest` |

### Reviews Domain

| Generator | Output | Validation Constraints |
|-----------|--------|----------------------|
| `review_data()` | `{product_id, customer_id, rating, ...}` | `SubmitReviewRequest`, rating weighted 4-5 stars |
| `edit_review_data(customer_id)` | `{customer_id, title, body, rating}` | `EditReviewRequest` |

### Notifications Domain

| Generator | Output | Validation Constraints |
|-----------|--------|----------------------|
| `notification_preferences_data()` | `{email_enabled, sms_enabled, ...}` | `UpdatePreferencesRequest` |
| `quiet_hours_data()` | `{start, end}` | `SetQuietHoursRequest` |
| `notification_type()` | `"OrderConfirmation"` | Valid `NotificationType` enum value |

## Project Structure

```
loadtests/
├── locustfile.py              # Entry point — imports default user classes,
│                              #   test_start/test_stop event hooks,
│                              #   Observatory metrics fetch on stop
├── locust.conf                # Default config (host, web UI port)
├── data_generators.py         # Faker-based payload generators (all 9 domains)
│
├── scenarios/
│   ├── identity.py            # NewCustomerJourney, AccountLifecycleJourney,
│   │                          #   TierProgressionJourney, IdentityUser
│   ├── catalogue.py           # ProductCatalogBuilder, ProductLifecycleJourney,
│   │                          #   CategoryHierarchyBuilder, CatalogueUser
│   ├── ordering.py            # CartLifecycleJourney, OrderFullLifecycleJourney,
│   │                          #   CartToCheckoutJourney, OrderCancellationJourney,
│   │                          #   OrderReturnJourney, OrderingUser
│   │                          #   + OrderCheckoutSagaJourney, OrderingSagaUser (specialty)
│   ├── inventory.py           # StockInitAndReceiveJourney, ReservationLifecycleJourney,
│   │                          #   ReservationReleaseJourney, DamageWriteOffJourney,
│   │                          #   ReturnToStockJourney, WarehouseManagementJourney,
│   │                          #   InventoryUser
│   │                          #   + ExpireReservationsJourney, InventoryMaintenanceUser (specialty)
│   ├── payments.py            # PaymentSuccessJourney, PaymentFailureRetryJourney,
│   │                          #   PaymentRefundJourney, InvoiceJourney, PaymentsUser
│   ├── fulfillment.py         # FulfillmentCreationJourney, FulfillmentCancellationJourney,
│   │                          #   FulfillmentPickerCancelJourney, FulfillmentUser
│   │                          #   + FulfillmentTrackingWebhookJourney, FulfillmentTrackingUser (specialty)
│   ├── reviews.py             # ReviewSubmitAndModerateJourney, ReviewVotingJourney,
│   │                          #   ReviewEditAndResubmitJourney, ReviewSellerReplyJourney,
│   │                          #   ReviewReportAndRemoveJourney, ReviewsUser
│   ├── notifications.py       # PreferenceManagementJourney, QuietHoursLifecycleJourney,
│   │                          #   UnsubscribeResubscribeJourney, NotificationsUser
│   │                          #   + NotificationCancelJourney, NotificationsCancelUser (specialty)
│   ├── cross_domain.py        # EndToEndOrderJourney, FlashSaleStampede,
│   │                          #   CancelDuringPaymentJourney, ConcurrentOrderModificationJourney,
│   │                          #   SagaOrderCheckoutJourney, SagaDrivenCheckoutJourney,
│   │                          #   SagaDrivenCheckoutFailureJourney,
│   │                          #   SubscriberVariantStockJourney, SubscriberOrderRefundJourney,
│   │                          #   SubscriberVerifiedPurchaseJourney,
│   │                          #   CrossDomainUser, FlashSaleUser, RaceConditionUser, SubscriberUser
│   ├── mixed.py               # MixedWorkloadUser (all 9 domains, weighted)
│   ├── stress.py              # EventFloodUser, SpikeUser, CrossDomainFloodUser
│   └── priority_lanes.py      # MigrationBulkImportPhase, ProductionTrafficPhase,
│                              #   MigrationWithProductionTrafficUser, BackfillDrainRateUser,
│                              #   PriorityStarvationTestUser, PriorityLanesDisabledBaseline
│
└── helpers/
    ├── state.py               # CustomerState, ProductState, CategoryState,
    │                          #   CartState, OrderState, InventoryState,
    │                          #   PaymentState, FulfillmentState, ReviewState,
    │                          #   NotificationState, CrossDomainState, SagaState
    └── response.py            # API error extraction utility
```

Supporting files:
- `scripts/loadtest-stack.sh` — Full-stack orchestration script (all domains)
- `results/` — Output directory for headless CSV/HTML reports (gitignored)

## Extending Scenarios

### Adding a New Journey

1. Create a new `SequentialTaskSet` in the appropriate scenario file
2. Add data generators to `data_generators.py` if needed
3. Add state tracking to `helpers/state.py` if needed
4. Add it to the appropriate `HttpUser.tasks` dict with a weight
5. Import the new `HttpUser` in `locustfile.py` (or exclude with a comment if it generates expected failures)

### Key Patterns

- **`catch_response=True`** — Required for custom success/failure logic
- **`name="PUT /orders/{id}/confirm"`** — Groups requests by logical endpoint in stats
- **`self.interrupt()`** on failure — Skips remaining steps, user restarts a fresh journey
- **Race condition tasks** mark expected errors (409, 422) as `resp.success()` to avoid polluting failure stats
- **Prefix tags** (`[E2E]`, `[SAGA]`, `[FLASH]`, `[RACE-CANCEL]`, `[STRESS]`, `[MIGRATION]`, etc.) group requests visually in Locust stats

### Default vs Specialty Scenarios

Scenarios that generate expected failures are excluded from default Locust discovery in `locustfile.py`. They have dedicated `HttpUser` subclasses and must be run explicitly. This prevents expected race-condition failures from polluting normal load test results.

## Known API Limitations

- **`POST /fulfillments`** does not return internal `FulfillmentItem` IDs — the pick endpoint requires item IDs. Use `GET /fulfillments/{id}` to retrieve them after creation.

## Troubleshooting

### "Connection refused" errors

The API server is not running. Start it with `make docker-dev` or `make api`.

### High failure rate on registration

Check that databases exist and have the correct schema:
```bash
make setup-db
```

### Observatory not loading on port 9000

Ensure all domain modules can be imported. The observatory loads all domains specified in `make observatory`. Check that all `src/*/domain.py` files exist and import correctly.

### Outbox messages growing unboundedly

Engines are not running or cannot keep up. Start more engine workers:
```bash
make docker-dev-scaled
```

### Flash sale shows 0% failures

If all flash sale reservations succeed, the initial stock quantity (10 units) is too high relative to user count. Increase users or decrease stock in `FlashSaleStampede._setup_shared_inventory()`.

### Notification scenarios failing on preferences

Notification journeys register a customer first, then wait 0.5s for the Engine to process `CustomerRegistered` and auto-create preferences. If the Engine is slow or not running, preference endpoints will return 404. Ensure the Identity and Notifications Engines are running.

### Cleaning up after a load test

```bash
make loadtest-clean                 # Truncates all tables, preserves schema
# Or for a full reset:
make drop-db && make setup-db
```
