# Load Testing

Locust-based load testing suite for ShopStream. Simulates realistic e-commerce traffic across both the Identity and Catalogue domains, exercising the full CQRS event pipeline — from HTTP command processing through outbox persistence, Redis Streams publishing, and projector consumption.

## Table of Contents

- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Scenarios](#scenarios)
  - [Identity Domain](#identity-domain)
  - [Catalogue Domain](#catalogue-domain)
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
│  across domains     │               │  /categories/*      │
└─────────────────────┘               └──────────┬──────────┘
                                                  │ atomic writes
                                                  ▼
┌─────────────────────┐               ┌──────────────────────┐
│  Observatory (:9000)│               │  PostgreSQL          │
│                     │◀ ─ ─ scrape ─ │  Aggregate tables    │
│  Live dashboard     │               │  Outbox table        │
│  Prometheus /metrics│               └──────────┬───────────┘
└─────────────────────┘                          │ drain
                                                  ▼
                                      ┌──────────────────────┐
                                      │  Engine Workers       │
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
make loadtest-stack-scaled    # Scaled: 3 identity + 2 catalogue engines
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

The first address is automatically set as default by the domain (invariant: exactly one default when addresses exist). The tier upgrade goes from STANDARD to SILVER.

**`AccountLifecycleJourney`** — Exercises the full account state machine. Generates **4 domain events**.

| Step | Endpoint | State Transition |
|------|----------|-----------------|
| 1. Register | `POST /customers` | → Active |
| 2. Suspend | `PUT /customers/{id}/suspend` | Active → Suspended |
| 3. Reactivate | `PUT /customers/{id}/reactivate` | Suspended → Active |
| 4. Close | `PUT /customers/{id}/close` | Active → Closed |

**`TierProgressionJourney`** — Walks through the full tier ladder. Generates **4 domain events**.

| Step | Endpoint | Tier |
|------|----------|------|
| 1. Register | `POST /customers` | STANDARD |
| 2. Upgrade | `PUT /customers/{id}/tier` | → SILVER |
| 3. Upgrade | `PUT /customers/{id}/tier` | → GOLD |
| 4. Upgrade | `PUT /customers/{id}/tier` | → PLATINUM |

The domain enforces that tiers can only go up (no downgrades), so this respects the invariant.

### Catalogue Domain

**`ProductCatalogBuilder`** — Models a seller building a complete product listing. Generates **6 domain events**.

| Step | Endpoint | Event Raised |
|------|----------|-------------|
| 1. Create product | `POST /products` | `ProductCreated` |
| 2. Add variant (size S) | `POST /products/{id}/variants` | `VariantAdded` |
| 3. Add variant (size M) | `POST /products/{id}/variants` | `VariantAdded` |
| 4. Add primary image | `POST /products/{id}/images` | `ProductImageAdded` |
| 5. Add secondary image | `POST /products/{id}/images` | `ProductImageAdded` |
| 6. Activate | `PUT /products/{id}/activate` | `ProductActivated` |

Activation requires at least one variant (domain invariant), which step 2 satisfies.

**`ProductLifecycleJourney`** — Exercises the full product state machine. Generates **5 domain events**.

| Step | Endpoint | Status |
|------|----------|--------|
| 1. Create | `POST /products` | Draft |
| 2. Add variant | `POST /products/{id}/variants` | Draft (required for activation) |
| 3. Activate | `PUT /products/{id}/activate` | → Active |
| 4. Discontinue | `PUT /products/{id}/discontinue` | → Discontinued |
| 5. Archive | `PUT /products/{id}/archive` | → Archived |

**`CategoryHierarchyBuilder`** — Creates a 3-level category tree, then mutates it. Generates **6 domain events**.

| Step | Endpoint | Event Raised |
|------|----------|-------------|
| 1. Create root | `POST /categories` | `CategoryCreated` |
| 2. Create child | `POST /categories` (parent=root) | `CategoryCreated` |
| 3. Create grandchild | `POST /categories` (parent=child) | `CategoryCreated` |
| 4. Update root | `PUT /categories/{id}` | `CategoryDetailsUpdated` |
| 5. Reorder leaf | `PUT /categories/{id}/reorder` | `CategoryReordered` |
| 6. Deactivate leaf | `PUT /categories/{id}/deactivate` | `CategoryDeactivated` |

Category depth is limited to 5 levels; this journey creates 3 (root=0, child=1, grandchild=2).

### Mixed Workload

**`MixedWorkloadUser`** combines all six journeys with weights that model realistic e-commerce traffic:

| Journey | Weight | Share | Rationale |
|---------|--------|-------|-----------|
| NewCustomerJourney | 10 | 33% | Most common write operation |
| ProductCatalogBuilder | 8 | 27% | Frequent seller activity |
| AccountLifecycleJourney | 4 | 13% | Less frequent |
| TierProgressionJourney | 3 | 10% | Occasional |
| ProductLifecycleJourney | 3 | 10% | Occasional |
| CategoryHierarchyBuilder | 2 | 7% | Admin-only activity |

This creates cross-domain pressure on both PostgreSQL databases simultaneously, testing the `DomainContextMiddleware`'s routing under load.

### Stress & Spike

**`EventFloodUser`** — Maximum event throughput. Every task creates a brand-new aggregate (no sequential dependencies, no contention). Runs at ~10 requests/second per user via `constant_pacing(0.1)`.

| Task | Weight | Events per call |
|------|--------|----------------|
| Register customer | 5 | 1 |
| Create product + variant | 4 | 2 |
| Create product | 3 | 1 |
| Create category | 2 | 1 |

With 100 users, this generates ~1,000 requests/second and ~1,200+ events/second. The key metric to watch is `protean_outbox_messages{status="PENDING"}` — if it grows unboundedly, the engines cannot keep up with the event generation rate.

**`SpikeUser`** — Rapid-fire customer registration at ~20 requests/second per user via `constant_pacing(0.05)`. Used with instant spawn rates (`-r 100`) to simulate sudden traffic bursts.

## User Classes

Locust discovers these 5 `HttpUser` subclasses from `locustfile.py`:

| Class | Wait Time | Domain | Use Case |
|-------|-----------|--------|----------|
| `IdentityUser` | 0.5–2.0s | Identity | Test Identity endpoints in isolation |
| `CatalogueUser` | 0.5–2.0s | Catalogue | Test Catalogue endpoints in isolation |
| `MixedWorkloadUser` | 0.5–3.0s | Both | Realistic cross-domain load baseline |
| `EventFloodUser` | 0.1s (constant) | Both | Pipeline saturation / find breaking points |
| `SpikeUser` | 0.05s (constant) | Identity | Sudden traffic burst handling |

Select specific classes via the Locust web UI or CLI:

```bash
poetry run locust -f loadtests/locustfile.py --host http://localhost:8000 MixedWorkloadUser
```

## Test Profiles

| Profile | Users | Spawn Rate | Duration | Scenario | Purpose |
|---------|-------|-----------|----------|----------|---------|
| **Smoke** | 5 | 1/s | 60s | MixedWorkloadUser | Verify setup works, 0% failures expected |
| **Load** | 50 | 5/s | 5 min | MixedWorkloadUser | Normal load baseline, measure p95 latency |
| **Stress** | 200 | 20/s | 5 min | EventFloodUser | Find the breaking point — where do errors start? |
| **Spike** | 100 | 100/s | 2 min | SpikeUser | All users spawn instantly — how fast does recovery take? |
| **Endurance** | 30 | 3/s | 30 min | MixedWorkloadUser | Memory leaks, connection pool exhaustion, outbox table growth |

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
make loadtest-stress                # EventFloodUser only
```

For multi-worker engine testing without Docker:

```bash
# Terminal 1: Infrastructure
make docker-up

# Terminal 2: API server
make api

# Terminal 3: Scaled Identity engine (4 workers)
make engine-identity-scaled

# Terminal 4: Scaled Catalogue engine (4 workers)
make engine-catalogue-scaled

# Terminal 5: Observatory
make observatory

# Terminal 6: Locust
make loadtest-stress
```

### Automated Stack

A single command starts everything — Docker infrastructure, API, engines, Observatory, and Locust. Ctrl-C stops all processes cleanly.

```bash
make loadtest-stack                 # 1 engine per domain
make loadtest-stack-scaled          # 3 identity + 2 catalogue engine containers
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
```

Both produce reports in `results/`:
- `results/loadtest_stats.csv` — per-endpoint statistics
- `results/loadtest_stats_history.csv` — time-series data
- `results/loadtest-report.html` — visual HTML report

### Resetting Between Runs

```bash
make loadtest-clean                 # Truncates all data, preserves schema
```

This runs `make truncate-db` which clears both Identity and Catalogue databases without dropping and recreating tables.

## Monitoring During Tests

Three dashboards provide complementary views during a load test:

| Dashboard | URL | What It Shows |
|-----------|-----|---------------|
| **Locust** | http://localhost:8089 | Request rate, response times (p50/p95/p99), failure rate, per-endpoint breakdown |
| **Observatory** | http://localhost:9000 | Live message flow across domains, outbox queue depth, stream health |
| **Prometheus** | http://localhost:9000/metrics | Raw Prometheus-format metrics for scraping or ad-hoc queries |

### Key Metrics to Correlate

| What to Watch | Locust Metric | Observatory Metric | Warning Sign |
|---------------|--------------|-------------------|-------------|
| **Event pipeline backlog** | Requests/sec | `protean_outbox_messages{status="PENDING"}` | Pending count grows unboundedly — engines cannot keep up |
| **Broker health** | Response time p95 | `protean_broker_ops_per_sec` | High latency correlating with low broker ops |
| **Consumer lag** | — | `protean_stream_pending` | Pending stream messages growing — consumers falling behind |
| **Infrastructure down** | Failure rate spikes | `protean_broker_up` | Broker goes down, all writes start failing |

### Quick CLI Monitoring

```bash
# Watch outbox depth during a load test
watch -n 2 'curl -s http://localhost:9000/metrics | grep protean_outbox_messages'

# Watch stream pending counts
watch -n 2 'curl -s http://localhost:9000/metrics | grep protean_stream_pending'
```

### End-of-Test Metrics

When a Locust run completes (or is stopped), the `locustfile.py` automatically fetches and prints Observatory metrics to the terminal — outbox depth, stream pending, and broker stats. This gives an immediate snapshot of event pipeline health without switching dashboards.

## Data Generators

All test data is generated by `data_generators.py` using [Faker](https://faker.readthedocs.io/). Each generator produces payloads that pass the domain's validation rules and match the exact Pydantic request schema field names.

### Identity Domain

| Generator | Output | Validation Constraints |
|-----------|--------|----------------------|
| `unique_external_id()` | `"EXT-LT-a1b2c3d4"` | UUID-based, unique per call |
| `valid_email()` | `"jdoe.f8a2@gmail.com"` | Passes `EmailAddress` VO: single `@`, no spaces, valid domain |
| `valid_phone()` | `"+1-555-234-5678"` | Passes `PhoneNumber` VO regex: `^\+?[\d\s\-()]+$` |
| `customer_name()` | `("Jane", "Doe")` | Faker names, truncated to 100 chars |
| `date_of_birth()` | `"1985-03-15"` | ISO format, age 18–80 |
| `address_data()` | `{label, street, city, ...}` | Label from `[Home, Work, Other]`, all fields within schema max lengths |

### Catalogue Domain

| Generator | Output | Validation Constraints |
|-----------|--------|----------------------|
| `valid_sku(prefix)` | `"PROD-A1B2C3D4"` | Passes `SKU` VO: 3–50 chars, alphanumeric + hyphens, no leading/trailing/consecutive hyphens |
| `product_data()` | `{sku, title, brand, slug, ...}` | Full `CreateProductRequest` payload, slug is lowercase + hex |
| `variant_data()` | `{variant_sku, base_price, ...}` | Price 9.99–299.99, weight/dimensions with units |
| `image_data(is_primary)` | `{url, alt_text, is_primary}` | CDN-style URL, alt_text ≤ 255 chars |
| `category_name()` | `"Casual Footwear"` | Two capitalized words, ≤ 100 chars |

### State Tracking

Each Locust user maintains its own state via dataclasses in `helpers/state.py`:

- **`CustomerState`** — tracks `customer_id` returned by registration, plus `address_count`, `current_tier`, `current_status`
- **`ProductState`** — tracks `product_id` returned by creation, plus `variant_count`, `image_count`, `current_status`
- **`CategoryState`** — tracks list of `category_ids` to build parent-child relationships

State is per-user-instance (no cross-user sharing), which matches the CQRS model where each session operates on its own aggregates.

**API limitation:** The API returns aggregate root IDs (`customer_id`, `product_id`, `category_id`) but does not return sub-entity IDs (`address_id`, `variant_id`, `image_id`). Therefore, operations like `update_address`, `update_variant_price`, or `remove_image` — which require sub-entity IDs in the URL path — are not included in load test scenarios. This still covers 18 of 24 endpoints and generates all 24 event types.

## Project Structure

```
loadtests/
├── locustfile.py              # Entry point — imports all user classes,
│                              #   test_start/test_stop event hooks
├── locust.conf                # Default config (host, web UI port)
├── data_generators.py         # Faker-based payload generators
│
├── scenarios/
│   ├── identity.py            # NewCustomerJourney, AccountLifecycleJourney,
│   │                          #   TierProgressionJourney, IdentityUser
│   ├── catalogue.py           # ProductCatalogBuilder, ProductLifecycleJourney,
│   │                          #   CategoryHierarchyBuilder, CatalogueUser
│   ├── mixed.py               # MixedWorkloadUser (cross-domain)
│   └── stress.py              # EventFloodUser, SpikeUser
│
└── helpers/
    └── state.py               # CustomerState, ProductState, CategoryState
```

Supporting files:
- `scripts/loadtest-stack.sh` — Full-stack orchestration script
- `results/` — Output directory for headless CSV/HTML reports (gitignored)

## Extending Scenarios

### Adding a New Journey

1. Create a new `SequentialTaskSet` in the appropriate scenario file:

```python
class MyNewJourney(SequentialTaskSet):
    def on_start(self):
        self.state = CustomerState()

    @task
    def step_one(self):
        with self.client.post("/customers", json=..., catch_response=True,
                              name="POST /customers") as resp:
            if resp.status_code == 201:
                self.state.customer_id = resp.json()["customer_id"]
            else:
                resp.failure(f"Failed: {resp.status_code}")
                self.interrupt()  # Abort remaining steps

    @task
    def step_two(self):
        # Use self.state.customer_id from step_one
        ...

    @task
    def done(self):
        self.interrupt()  # Restart the journey
```

2. Add it to the appropriate `HttpUser.tasks` dict with a weight.

3. If it needs new data, add a generator to `data_generators.py`.

### Key Patterns

- **`catch_response=True`** — Required for custom success/failure logic. Without it, any 2xx/3xx is "success".
- **`name="PUT /customers/{id}/profile"`** — Groups requests by logical endpoint in Locust stats, rather than splitting by unique URL.
- **`self.interrupt()`** on failure — Skips remaining steps in the sequential task set. The user then restarts a fresh journey.
- **`self.interrupt()`** at the end — Signals the task set is complete. Without this, `SequentialTaskSet` loops back to the first task.

### Adding a New User Class

```python
class MyUser(HttpUser):
    wait_time = between(0.5, 2.0)       # Random pause between journeys
    tasks = {
        MyNewJourney: 5,                  # Weight: 5/8 = 62.5%
        ExistingJourney: 3,               # Weight: 3/8 = 37.5%
    }
```

Import it in `locustfile.py` so Locust discovers it.

## Troubleshooting

### "Connection refused" errors

The API server is not running. Start it with `make docker-dev` or `make api`.

### High failure rate on registration

Check that databases exist and have the correct schema:
```bash
make setup-db
```

### Outbox messages growing unboundedly

Engines are not running or cannot keep up. Start more engine workers:
```bash
make docker-dev-scaled                  # 3 identity + 2 catalogue containers
# Or natively:
make engine-identity-scaled             # 4 identity workers
make engine-catalogue-scaled            # 4 catalogue workers
```

### "RecursionError" when importing locust in Python 3.13

This is a known gevent/Python 3.13 monkey-patching issue that only occurs when importing `locust` from a regular Python script. The `locust` CLI handles this correctly. Always run via `make loadtest*` or `poetry run locust`.

### Cleaning up after a load test

```bash
make loadtest-clean                     # Truncates all tables, preserves schema
# Or for a full reset:
make drop-db && make setup-db
```
