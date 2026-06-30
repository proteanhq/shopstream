# ShopStream

[![CI](https://github.com/proteanhq/shopstream/actions/workflows/ci.yml/badge.svg)](https://github.com/proteanhq/shopstream/actions/workflows/ci.yml)
![Coverage](https://img.shields.io/endpoint?url=https://gist.githubusercontent.com/subhashb/e80d8bfc7bc87c8165d51ad65f504832/raw/shopstream-coverage.json)

**Version 0.1.0**

E-Commerce Platform built on [Protean](https://github.com/proteanhq/protean) — a Domain-Driven Design framework for Python.

ShopStream implements a multi-domain CQRS architecture with **nine bounded contexts**:

- **Identity** — Customer accounts, profiles, addresses, tiers
- **Catalogue** — Products, variants, categories, pricing
- **Ordering** — Shopping carts and the order lifecycle (event-sourced), checkout
- **Inventory** — Stock levels, reservations, warehouse management (event-sourced)
- **Payments** — Payment processing, refunds, invoices (event-sourced), gateway integration
- **Fulfillment** — Picking, packing, shipping, delivery tracking
- **Reviews** — Product reviews, ratings, moderation, voting, seller replies
- **Notifications** — Multi-channel notifications (email/SMS/push/Slack) + preferences; cross-domain event-consumer hub
- **Loyalty** — Reward accounts, points, tiers, membership cards (CQRS) + event-sourced promo campaigns; also the Protean capability showcase

Commands are processed synchronously via a FastAPI web server. Events flow asynchronously through the outbox pattern and per-domain Redis Streams, with Engine workers maintaining read-model projections. Cross-domain events flow over a shared external Redis bus and are consumed by `@domain.subscriber` (ACL) classes. See [`docs/`](docs/) for the domain narratives, context map, and glossary.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Architecture](#architecture)
- [Running the Platform](#running-the-platform)
- [Project Structure](#project-structure)
- [Testing](#testing)
- [Load Testing](#load-testing)
- [Configuration](#configuration)
- [Available Commands](#available-commands)

## Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) for dependency management
- Docker and Docker Compose for infrastructure services
- Make (optional, for convenience commands)

## Quick Start

```bash
# Install dependencies
make install

# Start infrastructure (PostgreSQL, Message DB, Redis)
make docker-up

# Create database schemas
make setup-db

# Start the API server
make api
```

The API is now available at `http://localhost:8000`. Browse the interactive API docs at **http://localhost:8000/docs** (powered by [Scalar](https://scalar.com)).

```bash
curl -X POST http://localhost:8000/customers \
  -H "Content-Type: application/json" \
  -d '{"external_id":"EXT-1","email":"jane@example.com","first_name":"Jane","last_name":"Doe"}'
```

To process events asynchronously (update projections, etc.), start the Engine workers in separate terminals — one per domain (`make engine-identity`, `engine-catalogue`, `engine-ordering`, `engine-inventory`, `engine-payments`, `engine-fulfillment`, `engine-reviews`, `engine-notifications`, `engine-loyalty`):

```bash
make engine-identity   # Terminal 2
make engine-ordering   # Terminal 3
# … and so on per domain
```

## Architecture

```
  ┌──────────────────────┐          ┌──────────────────────┐
  │  FastAPI Web Server  │          │   PostgreSQL (5432)  │
  │    (port 8000)       │          │  one <domain>_local  │
  │                      │          │  DB per domain       │
  │  /customers /products│─────────▶│  + per-domain        │
  │  /orders /inventory  │ commands │  Outbox Table        │
  │  /payments /reviews… │          └──────────┬───────────┘
  └──────────────────────┘                     │
                                               │ OutboxProcessor
                                               ▼
  ┌──────────────────────┐          ┌──────────────────────┐
  │  Engine Workers      │◀─────────│   Redis Streams      │
  │  (one per domain)    │ consume  │   (port 6379)        │
  │                      │          │   DB 0..8 per domain │
  │  Identity, Catalogue,│          │   DB 15 external bus │
  │  Ordering, Inventory,│          └──────────────────────┘
  │  Payments, Fulfillment,│
  │  Reviews, Notifications,│        ┌──────────────────────┐
  │  Loyalty             │          │   Message DB (5433)  │
  │  - OutboxProcessor   │          │   Event Store        │
  │  - Projector Subs    │          │  (event-sourced aggs)│
  │  - ACL Subscribers   │          └──────────────────────┘
  └──────────────────────┘

  ┌──────────────────────┐
  │ Observatory (:9000)  │
  │  /outbox, /streams   │
  │  /metrics, /health   │
  └──────────────────────┘
```

### Event Flow

1. HTTP request hits the FastAPI server
2. Command handler mutates the aggregate and raises domain events
3. UoW commit writes aggregate state + outbox records **atomically**
4. HTTP response returns to client
5. Engine's OutboxProcessor picks up pending outbox records and publishes to Redis Streams
6. Engine's StreamSubscription reads from Redis, invokes projectors to update read models
7. On failure, messages are retried with exponential backoff, then moved to a DLQ

### Process Model

| Process | Command | Port | Purpose |
|---------|---------|------|---------|
| Web Server | `make api` | 8000 | Synchronous command processing (all domains) |
| Domain Engines | `make engine-<domain>` | — | Async event processing, one per domain: identity, catalogue, ordering, inventory, payments, fulfillment, reviews, notifications, loyalty |
| Observatory | `make observatory` | 9000 | Live message flow dashboard + Prometheus metrics |

## Running the Platform

### 1. Infrastructure

```bash
# Start PostgreSQL, Message DB, and Redis
make docker-up

# Create database tables for all domains
make setup-db
```

### 2. API Server

```bash
make api
```

Starts a FastAPI server on port 8000 with hot-reload. Routes are mapped to domain contexts:

| Route prefix | Domain |
|-------------|--------|
| `/customers/*` | Identity |
| `/products/*`, `/categories/*` | Catalogue |
| `/carts/*`, `/orders/*` | Ordering |
| `/inventory/*`, `/warehouses/*` | Inventory |
| `/payments/*`, `/invoices/*` | Payments |
| `/fulfillments/*` | Fulfillment |
| `/reviews/*` | Reviews |
| `/notifications/*` | Notifications |
| `/loyalty/*` | Loyalty |
| `/health` | — |
| `/docs` | Interactive API reference (Scalar) |
| `/openapi.json` | OpenAPI 3.x spec |

### 3. Engine Workers

Engine workers process events asynchronously. Each engine runs an OutboxProcessor (polls the outbox table, publishes to Redis Streams) and StreamSubscriptions (consume from Redis, invoke projectors).

```bash
# Run the engines together (via Docker Compose)
make docker-dev

# Or run a domain's engine individually (recommended for production)
make engine-identity
make engine-ordering
# … one per domain: engine-<domain>
```

### 4. Observatory

```bash
make observatory
```

Available at `http://localhost:9000` — provides a live message flow dashboard and Prometheus metrics endpoint at `/metrics` for monitoring outbox depth, Redis stream health, and broker statistics across all domains.

### Development Workflow

```bash
# One-command setup: starts Docker + creates schemas
make dev

# Then in separate terminals:
make api               # Terminal 1: web server
make engine-identity   # Terminal 2: a domain worker (one per domain as needed)
make observatory       # Terminal 3: monitoring (optional)
```

## Testing

```bash
# Run all tests (against Postgres/Redis/Message DB)
make test

# Run everything in-memory (no Docker needed)
make test-memory

# With coverage report
make test-cov

# By layer
make test-domain        # Pure business logic (no DB)
make test-application   # Command handler tests (with DB)
make test-integration   # Cross-domain outbox/event tests

# By domain (test-<domain> for any of: identity, catalogue, ordering,
# inventory, payments, fulfillment, reviews, notifications, loyalty)
make test-identity
make test-loyalty

# Fast tests only (skip slow/integration)
make test-fast
```

Tests use `PROTEAN_ENV=test`, which keeps `event_processing = "sync"` so projectors fire during UoW commit for deterministic assertions. Tests run against separate `_test` databases so they never destroy dev data (see [Configuration](#configuration)).

## Load Testing

ShopStream includes a [Locust](https://locust.io)-based load testing suite that simulates realistic e-commerce traffic across all domains. It exercises the full event pipeline — API throughput, outbox processing, Redis Streams publishing, and projector consumption. The table below lists a few representative user classes; see [`loadtests/README.md`](loadtests/README.md) for the full set (per-domain journeys, cross-domain, flash-sale, race-condition, and priority-lane scenarios).

```bash
# Install load testing dependencies
make loadtest-install

# Start the backend (API + engines in Docker)
make docker-dev                # or make docker-dev-scaled for multi-worker engines

# Start the Observatory for monitoring
make observatory               # Terminal 2

# Start Locust web UI
make loadtest                  # Terminal 3 — opens at http://localhost:8089
```

The suite provides 5 user classes covering 6 journey scenarios:

| User Class | Scenarios | Purpose |
|------------|-----------|---------|
| `MixedWorkloadUser` | All 6 journeys, weighted | Realistic cross-domain baseline |
| `IdentityUser` | Customer registration, lifecycle, tiers | Identity domain focus |
| `CatalogueUser` | Product building, lifecycle, categories | Catalogue domain focus |
| `EventFloodUser` | Rapid aggregate creation | Event pipeline saturation |
| `SpikeUser` | Burst registration | Sudden traffic handling |

```bash
# Key commands
make loadtest-mixed            # Mixed workload (web UI)
make loadtest-stress           # Event pipeline stress (web UI)
make loadtest-headless         # CI mode: 50 users, 5 min, CSV + HTML report
make loadtest-spike            # Burst: 100 users, instant spawn, 2 min
make loadtest-stack            # Full stack: Docker + Observatory + Locust
make loadtest-stack-scaled     # Same with 3 identity + 2 catalogue engines
make loadtest-clean            # Truncate all data for a fresh run
```

During testing, monitor three dashboards simultaneously: **Locust** (`:8089`) for request metrics, **Observatory** (`:9000`) for event flow and outbox depth, and **Prometheus** (`:9000/metrics`) for raw counters. See [`loadtests/README.md`](loadtests/README.md) for full documentation.

## Configuration

### Domain Configuration

Each domain has a `domain.toml` in its package directory. Key settings:

```toml
event_processing = "sync"        # Base config (development)
command_processing = "sync"
enable_outbox = true             # Events written to outbox table

[databases.default]
provider = "postgresql"
database_uri = "${DATABASE_URL|postgresql://.../<domain>_local}"

[brokers.default]
provider = "redis"
URI = "redis://127.0.0.1:6379/0"

[event_store]
provider = "message_db"
database_uri = "${MESSAGE_DB_URL|postgresql://...}"

# Test overlay — separate database for tests
[test]
testing = true
[test.databases.default]
database_uri = "${TEST_DATABASE_URL|postgresql://.../<domain>_test}"

# Production overlay
[production]
event_processing = "async"       # Projectors fire via Engine workers
debug = false
[production.databases.default]
database_uri = "${DATABASE_URL|postgresql://.../<domain>}"
```

### Environment Overlays

Protean applies config sections from `domain.toml` based on `PROTEAN_ENV`:

| Environment | DB naming (per domain) | `event_processing` | Projectors fire... |
|-------------|------------------------|-------------------|-------------------|
| _(unset)_ — development | `<domain>_local` | sync | During UoW commit |
| `test` | `<domain>_test` | sync | During UoW commit |
| `memory` | in-memory (no Docker) | sync | During UoW commit |
| `production` | `<domain>` | async | Via Engine workers |

Tests and dev use separate databases so running the test suite never destroys development data.

### Environment Variables

See [.env.example](.env.example) for all variables:

```bash
PROTEAN_ENV=production

# Per-domain database URLs. Identity uses DATABASE_URL / TEST_DATABASE_URL;
# every other domain uses <DOMAIN>_DATABASE_URL / TEST_<DOMAIN>_DATABASE_URL,
# e.g. CATALOGUE_DATABASE_URL, ORDERING_DATABASE_URL, …, LOYALTY_DATABASE_URL.
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/identity_local
CATALOGUE_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/catalogue_local
# … ORDERING_DATABASE_URL, INVENTORY_DATABASE_URL, PAYMENTS_DATABASE_URL,
# … FULFILLMENT_DATABASE_URL, REVIEWS_DATABASE_URL, NOTIFICATIONS_DATABASE_URL, LOYALTY_DATABASE_URL

# Test databases (used when PROTEAN_ENV=test): TEST_<DOMAIN>_DATABASE_URL
TEST_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/identity_test

MESSAGE_DB_URL=postgresql://message_store:message_store@localhost:5433/message_store
REDIS_URL=redis://127.0.0.1:6379/0
SECRET_KEY=change-me-in-production
```

## Available Commands

Run `make help` for the full list.

### API & Workers

```bash
make api                    # FastAPI web server (port 8000)
make engine-<domain>        # Per-domain engine (identity, catalogue, ordering, inventory,
                            #   payments, fulfillment, reviews, notifications, loyalty)
make engine-identity-scaled # Example: identity engine with 4 workers
make observatory            # Observatory dashboard (port 9000)
```

### Database

```bash
make setup-db          # Create all database schemas
make drop-db           # Drop all database schemas
make truncate-db       # Delete all data (preserves schema)
```

### Testing

```bash
make test              # All tests
make test-cov          # Tests with coverage
make test-domain       # Domain layer only
make test-application  # Application layer only
make test-integration  # Integration tests
make test-fast         # Skip slow tests
```

### Code Quality

```bash
make lint              # Ruff linting
make format            # Ruff formatting
make typecheck         # MyPy type checking
make check             # All checks (lint + typecheck + test)
make pre-commit        # Run pre-commit hooks
```

### Docker

```bash
make docker-up         # Start infrastructure services
make docker-dev        # Full stack in Docker (API + engines)
make docker-dev-scaled # Full stack with scaled engines
make docker-down       # Stop services
make docker-logs       # Follow service logs
make docker-clean      # Stop + remove volumes
make dev               # docker-up (infrastructure only)
```

### Load Testing

```bash
make loadtest-install       # Install Locust dependency
make loadtest               # Locust web UI (all scenarios)
make loadtest-mixed         # Mixed workload
make loadtest-stress        # Event pipeline stress
make loadtest-headless      # Headless: 50 users, 5 min, reports
make loadtest-spike         # Spike: 100 users, instant burst
make loadtest-stack         # Full stack + Locust (one command)
make loadtest-stack-scaled  # Same with scaled engines
make loadtest-clean         # Truncate data for fresh run
```
