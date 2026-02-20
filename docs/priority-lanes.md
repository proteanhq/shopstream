# Priority Lanes — Load Test & Verification Guide

This guide covers how to test and verify Priority Lanes in ShopStream — Protean's prioritized event processing feature that ensures production traffic is never blocked by migration or bulk operations.

## Overview

Priority Lanes routes events to separate Redis Streams based on their processing priority:

- **Primary lane** (`customer`, `order`, etc.) — production traffic, processed immediately
- **Backfill lane** (`customer:backfill`, `order:backfill`, etc.) — migration/bulk traffic, processed only when primary is idle

The Engine's StreamSubscription always drains the primary lane first, ensuring production event processing (projections, read models) is never held hostage by batch jobs.

## Configuration

Enable priority lanes in each domain's `domain.toml`:

```toml
[server.priority_lanes]
enabled = true          # Default: false — opt-in feature
threshold = 0           # Messages with priority < threshold → backfill lane
backfill_suffix = "backfill"  # Stream suffix for the backfill lane
```

ShopStream domains with priority lanes enabled:
- `src/identity/domain.toml`
- `src/catalogue/domain.toml`
- `src/ordering/domain.toml`
- `src/inventory/domain.toml`
- `src/payments/domain.toml`

## Priority Levels

| Priority | Value | Lane | Use Case |
|----------|-------|------|----------|
| `CRITICAL` | 100 | Primary | Payment processing, security events |
| `HIGH` | 50 | Primary | Time-sensitive operations |
| `NORMAL` | 0 | Primary | All production traffic (default) |
| `LOW` | -50 | Backfill | Background tasks, data migrations |
| `BULK` | -100 | Backfill | Bulk imports, re-indexing |

## Automated Load Test Scenarios

All priority lanes load tests are in `loadtests/scenarios/priority_lanes.py`.

### 1. Migration + Production Mixed Workload

**Scenario:** `MigrationWithProductionTrafficUser`

Simulates a migration job (70% of traffic) running alongside live production orders (30%). Migration requests carry the `X-Processing-Priority: low` header.

```bash
# Web UI (interactive)
make loadtest-priority

# Headless (CI mode — 30 users, 3 min)
make loadtest-priority-headless
```

**What to observe:**
- `[PRODUCTION]` tagged requests maintain low latency throughout
- `[MIGRATION]` tagged requests may show higher latency due to backfill routing
- In Observatory: production events appear on `customer` stream, migration events on `customer:backfill`

**Success criteria:**
- Production API p95 latency < 500ms
- Production events processed within 2s of commit
- Migration events eventually processed when production is idle

### 2. Backfill Drain Rate

**Scenario:** `BackfillDrainRateUser`

Seeds 100 migration events in a burst on startup, then generates only light production traffic. Measures how fast the backfill lane drains when production is idle.

```bash
make loadtest-backfill-drain
```

**What to observe:**
- Initial burst fills `customer:backfill` stream
- Backfill drains steadily when production traffic is light
- Observatory shows backfill stream length decreasing over time

### 3. Priority Starvation Test

**Scenario:** `PriorityStarvationTestUser`

Aggressive producer (10 req/sec per user) with 80% production and 20% migration. Verifies that continuous production traffic completely prevents backfill processing.

```bash
make loadtest-starvation
```

**What to observe:**
- `customer:backfill` stream length stays constant or grows during the test
- Production events on the primary stream are processed immediately
- After stopping the test, backfill starts draining

### 4. Baseline Comparison

**Scenario:** `PriorityLanesDisabledBaseline`

Same workload as the migration scenario but without priority headers. All events go through the primary lane. Run this with `priority_lanes.enabled = false` to establish a baseline.

```bash
# First, disable priority lanes in domain.toml, then:
make loadtest-baseline
```

**What to compare (lanes ON vs OFF):**
- Production request p95 latency
- Total event throughput
- Time for all events to be processed

## Manual Test Protocol

For scenarios that benefit from visual observation and step-by-step verification.

### Prerequisites

```bash
# Start infrastructure
make docker-up

# Set up databases
make setup-db

# Ensure priority lanes are enabled in domain.toml files
# (see Configuration section above)
```

### Step 1: Start Services

