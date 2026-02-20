# Load Testing

Locust-based load testing suite for ShopStream. Simulates realistic e-commerce traffic across all five bounded contexts (Identity, Catalogue, Ordering, Inventory, Payments), exercising the full CQRS event pipeline — from HTTP command processing through outbox persistence, Redis Streams publishing, and projector consumption.

Includes targeted race condition scenarios based on the domain specification: concurrent checkout, flash sale stampede, cancel-during-payment, and concurrent order modification.

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
  - [Cross-Domain & Race Conditions](#cross-domain--race-conditions)
  - [Mixed Workload](#mixed-workload)
  - [Stress & Spike](#stress--spike)
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
- [Troubleshooting](#troubleshooting)

## Architecture

During a load test, the following processes run simultaneously:

```
┌─────────────────────┐     HTTP      ┌─────────────────────┐
│  Locust (:8089)     │──────────────▶│  FastAPI API (:8000) │
│                     │  commands     │                     │
│  Simulated users    │               │  /customers/*       │
│  generate traffic   │               │  /products/*        │
│  across 5 domains   │               │  /orders/*          │
│                     │               │  /inventory/*       │
│                     │               │  /payments/*        │
└─────────────────────┘               └──────────┬──────────┘
                                                 │ atomic writes
                                                 ▼
┌─────────────────────┐               ┌──────────────────────┐
│  Observatory (:9000)│               │  PostgreSQL          │
│                     │◀ ─ ─ scrape ─ │  5 domain databases  │
│  Live dashboard     │               │  Outbox tables       │
│  Prometheus /metrics│               └──────────┬───────────┘
└─────────────────────┘                          │ drain
                                                 ▼
                                      ┌──────────────────────┐
                                      │  Engine Workers       │
                                      │  (5 domains)          │
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

This installs Locust into an optional `[tool.poetry.group.loadtest]` dependency group.

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

**`NewCustomerJourney`** — The most common user flow. Generates **5 domain events**.

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

**`ProductCatalogBuilder`** — Seller building a product listing. Generates **6 domain events** (Create → 2 Variants → 2 Images → Activate).

**`ProductLifecycleJourney`** — Full product state machine. Generates **5 domain events** (Draft → Active → Discontinued → Archived).

**`CategoryHierarchyBuilder`** — 3-level category tree with mutations. Generates **6 domain events**.

### Ordering Domain

**`CartLifecycleJourney`** — Cart browsing and abandonment. Generates **5+ events** (Create → Add Items ×3 → Abandon).

**`OrderFullLifecycleJourney`** — Happy path order lifecycle. Generates **8 events** (Create → Confirm → Payment Pending → Payment Success → Processing → Ship → Deliver → Complete).

**`CartToCheckoutJourney`** — Cart-to-order conversion. The most common purchase path.

**`OrderCancellationJourney`** — Cancel during payment + refund path. Tests compensation logic.

**`OrderReturnJourney`** — Full return flow (Create → ... → Deliver → Request Return → Approve → Record Return).

### Inventory Domain

**`StockInitAndReceiveJourney`** — Warehouse setup: Create Warehouse → Initialize Stock → Receive → Adjust → Stock Check.

**`ReservationLifecycleJourney`** — Order-driven reservation: Init Stock → Reserve.

**`ReservationReleaseJourney`** — Cancelled order releasing stock: Init → Reserve → Release.

**`DamageWriteOffJourney`** — Damage reporting: Init → Mark Damaged → Write Off.

### Payments Domain

**`PaymentSuccessJourney`** — Happy path: Initiate → Webhook Success.

**`PaymentFailureRetryJourney`** — Retry logic: Initiate → Webhook Failure → Retry → Webhook Success.

**`PaymentRefundJourney`** — Refund flow: Initiate → Success → Refund Request → Refund Webhook.

**`InvoiceJourney`** — Invoice lifecycle: Generate → Void.

### Cross-Domain & Race Conditions

These scenarios are the primary reason for the load testing suite. They weave threads across multiple bounded contexts and deliberately create the race conditions described in the domain specification.

**`EndToEndOrderJourney`** — The complete happy path across all 5 domains. Generates **15+ events**:

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
- Expected: some succeed, some get `409 Conflict` or `422 Insufficient Stock`
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

**`SagaOrderCheckoutJourney`** — **Order-Payment Saga (Distributed Transaction)**

Per the domain spec (Phase 4 — Order Checkout Saga): Coordinates Order, Inventory, and Payment domains. 70% of runs follow the happy path; 30% simulate payment failure with compensation (release stock → cancel order).

## User Classes

Locust discovers these `HttpUser` subclasses from `locustfile.py`:

| Class | Wait Time | Domains | Use Case |
|-------|-----------|---------|----------|
| `IdentityUser` | 0.5–2.0s | Identity | Test Identity endpoints in isolation |
| `CatalogueUser` | 0.5–2.0s | Catalogue | Test Catalogue endpoints in isolation |
| `OrderingUser` | 0.5–2.0s | Ordering | Test Ordering endpoints in isolation |
| `InventoryUser` | 0.5–2.0s | Inventory | Test Inventory endpoints in isolation |
| `PaymentsUser` | 0.5–2.0s | Payments | Test Payments endpoints in isolation |
| `MixedWorkloadUser` | 0.5–3.0s | All 5 | Realistic cross-domain load baseline |
| `CrossDomainUser` | 1.0–3.0s | All 5 | End-to-end journeys + saga + race conditions |
| `RaceConditionUser` | 0.3–1.0s | Ordering+Inventory+Payments | Targeted race condition testing |
| `FlashSaleUser` | 0.2s (constant) | Inventory | Flash sale stampede simulation |
| `EventFloodUser` | 0.1s (constant) | All 5 | Pipeline saturation / find breaking points |
| `CrossDomainFloodUser` | 0.1s (constant) | All 5 | Even pressure across all domains |
| `SpikeUser` | 0.05s (constant) | Identity | Sudden traffic burst handling |

## Test Profiles

| Profile | Users | Spawn Rate | Duration | Scenario | Purpose |
|---------|-------|-----------|----------|----------|---------|
| **Smoke** | 5 | 1/s | 60s | MixedWorkloadUser | Verify setup works, 0% failures expected |
| **Load** | 50 | 5/s | 5 min | MixedWorkloadUser | Normal load baseline, measure p95 latency |
| **Cross-Domain** | 30 | 3/s | 5 min | CrossDomainUser | End-to-end order lifecycle across all domains |
| **Race Conditions** | 30 | 10/s | 3 min | RaceConditionUser | Targeted race condition testing |
| **Flash Sale** | 50 | 50/s | 2 min | FlashSaleUser | Concurrent inventory reservation |
| **Stress** | 200 | 20/s | 5 min | EventFloodUser | Find the breaking point |
| **Cross-Flood** | 100 | 10/s | 5 min | CrossDomainFloodUser | Even pressure across all 5 domains |
| **Spike** | 100 | 100/s | 2 min | SpikeUser | All users spawn instantly |
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
make loadtest                       # All user classes
make loadtest-mixed                 # MixedWorkloadUser only
make loadtest-cross-domain          # CrossDomainUser only
make loadtest-race                  # RaceConditionUser only
make loadtest-flash-sale            # FlashSaleUser only
make loadtest-stress                # EventFloodUser only
make loadtest-cross-flood           # CrossDomainFloodUser only
```

### Automated Stack

A single command starts everything — Docker infrastructure, API, engines (all 5 domains), Observatory, and Locust. Ctrl-C stops all processes cleanly.

```bash
make loadtest-stack                 # 1 engine per domain
make loadtest-stack-scaled          # 3 identity + 2 catalogue + 2 ordering + 2 inventory + 2 payments
```

The script (`scripts/loadtest-stack.sh`):
1. Starts Docker infrastructure (`make docker-up`)
2. Sets up and truncates databases (`make setup-db && make truncate-db`)
3. Starts API + all 5 engine containers via Docker Compose
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
| **Observatory** | http://localhost:9000 | Live message flow across all 5 domains, outbox queue depth, stream health |
| **Prometheus** | http://localhost:9000/metrics | Raw Prometheus-format metrics for scraping or ad-hoc queries |

### Key Metrics to Correlate

| What to Watch | Locust Metric | Observatory Metric | Warning Sign |
|---------------|--------------|-------------------|-------------|
| **Event pipeline backlog** | Requests/sec | `protean_outbox_messages{status="PENDING"}` | Pending count grows unboundedly — engines cannot keep up |
| **Version conflicts** | 409 error count | `protean_stream_pending` | High conflict rate means heavy contention on same aggregate |
| **Broker health** | Response time p95 | `protean_broker_ops_per_sec` | High latency correlating with low broker ops |
| **Consumer lag** | — | `protean_stream_pending` | Pending stream messages growing — consumers falling behind |

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
| `address_data()` | `{label, street, city, ...}` | All fields within schema max lengths |

### Catalogue Domain

| Generator | Output | Validation Constraints |
|-----------|--------|----------------------|
| `valid_sku(prefix)` | `"PROD-A1B2C3D4"` | Passes `SKU` VO: 3–50 chars |
| `product_data()` | `{sku, title, brand, ...}` | Full `CreateProductRequest` payload |
| `variant_data()` | `{variant_sku, base_price, ...}` | Price 9.99–299.99 |
| `image_data()` | `{url, alt_text, is_primary}` | CDN-style URL |

### Ordering Domain

| Generator | Output | Validation Constraints |
|-----------|--------|----------------------|
| `order_address()` | `{street, city, ...}` | `AddressSchema` compatible |
| `order_item()` | `{product_id, variant_id, ...}` | `OrderItemSchema` compatible |
| `order_data(customer_id)` | Full `CreateOrderRequest` | With computed totals |
| `cart_data()` | `{customer_id}` | `CreateCartRequest` |
| `cart_item_data()` | `{product_id, variant_id, qty}` | `AddToCartRequest` |
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

## Project Structure

```
loadtests/
├── locustfile.py              # Entry point — imports all user classes,
│                              #   test_start/test_stop event hooks
├── locust.conf                # Default config (host, web UI port)
├── data_generators.py         # Faker-based payload generators (all 5 domains)
│
├── scenarios/
│   ├── identity.py            # NewCustomerJourney, AccountLifecycleJourney,
│   │                          #   TierProgressionJourney, IdentityUser
│   ├── catalogue.py           # ProductCatalogBuilder, ProductLifecycleJourney,
│   │                          #   CategoryHierarchyBuilder, CatalogueUser
│   ├── ordering.py            # CartLifecycleJourney, OrderFullLifecycleJourney,
│   │                          #   CartToCheckoutJourney, OrderCancellationJourney,
│   │                          #   OrderReturnJourney, OrderingUser
│   ├── inventory.py           # StockInitAndReceiveJourney, ReservationLifecycleJourney,
│   │                          #   ReservationReleaseJourney, DamageWriteOffJourney,
│   │                          #   InventoryUser
│   ├── payments.py            # PaymentSuccessJourney, PaymentFailureRetryJourney,
│   │                          #   PaymentRefundJourney, InvoiceJourney, PaymentsUser
│   ├── cross_domain.py        # EndToEndOrderJourney, FlashSaleStampede,
│   │                          #   CancelDuringPaymentJourney, ConcurrentOrderModificationJourney,
│   │                          #   SagaOrderCheckoutJourney, CrossDomainUser,
│   │                          #   FlashSaleUser, RaceConditionUser
│   ├── mixed.py               # MixedWorkloadUser (all 5 domains)
│   └── stress.py              # EventFloodUser, SpikeUser, CrossDomainFloodUser
│
└── helpers/
    ├── state.py               # CustomerState, ProductState, CategoryState,
    │                          #   CartState, OrderState, InventoryState,
    │                          #   PaymentState, CrossDomainState
    └── response.py            # API error extraction utility
```

Supporting files:
- `scripts/loadtest-stack.sh` — Full-stack orchestration script (all 5 domains)
- `results/` — Output directory for headless CSV/HTML reports (gitignored)

## Extending Scenarios

### Adding a New Journey

1. Create a new `SequentialTaskSet` in the appropriate scenario file
2. Add data generators to `data_generators.py` if needed
3. Add state tracking to `helpers/state.py` if needed
4. Add it to the appropriate `HttpUser.tasks` dict with a weight
5. Import the new `HttpUser` in `locustfile.py`

### Key Patterns

- **`catch_response=True`** — Required for custom success/failure logic
- **`name="PUT /orders/{id}/confirm"`** — Groups requests by logical endpoint in stats
- **`self.interrupt()`** on failure — Skips remaining steps
- **Race condition tasks** mark expected errors (409, 422) as `resp.success()` to avoid polluting failure stats

## Troubleshooting

### "Connection refused" errors

The API server is not running. Start it with `make docker-dev` or `make api`.

### High failure rate on registration

Check that databases exist and have the correct schema:
```bash
make setup-db
```

### Observatory not loading on port 9000

Ensure all 5 domain modules can be imported. The observatory loads all domains specified in `make observatory`. Check `src/inventory/domain.py` and `src/payments/domain.py` exist and import correctly.

### Outbox messages growing unboundedly

Engines are not running or cannot keep up. Start more engine workers:
```bash
make docker-dev-scaled
# Or natively:
make engine-identity-scaled
make engine-ordering-scaled
make engine-inventory-scaled
make engine-payments-scaled
```

### Flash sale shows 0% failures

If all flash sale reservations succeed, the initial stock quantity (10 units) is too high relative to user count. Increase users or decrease stock in `FlashSaleStampede._setup_shared_inventory()`.

### Cleaning up after a load test

```bash
make loadtest-clean                 # Truncates all tables, preserves schema
# Or for a full reset:
make drop-db && make setup-db
```