Open separate terminals for each service:

```bash
# Terminal 1: API server
make api

# Terminal 2: Identity Engine
make engine-identity

# Terminal 3: Ordering Engine
make engine-ordering

# Terminal 4: Observatory
make observatory
```

### Step 2: Seed Migration Data

In a new terminal, run the migration demo script:

```bash
# Create 5000 customers with LOW priority
python scripts/migration_demo.py --count 5000 --priority low
```

### Step 3: Observe Backfill Queue

Open Observatory at http://localhost:9000:

- **Watch:** `customer:backfill` stream should fill up with pending messages
- **Note:** The backfill stream drain rate — events are processed only when the primary stream is empty

### Step 4: Send Production Traffic

While the migration is running (or the backfill is draining), generate production traffic:

```bash
# Terminal 5: Start light production load
make loadtest-headless
```

Or use curl for individual requests:

```bash
# Create a production order (normal priority)
curl -X POST http://localhost:8000/orders \
  -H 'Content-Type: application/json' \
  -d '{
    "customer_id": "prod-customer-1",
    "items": [{"product_id": "p1", "variant_id": "v1", "sku": "TEST-001", "title": "Test Product", "quantity": 1, "unit_price": 29.99}],
    "shipping_address": {"street": "123 Main St", "city": "NYC", "state": "NY", "postal_code": "10001", "country": "US"},
    "billing_address": {"street": "123 Main St", "city": "NYC", "state": "NY", "postal_code": "10001", "country": "US"},
    "shipping_cost": 5.99, "tax_total": 3.00, "discount_total": 0, "currency": "USD"
  }'
```

### Step 5: Verify Priority Ordering

In Observatory, verify:

1. **Production events on primary stream** (`customer`, `order`) are processed **immediately** — near-zero lag
2. **Migration events on backfill stream** (`customer:backfill`) **pause processing** while production events are flowing
3. **After production stops**, backfill processing **resumes**

### Step 6: Baseline Comparison

Disable priority lanes and repeat the test to see the difference:

1. Edit `src/identity/domain.toml` — set `enabled = false` under `[server.priority_lanes]`
2. Restart the Identity Engine
3. Run the migration demo again: `python scripts/migration_demo.py --count 5000 --priority normal`
4. Send production traffic concurrently
5. **Observe:** Production events now wait behind migration events in the FIFO queue — latency increases

### Expected Results Summary

| Metric | Lanes OFF | Lanes ON |
|--------|-----------|----------|
| Production event processing latency | High during migration (500ms+) | Low always (<100ms) |
| Migration completion time | Faster (FIFO) | Slower (yielded to production) |
| Production API p95 latency | Degraded under migration load | Stable |
| Overall throughput | Same | Same (no overhead) |

## Prometheus Metrics

Monitor these metrics in Observatory (http://localhost:9000/metrics):

```
# Outbox queue depth by priority
protean_outbox_messages{status="PENDING", domain="identity"}

# Redis Stream lengths (primary vs backfill)
protean_stream_messages{stream="customer"}
protean_stream_messages{stream="customer:backfill"}

# Processing throughput
protean_stream_processed_total{stream="customer"}
protean_stream_processed_total{stream="customer:backfill"}
```

## Troubleshooting

### Backfill not draining
- Verify `[server.priority_lanes]` is `enabled = true` in domain.toml
- Check that the Engine is running and connected to Redis
- Ensure primary stream is empty (production traffic has stopped)

### Production events going to backfill
- Check that production code does NOT set `processing_priority()` context
- Verify the `X-Processing-Priority` header is not being sent by production clients
- Default priority is NORMAL (0), which routes to the primary lane

### All events going to primary lane
- Verify migration code uses `processing_priority(Priority.LOW)` context manager
- Or passes `priority=Priority.LOW` to `domain.process()`
- Check that `threshold` in config matches your priority values (default: 0)

## Make Targets Reference

```bash
make loadtest-priority            # Migration + production mixed (web UI)
make loadtest-priority-headless   # Same, headless mode (30 users, 3 min)
make loadtest-backfill-drain      # Backfill drain rate measurement
make loadtest-starvation          # Priority starvation verification
make loadtest-baseline            # Lanes-disabled baseline comparison
```
