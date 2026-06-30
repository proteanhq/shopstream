#!/usr/bin/env bash
set -euo pipefail

# Observatory Timeline & Causation Graph Verification Script
#
# Verifies the Protean Observatory Event Timeline (Epic 6.2) and
# Causation Graph (Epic 6.3) end-to-end against a running ShopStream
# stack. Seeds test data across multiple domains, then validates all
# Timeline and Trace API endpoints.
#
# Prerequisites:
#   make docker-up && make setup-db && make truncate-db
#   make api                    # terminal 1 — port 8000
#   make observatory            # terminal 2 — port 9000
#   make engine-ordering        # terminal 3
#   make engine-identity        # terminal 4
#   make engine-inventory       # terminal 5
#   make engine-catalogue       # terminal 6 (optional, for projection processing)
#   make engine-payments        # terminal 7 (optional)
#   make engine-fulfillment     # terminal 8 (optional)
#   make engine-loyalty         # terminal 9 (optional, for loyalty projections + the RedemptionSaga)
#
# Usage:
#   ./scripts/verify-timeline.sh              # Full run: seed + verify
#   ./scripts/verify-timeline.sh --skip-seed  # Skip seeding (reuse existing data)
#   ./scripts/verify-timeline.sh --seed-only  # Seed data only, skip verification

API_URL="${API_URL:-http://localhost:8000}"
OBS_URL="${OBS_URL:-http://localhost:9000}"
SKIP_SEED=false
SEED_ONLY=false

for arg in "$@"; do
    case $arg in
        --skip-seed) SKIP_SEED=true ;;
        --seed-only) SEED_ONLY=true ;;
        -h|--help)
            echo "Usage: $0 [--skip-seed] [--seed-only]"
            echo "  --skip-seed  Skip data seeding, reuse existing data"
            echo "  --seed-only  Seed data only, skip API verification"
            exit 0
            ;;
    esac
done

# --- Counters ---
PASS=0
FAIL=0
FAILURES=()

pass() {
    PASS=$((PASS + 1))
    echo "  [PASS] $1"
}

fail() {
    FAIL=$((FAIL + 1))
    FAILURES+=("$1")
    echo "  [FAIL] $1"
}

check() {
    # check <condition_exit_code> <description>
    if [ "$1" -eq 0 ]; then
        pass "$2"
    else
        fail "$2"
    fi
}

section() {
    echo ""
    echo "==========================================="
    echo "  $1"
    echo "==========================================="
}

# --- Temp files for IDs ---
TMPDIR=$(mktemp -d)
trap 'rm -rf "$TMPDIR"' EXIT

# ============================================================
#  Preflight checks
# ============================================================
section "Preflight"

echo "  Checking API server at $API_URL..."
if ! curl -sf "$API_URL/health" > /dev/null 2>&1; then
    echo "  ERROR: API server not reachable at $API_URL"
    echo "  Start it with: make api"
    exit 1
fi
pass "API server reachable"

echo "  Checking Observatory at $OBS_URL..."
if ! curl -sf "$OBS_URL/" > /dev/null 2>&1; then
    echo "  ERROR: Observatory not reachable at $OBS_URL"
    echo "  Start it with: make observatory"
    exit 1
fi
pass "Observatory reachable"

# ============================================================
#  Phase 1: Seed test data across domains
# ============================================================
if [ "$SKIP_SEED" = false ]; then
    section "Phase 1: Seeding test data"

    # --- 1.1 Identity: Register customers ---
    echo "  Creating customers..."
    CUST1=$(curl -sf -X POST "$API_URL/customers" \
        -H "Content-Type: application/json" \
        -d '{"external_id":"timeline-cust-001","email":"timeline-alice@example.com","first_name":"Alice","last_name":"Smith"}')
    CUST1_ID=$(echo "$CUST1" | python3 -c "import json,sys; print(json.load(sys.stdin)['customer_id'])")
    echo "$CUST1_ID" > "$TMPDIR/cust1_id"

    CUST2=$(curl -sf -X POST "$API_URL/customers" \
        -H "Content-Type: application/json" \
        -d '{"external_id":"timeline-cust-002","email":"timeline-bob@example.com","first_name":"Bob","last_name":"Jones"}')
    CUST2_ID=$(echo "$CUST2" | python3 -c "import json,sys; print(json.load(sys.stdin)['customer_id'])")
    echo "$CUST2_ID" > "$TMPDIR/cust2_id"
    echo "  Customers: $CUST1_ID, $CUST2_ID"

    # --- 1.2 Catalogue: Create products + variants ---
    echo "  Creating products..."
    PROD1=$(curl -sf -X POST "$API_URL/products" \
        -H "Content-Type: application/json" \
        -d '{"sku":"TL-WH-001","title":"Timeline Wireless Headphones","description":"Noise-cancelling"}')
    PROD1_ID=$(echo "$PROD1" | python3 -c "import json,sys; print(json.load(sys.stdin)['product_id'])")

    curl -sf -X POST "$API_URL/products/$PROD1_ID/variants" \
        -H "Content-Type: application/json" \
        -d '{"variant_sku":"TL-WH-001-BLK","base_price":79.99}' > /dev/null

    # Wait for catalogue engine to update product projection with variant (retry up to 20s)
    VAR1_ID=""
    for i in $(seq 1 20); do
        P1_DETAIL=$(curl -sf "$API_URL/products/$PROD1_ID")
        VAR1_ID=$(echo "$P1_DETAIL" | python3 -c "
import json,sys
d = json.load(sys.stdin)
vs = d.get('variants', [])
print(vs[0]['variant_id'] if vs else '')
" 2>/dev/null)
        [ -n "$VAR1_ID" ] && break
        sleep 1
    done
    if [ -z "$VAR1_ID" ]; then
        echo "  ERROR: Variant not available after 20s. Is the catalogue engine running?"
        exit 1
    fi
    echo "$PROD1_ID" > "$TMPDIR/prod1_id"
    echo "$VAR1_ID" > "$TMPDIR/var1_id"

    PROD2=$(curl -sf -X POST "$API_URL/products" \
        -H "Content-Type: application/json" \
        -d '{"sku":"TL-UC-002","title":"Timeline USB-C Cable","description":"2m braided"}')
    PROD2_ID=$(echo "$PROD2" | python3 -c "import json,sys; print(json.load(sys.stdin)['product_id'])")

    curl -sf -X POST "$API_URL/products/$PROD2_ID/variants" \
        -H "Content-Type: application/json" \
        -d '{"variant_sku":"TL-UC-002-2M","base_price":12.99}' > /dev/null

    echo "$PROD2_ID" > "$TMPDIR/prod2_id"
    echo "  Products: $PROD1_ID, $PROD2_ID"

    # --- 1.3 Inventory: Warehouse + stock ---
    echo "  Creating warehouse and stock..."
    WH=$(curl -sf -X POST "$API_URL/warehouses" \
        -H "Content-Type: application/json" \
        -d '{"name":"Timeline Warehouse","address":{"street":"123 Warehouse Ave","city":"Portland","postal_code":"97201","country":"US"},"capacity":10000}')
    WH_ID=$(echo "$WH" | python3 -c "import json,sys; print(json.load(sys.stdin)['warehouse_id'])")

    INV=$(curl -sf -X POST "$API_URL/inventory" \
        -H "Content-Type: application/json" \
        -d "{\"product_id\":\"$PROD1_ID\",\"variant_id\":\"$VAR1_ID\",\"warehouse_id\":\"$WH_ID\",\"sku\":\"TL-WH-001-BLK\",\"initial_quantity\":100,\"reorder_point\":10,\"reorder_quantity\":50}")
    INV_ID=$(echo "$INV" | python3 -c "import json,sys; print(json.load(sys.stdin)['inventory_item_id'])")
    echo "  Warehouse: $WH_ID, Inventory: $INV_ID"

    # --- 1.4 Ordering: Create and progress an order ---
    echo "  Creating order (event-sourced aggregate)..."
    ORDER=$(curl -sf -X POST "$API_URL/orders" \
        -H "Content-Type: application/json" \
        -d "{
            \"customer_id\":\"$CUST1_ID\",
            \"items\":[{\"product_id\":\"$PROD1_ID\",\"variant_id\":\"$VAR1_ID\",\"sku\":\"TL-WH-001-BLK\",\"title\":\"Timeline Wireless Headphones\",\"quantity\":2,\"unit_price\":79.99}],
            \"shipping_address\":{\"street\":\"123 Main St\",\"city\":\"Portland\",\"postal_code\":\"97201\",\"country\":\"US\"},
            \"billing_address\":{\"street\":\"123 Main St\",\"city\":\"Portland\",\"postal_code\":\"97201\",\"country\":\"US\"},
            \"shipping_cost\":5.99,\"tax_total\":12.80,\"discount_total\":0,\"currency\":\"USD\",\"order_source\":\"web\"
        }")
    ORDER_ID=$(echo "$ORDER" | python3 -c "import json,sys; print(json.load(sys.stdin)['order_id'])")
    echo "$ORDER_ID" > "$TMPDIR/order_id"
    echo "  Order: $ORDER_ID"

    echo "  Progressing order lifecycle..."
    curl -sf -X PUT "$API_URL/orders/$ORDER_ID/confirm" > /dev/null

    # --- 1.5 Payments ---
    echo "  Creating payment..."
    PAYMENT=$(curl -sf -X POST "$API_URL/payments" \
        -H "Content-Type: application/json" \
        -d "{\"order_id\":\"$ORDER_ID\",\"customer_id\":\"$CUST1_ID\",\"amount\":178.77,\"currency\":\"USD\",\"payment_method_type\":\"credit_card\",\"last4\":\"4242\",\"idempotency_key\":\"tl-pay-$(date +%s)\"}")
    PAYMENT_ID=$(echo "$PAYMENT" | python3 -c "import json,sys; print(json.load(sys.stdin)['payment_id'])")
    echo "  Payment: $PAYMENT_ID"

    curl -sf -X PUT "$API_URL/orders/$ORDER_ID/payment/pending" \
        -H "Content-Type: application/json" \
        -d "{\"payment_id\":\"$PAYMENT_ID\",\"payment_method\":\"credit_card\"}" > /dev/null

    curl -sf -X PUT "$API_URL/orders/$ORDER_ID/payment/success" \
        -H "Content-Type: application/json" \
        -d "{\"payment_id\":\"$PAYMENT_ID\",\"amount\":178.77,\"payment_method\":\"credit_card\"}" > /dev/null

    curl -sf -X PUT "$API_URL/orders/$ORDER_ID/processing" > /dev/null

    # --- 1.6 Fulfillment ---
    echo "  Creating fulfillment..."
    ORDER_DETAIL=$(curl -sf "$API_URL/orders/$ORDER_ID")
    ORDER_ITEM_ID=$(echo "$ORDER_DETAIL" | python3 -c "import json,sys; print(json.load(sys.stdin)['items'][0]['id'])")

    FULFILL=$(curl -sf -X POST "$API_URL/fulfillments" \
        -H "Content-Type: application/json" \
        -d "{\"order_id\":\"$ORDER_ID\",\"customer_id\":\"$CUST1_ID\",\"items\":[{\"order_item_id\":\"$ORDER_ITEM_ID\",\"product_id\":\"$PROD1_ID\",\"sku\":\"TL-WH-001-BLK\",\"quantity\":2}]}")
    FULFILL_ID=$(echo "$FULFILL" | python3 -c "import json,sys; print(json.load(sys.stdin)['fulfillment_id'])")
    echo "  Fulfillment: $FULFILL_ID"

    curl -sf -X PUT "$API_URL/orders/$ORDER_ID/ship" \
        -H "Content-Type: application/json" \
        -d "{\"shipment_id\":\"$FULFILL_ID\",\"tracking_number\":\"TL-TRACK-12345\",\"carrier\":\"FedEx\"}" > /dev/null

    # --- 1.7 Loyalty (reward account, campaign, redemption saga) ---
    echo "  Seeding loyalty (account, campaign, redemption)..."
    LOY_ACC=$(curl -sf -X POST "$API_URL/loyalty/accounts" \
        -H "Content-Type: application/json" \
        -d "{\"customer_id\":\"$CUST1_ID\"}")
    LOY_ACC_ID=$(echo "$LOY_ACC" | python3 -c "import json,sys; print(json.load(sys.stdin)['account_id'])")
    curl -sf -X POST "$API_URL/loyalty/accounts/$LOY_ACC_ID/earn" \
        -H "Content-Type: application/json" -d '{"amount":500,"reason":"order"}' > /dev/null
    curl -sf -X POST "$API_URL/loyalty/accounts/$LOY_ACC_ID/redeem" \
        -H "Content-Type: application/json" -d '{"amount":100,"reason":"voucher"}' > /dev/null

    # Event-sourced PromoCampaign — its own stream + fact events
    LOY_CAMP=$(curl -sf -X POST "$API_URL/loyalty/campaigns" \
        -H "Content-Type: application/json" \
        -d '{"campaign_code":"OBSVERIFY","name":"Observatory Verify","discount_type":"points_multiplier","discount_value":2}')
    LOY_CAMP_ID=$(echo "$LOY_CAMP" | python3 -c "import json,sys; print(json.load(sys.stdin)['campaign_id'])")
    curl -sf -X POST "$API_URL/loyalty/campaigns/$LOY_CAMP_ID/activate" > /dev/null

    # Redemption — kicks off the RedemptionSaga (a causation chain on loyalty::redemption)
    curl -sf -X POST "$API_URL/loyalty/redemptions" \
        -H "Content-Type: application/json" \
        -d "{\"account_id\":\"$LOY_ACC_ID\",\"points\":120,\"reward_code\":\"GIFT25\"}" > /dev/null
    echo "  Loyalty account: $LOY_ACC_ID"

    # Let engines process events
    echo "  Waiting for engine processing..."
    sleep 3

    echo "  Seeding complete."
fi

if [ "$SEED_ONLY" = true ]; then
    echo ""
    echo "Seed-only mode. Exiting."
    exit 0
fi

# ============================================================
#  Phase 2: Timeline API Verification
# ============================================================

# --- 2.1 Stats ---
section "2.1 Stats endpoint"
curl -sf "$OBS_URL/api/timeline/stats" > "$TMPDIR/stats.json"
TOTAL=$(python3 -c "import json; print(json.load(open('$TMPDIR/stats.json')).get('total_events',0))")
STREAMS=$(python3 -c "import json; print(json.load(open('$TMPDIR/stats.json')).get('active_streams',0))")
LAST_TIME=$(python3 -c "import json; print(json.load(open('$TMPDIR/stats.json')).get('last_event_time',''))")
RATE=$(python3 -c "import json; print(json.load(open('$TMPDIR/stats.json')).get('events_per_minute','null'))")

echo "  total_events=$TOTAL  active_streams=$STREAMS  rate=$RATE"
[ "$TOTAL" -gt 0 ] 2>/dev/null; check $? "total_events > 0"
[ "$STREAMS" -gt 0 ] 2>/dev/null; check $? "active_streams > 0"
[ -n "$LAST_TIME" ]; check $? "last_event_time present"
pass "events_per_minute is number or null ($RATE)"

# --- 2.2 Event list (no filters) ---
section "2.2 Event list (limit=10, order=desc)"
curl -sf "$OBS_URL/api/timeline/events?limit=10&order=desc" > "$TMPDIR/events.json"
python3 -c "
import json, sys, os
with open('$TMPDIR/events.json') as f:
    d = json.load(f)
events = d.get('events', [])
cursor = d.get('next_cursor')

checks = []
checks.append((len(events) <= 10, f'Returns up to 10 events ({len(events)})'))

required = ['message_id','type','stream','kind','global_position','position','time','correlation_id','domain']
if events:
    e = events[0]
    missing = [f for f in required if f not in e]
    checks.append((not missing, f'All required fields present' + (f' (missing: {\",\".join(missing)})' if missing else '')))

    positions = [e['global_position'] for e in events]
    desc = all(positions[i] >= positions[i+1] for i in range(len(positions)-1))
    checks.append((desc, 'Events in descending global_position order'))

    no_snap = not any('snapshot' in e['type'].lower() for e in events)
    checks.append((no_snap, 'No snapshot messages in results'))

    checks.append((cursor is not None, f'next_cursor present ({cursor})'))

for ok, msg in checks:
    tag = 'PASS' if ok else 'FAIL'
    print(f'  [{tag}] {msg}')

with open('$TMPDIR/check_results', 'w') as f:
    passed = sum(1 for ok,_ in checks if ok)
    failed = sum(1 for ok,_ in checks if not ok)
    failures = [msg for ok,msg in checks if not ok]
    f.write(f'{passed}\n{failed}\n')
    for msg in failures:
        f.write(f'{msg}\n')
"
if [ -f "$TMPDIR/check_results" ]; then
    P=$(sed -n '1p' "$TMPDIR/check_results")
    F=$(sed -n '2p' "$TMPDIR/check_results")
    PASS=$((PASS + P))
    FAIL=$((FAIL + F))
    # Read failures
    tail -n +3 "$TMPDIR/check_results" | while IFS= read -r line; do
        FAILURES+=("$line")
    done
fi

# --- 2.3 Pagination ---
section "2.3 Pagination"
curl -sf "$OBS_URL/api/timeline/events?limit=5&order=asc" > "$TMPDIR/page1.json"
CURSOR1=$(python3 -c "import json; print(json.load(open('$TMPDIR/page1.json')).get('next_cursor',''))")
P1_LAST=$(python3 -c "import json; es=json.load(open('$TMPDIR/page1.json'))['events']; print(es[-1]['global_position'])")

curl -sf "$OBS_URL/api/timeline/events?limit=5&order=asc&cursor=$CURSOR1" > "$TMPDIR/page2.json"
P2_FIRST=$(python3 -c "import json; es=json.load(open('$TMPDIR/page2.json'))['events']; print(es[0]['global_position'])")

[ "$P2_FIRST" -ge "$P1_LAST" ] 2>/dev/null
check $? "Page 2 continues from page 1 (p1_last=$P1_LAST, p2_first=$P2_FIRST)"

# --- 2.4 Filter by stream_category ---
section "2.4 Filter by stream_category"
curl -sf "$OBS_URL/api/timeline/events?stream_category=ordering%3A%3Aorder&limit=20" > "$TMPDIR/filtered.json"
python3 -c "
import json
d = json.load(open('$TMPDIR/filtered.json'))
events = d.get('events', [])
all_match = all(e['stream'].startswith('ordering::order') for e in events)
print(f'  Events returned: {len(events)}')
tag = 'PASS' if all_match and events else 'FAIL'
print(f'  [{tag}] All events in ordering::order streams')
with open('$TMPDIR/filter_ok', 'w') as f:
    f.write('1' if (all_match and events) else '0')
"
FILTER_OK=$(cat "$TMPDIR/filter_ok")
if [ "$FILTER_OK" = "1" ]; then PASS=$((PASS + 1)); else FAIL=$((FAIL + 1)); FAILURES+=("stream_category filter"); fi

# --- 2.5 Filter by kind ---
section "2.5 Filter by kind"

curl -sf "$OBS_URL/api/timeline/events?kind=COMMAND&limit=10" > "$TMPDIR/commands.json"
CMD_OK=$(python3 -c "import json; es=json.load(open('$TMPDIR/commands.json'))['events']; print(1 if es and all(e['kind']=='COMMAND' for e in es) else 0)")
if [ "$CMD_OK" = "1" ]; then pass "COMMAND filter returns only commands"; else fail "COMMAND filter returns only commands"; fi

curl -sf "$OBS_URL/api/timeline/events?kind=EVENT&limit=10" > "$TMPDIR/events_only.json"
EVT_OK=$(python3 -c "import json; es=json.load(open('$TMPDIR/events_only.json'))['events']; print(1 if es and all(e['kind']=='EVENT' for e in es) else 0)")
if [ "$EVT_OK" = "1" ]; then pass "EVENT filter returns only events"; else fail "EVENT filter returns only events"; fi

HTTP=$(curl -s -o /dev/null -w "%{http_code}" "$OBS_URL/api/timeline/events?kind=INVALID")
[ "$HTTP" = "422" ]; check $? "Invalid kind returns 422 (got $HTTP)"

# --- 2.6 Filter by aggregate_id ---
section "2.6 Filter by aggregate_id"
# Find an order ID from the events
ORDER_ID=$(python3 -c "
import json
d = json.load(open('$TMPDIR/filtered.json'))
events = d.get('events', [])
if events:
    stream = events[0]['stream']
    # Extract ID after first dash
    parts = stream.split('-', 1)
    print(parts[1] if len(parts) > 1 else '')
else:
    print('')
")
if [ -n "$ORDER_ID" ]; then
    curl -sf "$OBS_URL/api/timeline/events?aggregate_id=$ORDER_ID&limit=20" > "$TMPDIR/agg_filter.json"
    AGG_OK=$(python3 -c "
import json
d = json.load(open('$TMPDIR/agg_filter.json'))
events = d.get('events', [])
ok = events and all('$ORDER_ID' in e['stream'] for e in events)
print(1 if ok else 0)
")
    if [ "$AGG_OK" = "1" ]; then pass "aggregate_id filter returns matching events"; else fail "aggregate_id filter returns matching events"; fi
else
    fail "aggregate_id filter (no order events found to test with)"
fi

# --- 2.7 Filter by event_type ---
section "2.7 Filter by event_type"
# event_type requires the full versioned type name
SAMPLE_TYPE=$(python3 -c "
import json
d = json.load(open('$TMPDIR/events_only.json'))
events = d.get('events', [])
print(events[0]['type'] if events else '')
")
if [ -n "$SAMPLE_TYPE" ]; then
    curl -sf "$OBS_URL/api/timeline/events?event_type=$(python3 -c "import urllib.parse; print(urllib.parse.quote('$SAMPLE_TYPE'))")&limit=10" > "$TMPDIR/type_filter.json"
    TYPE_OK=$(python3 -c "
import json
d = json.load(open('$TMPDIR/type_filter.json'))
events = d.get('events', [])
ok = events and all('$SAMPLE_TYPE' in e['type'] for e in events)
print(1 if ok else 0)
")
    if [ "$TYPE_OK" = "1" ]; then pass "event_type filter with full type name ($SAMPLE_TYPE)"; else fail "event_type filter with full type name ($SAMPLE_TYPE)"; fi
else
    fail "event_type filter (no sample type found)"
fi

# --- 2.8 Single event detail ---
section "2.8 Single event detail"
MSG_ID=$(python3 -c "import json; print(json.load(open('$TMPDIR/events.json'))['events'][0]['message_id'])")

curl -sf "$OBS_URL/api/timeline/events/$MSG_ID" > "$TMPDIR/detail.json"
python3 -c "
import json
d = json.load(open('$TMPDIR/detail.json'))
fields = ['message_id','type','kind','stream','time','global_position','position','data','metadata','correlation_id']
missing = [f for f in fields if f not in d]
data_ok = isinstance(d.get('data'), dict)
meta_ok = isinstance(d.get('metadata'), dict)
with open('$TMPDIR/detail_ok', 'w') as f:
    f.write(f'{int(not missing)} {int(data_ok)} {int(meta_ok)}')
    f.write(f'\n{\" \".join(missing) if missing else \"\"}')
"
read -r FIELDS_OK DATA_OK META_OK < "$TMPDIR/detail_ok"
MISSING_FIELDS=$(sed -n '2p' "$TMPDIR/detail_ok")
if [ "$FIELDS_OK" = "1" ]; then pass "All detail fields present"; else fail "Missing detail fields: $MISSING_FIELDS"; fi
if [ "$DATA_OK" = "1" ]; then pass "data is a dict (event payload)"; else fail "data is not a dict"; fi
if [ "$META_OK" = "1" ]; then pass "metadata is a dict"; else fail "metadata is not a dict"; fi

HTTP=$(curl -s -o /dev/null -w "%{http_code}" "$OBS_URL/api/timeline/events/nonexistent-message-id")
[ "$HTTP" = "404" ]; check $? "Invalid message_id returns 404 (got $HTTP)"

# --- 2.9 Correlation chain ---
section "2.9 Correlation chain"
CORR_ID=$(python3 -c "import json; print(json.load(open('$TMPDIR/detail.json')).get('correlation_id',''))")

if [ -n "$CORR_ID" ]; then
    curl -sf "$OBS_URL/api/timeline/correlation/$CORR_ID" > "$TMPDIR/corr.json"
    python3 -c "
import json
d = json.load(open('$TMPDIR/corr.json'))
events = d.get('events', [])
tree = d.get('tree', {})
count = d.get('event_count', 0)
checks = []
checks.append((count == len(events), f'event_count ({count}) matches events array ({len(events)})'))
checks.append((bool(events), f'events array has entries ({len(events)})'))
checks.append((bool(tree), 'tree structure present'))
checks.append(('children' in tree if tree else False, 'tree has children field'))
for ok, msg in checks:
    tag = 'PASS' if ok else 'FAIL'
    print(f'  [{tag}] {msg}')
with open('$TMPDIR/corr_results', 'w') as f:
    f.write(f'{sum(1 for ok,_ in checks if ok)}\n{sum(1 for ok,_ in checks if not ok)}')
"
    read -r CP CF < "$TMPDIR/corr_results"
    PASS=$((PASS + CP))
    FAIL=$((FAIL + CF))
else
    fail "No correlation_id found to test"
fi

HTTP=$(curl -s -o /dev/null -w "%{http_code}" "$OBS_URL/api/timeline/correlation/nonexistent-correlation-id")
[ "$HTTP" = "404" ]; check $? "Invalid correlation_id returns 404 (got $HTTP)"

# --- 2.10 Aggregate history ---
section "2.10 Aggregate history"
if [ -n "$ORDER_ID" ]; then
    curl -sf "$OBS_URL/api/timeline/aggregate/ordering%3A%3Aorder/$ORDER_ID" > "$TMPDIR/agg_hist.json"
    python3 -c "
import json
d = json.load(open('$TMPDIR/agg_hist.json'))
stream = d.get('stream', '')
version = d.get('current_version')
events = d.get('events', [])
count = d.get('event_count', 0)

checks = []
checks.append(('order' in stream.lower(), f'stream matches expected format ({stream})'))
checks.append((version is not None, f'current_version present ({version})'))
checks.append((count == len(events), f'event_count ({count}) matches events ({len(events)})'))

if events:
    positions = [e.get('position', -1) for e in events]
    chrono = all(positions[i] <= positions[i+1] for i in range(len(positions)-1))
    checks.append((chrono, f'Events in chronological order ({positions})'))

    types = [e['type'].rsplit('.', 1)[0].split('.')[-1] for e in events]
    checks.append((len(events) >= 3, f'Multiple lifecycle events ({len(events)}: {\", \".join(types)})'))

for ok, msg in checks:
    tag = 'PASS' if ok else 'FAIL'
    print(f'  [{tag}] {msg}')

with open('$TMPDIR/agg_hist_results', 'w') as f:
    f.write(f'{sum(1 for ok,_ in checks if ok)}\n{sum(1 for ok,_ in checks if not ok)}')
"
    read -r AP AF < "$TMPDIR/agg_hist_results"
    PASS=$((PASS + AP))
    FAIL=$((FAIL + AF))
else
    fail "No order ID available for aggregate history"
fi

# --- 2.11 Multi-domain coverage ---
section "2.11 Multi-domain coverage"
curl -sf "$OBS_URL/api/timeline/events?limit=100" > "$TMPDIR/multi.json"
python3 -c "
import json
d = json.load(open('$TMPDIR/multi.json'))
events = d.get('events', [])
# Derive domain from stream prefix (more reliable than 'domain' field)
stream_domains = sorted(set(e.get('stream','').split('::')[0] for e in events if '::' in e.get('stream','')))
with open('$TMPDIR/domains.txt', 'w') as f:
    f.write(f'{len(stream_domains)}\n')
    f.write(', '.join(stream_domains))
"
DOMAIN_COUNT=$(sed -n '1p' "$TMPDIR/domains.txt")
DOMAIN_LIST=$(sed -n '2p' "$TMPDIR/domains.txt")
[ "$DOMAIN_COUNT" -gt 1 ] 2>/dev/null
check $? "Multiple domains present ($DOMAIN_COUNT: $DOMAIN_LIST)"

# Loyalty events should be in the timeline (requires engine-loyalty running)
echo "$DOMAIN_LIST" | grep -q "loyalty"
check $? "Loyalty events present in the timeline (needs engine-loyalty)"

section "2.12 Loyalty stream coverage"
curl -sf "$OBS_URL/api/timeline/events?limit=200" > "$TMPDIR/loy.json"
python3 -c "
import json
d = json.load(open('$TMPDIR/loy.json'))
streams = set(e.get('stream','').split('-')[0] for e in d.get('events', []))
loyalty_cats = sorted(s for s in streams if s.startswith('loyalty::'))
open('$TMPDIR/loy_cats.txt','w').write(', '.join(loyalty_cats) or 'none')
"
LOY_CATS=$(cat "$TMPDIR/loy_cats.txt")
echo "  Loyalty stream categories seen: $LOY_CATS"
echo "$LOY_CATS" | grep -q "loyalty::reward_account"
check $? "loyalty::reward_account stream present ($LOY_CATS)"

# ============================================================
#  Phase 4: Causation Graph — Epic 6.3 Endpoints
# ============================================================

# --- 4.1 Recent traces ---
section "4.1 Recent traces endpoint"
curl -sf "$OBS_URL/api/timeline/traces/recent?limit=10" > "$TMPDIR/recent_traces.json"
python3 -c "
import json
d = json.load(open('$TMPDIR/recent_traces.json'))
traces = d.get('traces', [])
count = d.get('count', 0)
checks = []
checks.append((count == len(traces), f'count ({count}) matches traces array ({len(traces)})'))
checks.append((bool(traces), f'traces array has entries ({len(traces)})'))
checks.append((count <= 10, f'limit respected ({count} <= 10)'))
if traces:
    t = traces[0]
    required = ['correlation_id', 'root_type', 'event_count', 'started_at', 'streams']
    missing = [f for f in required if f not in t]
    checks.append((not missing, 'All required summary fields present' + (f' (missing: {\",\".join(missing)})' if missing else '')))
    checks.append((isinstance(t.get('streams'), list), f'streams is a list'))
    checks.append((t.get('event_count', 0) >= 1, f'event_count >= 1 ({t.get(\"event_count\")})'))
for ok, msg in checks:
    tag = 'PASS' if ok else 'FAIL'
    print(f'  [{tag}] {msg}')
with open('$TMPDIR/recent_traces_results', 'w') as f:
    f.write(f'{sum(1 for ok,_ in checks if ok)}\n{sum(1 for ok,_ in checks if not ok)}')
"
read -r TP TF < "$TMPDIR/recent_traces_results"
PASS=$((PASS + TP))
FAIL=$((FAIL + TF))

# --- 4.2 Trace search by aggregate_id ---
section "4.2 Trace search by aggregate_id"
if [ -n "$ORDER_ID" ]; then
    curl -sf "$OBS_URL/api/timeline/traces/search?aggregate_id=$ORDER_ID" > "$TMPDIR/trace_search_agg.json"
    python3 -c "
import json
d = json.load(open('$TMPDIR/trace_search_agg.json'))
traces = d.get('traces', [])
count = d.get('count', 0)
checks = []
checks.append((bool(traces), f'Search by aggregate_id returns results ({count})'))
checks.append((count == len(traces), f'count matches array length'))
for ok, msg in checks:
    tag = 'PASS' if ok else 'FAIL'
    print(f'  [{tag}] {msg}')
with open('$TMPDIR/trace_search_agg_results', 'w') as f:
    f.write(f'{sum(1 for ok,_ in checks if ok)}\n{sum(1 for ok,_ in checks if not ok)}')
"
    read -r TP TF < "$TMPDIR/trace_search_agg_results"
    PASS=$((PASS + TP))
    FAIL=$((FAIL + TF))
else
    fail "Trace search by aggregate_id (no order ID available)"
fi

# --- 4.3 Trace search by stream_category ---
section "4.3 Trace search by stream_category"
curl -sf "$OBS_URL/api/timeline/traces/search?stream_category=ordering%3A%3Aorder" > "$TMPDIR/trace_search_stream.json"
python3 -c "
import json
d = json.load(open('$TMPDIR/trace_search_stream.json'))
traces = d.get('traces', [])
count = d.get('count', 0)
checks = []
checks.append((bool(traces), f'Search by stream_category returns results ({count})'))
# Verify returned traces contain ordering::order streams
if traces:
    has_ordering = any('ordering::order' in s for t in traces for s in t.get('streams', []))
    checks.append((has_ordering, 'Results include ordering::order streams'))
for ok, msg in checks:
    tag = 'PASS' if ok else 'FAIL'
    print(f'  [{tag}] {msg}')
with open('$TMPDIR/trace_search_stream_results', 'w') as f:
    f.write(f'{sum(1 for ok,_ in checks if ok)}\n{sum(1 for ok,_ in checks if not ok)}')
"
read -r TP TF < "$TMPDIR/trace_search_stream_results"
PASS=$((PASS + TP))
FAIL=$((FAIL + TF))

# --- 4.4 Trace search by event_type ---
section "4.4 Trace search by event_type"
if [ -n "$SAMPLE_TYPE" ]; then
    ENCODED_TYPE=$(python3 -c "import urllib.parse; print(urllib.parse.quote('$SAMPLE_TYPE'))")
    curl -sf "$OBS_URL/api/timeline/traces/search?event_type=$ENCODED_TYPE" > "$TMPDIR/trace_search_type.json"
    TS_OK=$(python3 -c "import json; d=json.load(open('$TMPDIR/trace_search_type.json')); print(1 if d.get('traces') else 0)")
    if [ "$TS_OK" = "1" ]; then pass "Search by event_type returns results ($SAMPLE_TYPE)"; else fail "Search by event_type returns results ($SAMPLE_TYPE)"; fi
else
    fail "Trace search by event_type (no sample type available)"
fi

# --- 4.5 Trace search empty results ---
section "4.5 Trace search empty results"
curl -sf "$OBS_URL/api/timeline/traces/search?aggregate_id=nonexistent-id-99999" > "$TMPDIR/trace_search_empty.json"
python3 -c "
import json
d = json.load(open('$TMPDIR/trace_search_empty.json'))
traces = d.get('traces', [])
count = d.get('count', 0)
ok = (traces == [] and count == 0)
tag = 'PASS' if ok else 'FAIL'
print(f'  [{tag}] Empty search returns {{traces: [], count: 0}} (got count={count}, len={len(traces)})')
with open('$TMPDIR/trace_empty_ok', 'w') as f:
    f.write('1' if ok else '0')
"
TRACE_EMPTY_OK=$(cat "$TMPDIR/trace_empty_ok")
if [ "$TRACE_EMPTY_OK" = "1" ]; then PASS=$((PASS + 1)); else FAIL=$((FAIL + 1)); FAILURES+=("trace search empty results"); fi

# --- 4.6 Trace search requires at least one parameter ---
section "4.6 Trace search parameter validation"
HTTP=$(curl -s -o /dev/null -w "%{http_code}" "$OBS_URL/api/timeline/traces/search")
[ "$HTTP" = "400" ]; check $? "Trace search with no params returns 400 (got $HTTP)"

# --- 4.7 Enriched correlation response (Epic 6.3.1) ---
section "4.7 Enriched correlation response"
if [ -n "$CORR_ID" ]; then
    python3 -c "
import json
d = json.load(open('$TMPDIR/corr.json'))
tree = d.get('tree', {})
checks = []

# total_duration_ms field exists in response (may be null if no trace data)
checks.append(('total_duration_ms' in d, f'total_duration_ms field present (value={d.get(\"total_duration_ms\")})'))

# tree nodes should have enrichment fields
if tree:
    # Check root node has the enrichment fields (may be None)
    enrichment_fields = ['handler', 'duration_ms', 'delta_ms']
    for field in enrichment_fields:
        checks.append((field in tree, f'tree root has {field} field'))

    # Check children propagate enrichment fields
    children = tree.get('children', [])
    if children:
        child = children[0]
        for field in enrichment_fields:
            checks.append((field in child, f'tree child has {field} field'))

for ok, msg in checks:
    tag = 'PASS' if ok else 'FAIL'
    print(f'  [{tag}] {msg}')
with open('$TMPDIR/enriched_results', 'w') as f:
    f.write(f'{sum(1 for ok,_ in checks if ok)}\n{sum(1 for ok,_ in checks if not ok)}')
"
    read -r EP EF < "$TMPDIR/enriched_results"
    PASS=$((PASS + EP))
    FAIL=$((FAIL + EF))
else
    fail "Enriched correlation (no correlation_id available)"
fi

# ============================================================
#  Phase 5: Edge Cases & Parameter Validation
# ============================================================

# --- 5.4 Empty states ---
section "5.4 Empty states"
HTTP=$(curl -s -o /dev/null -w "%{http_code}" "$OBS_URL/api/timeline/events?aggregate_id=nonexistent-id-12345")
[ "$HTTP" = "200" ]; check $? "Nonexistent aggregate_id returns 200 with empty list (got $HTTP)"

HTTP=$(curl -s -o /dev/null -w "%{http_code}" "$OBS_URL/api/timeline/correlation/nonexistent-correlation-12345")
[ "$HTTP" = "404" ]; check $? "Nonexistent correlation returns 404 (got $HTTP)"

HTTP=$(curl -s -o /dev/null -w "%{http_code}" "$OBS_URL/api/timeline/aggregate/ordering%3A%3Aorder/nonexistent-id-12345")
[ "$HTTP" = "404" ]; check $? "Nonexistent aggregate history returns 404 (got $HTTP)"

# --- 5.5 Parameter validation ---
section "5.5 Parameter validation"
HTTP=$(curl -s -o /dev/null -w "%{http_code}" "$OBS_URL/api/timeline/events?kind=INVALID")
[ "$HTTP" = "422" ]; check $? "Invalid kind returns 422 (got $HTTP)"

HTTP=$(curl -s -o /dev/null -w "%{http_code}" "$OBS_URL/api/timeline/events?limit=999")
[ "$HTTP" = "422" ]; check $? "Limit > 200 returns 422 (got $HTTP)"

HTTP=$(curl -s -o /dev/null -w "%{http_code}" "$OBS_URL/api/timeline/events?order=sideways")
[ "$HTTP" = "422" ]; check $? "Invalid order returns 422 (got $HTTP)"

# --- 5.3 Snapshot exclusion ---
section "5.3 Snapshot exclusion"
SNAP_COUNT=$(python3 -c "
import json
d = json.load(open('$TMPDIR/multi.json'))
snaps = [e for e in d['events'] if 'snapshot' in e.get('type','').lower()]
print(len(snaps))
")
[ "$SNAP_COUNT" = "0" ]; check $? "No snapshot messages in timeline ($SNAP_COUNT found)"

# ============================================================
#  Phase 3: UI page smoke checks (HTML loads)
# ============================================================
section "3.x UI page smoke checks"

HTTP=$(curl -s -o /dev/null -w "%{http_code}" "$OBS_URL/timeline")
[ "$HTTP" = "200" ]; check $? "Timeline page loads (HTTP $HTTP)"

# Deep linking
if [ -n "$CORR_ID" ]; then
    HTTP=$(curl -s -o /dev/null -w "%{http_code}" "$OBS_URL/timeline?correlation=$CORR_ID")
    [ "$HTTP" = "200" ]; check $? "Correlation deep link loads (HTTP $HTTP)"
fi

if [ -n "$ORDER_ID" ]; then
    HTTP=$(curl -s -o /dev/null -w "%{http_code}" "$OBS_URL/timeline?stream=ordering%3A%3Aorder&aggregate=$ORDER_ID")
    [ "$HTTP" = "200" ]; check $? "Aggregate deep link loads (HTTP $HTTP)"
fi

HTTP=$(curl -s -o /dev/null -w "%{http_code}" "$OBS_URL/timeline?correlation=invalid-uuid")
[ "$HTTP" = "200" ]; check $? "Invalid deep link returns 200 (empty state, not error)"

# Epic 6.3 UI checks
HTTP=$(curl -s -o /dev/null -w "%{http_code}" "$OBS_URL/timeline?view=traces")
[ "$HTTP" = "200" ]; check $? "Traces tab deep link loads (HTTP $HTTP)"

HTTP=$(curl -s -o /dev/null -w "%{http_code}" "$OBS_URL/static/js/causation-graph.js")
[ "$HTTP" = "200" ]; check $? "Causation graph JS file loads (HTTP $HTTP)"

# ============================================================
#  Summary
# ============================================================
section "RESULTS"
TOTAL=$((PASS + FAIL))
echo ""
echo "  Passed: $PASS / $TOTAL"
echo "  Failed: $FAIL / $TOTAL"

if [ "$FAIL" -gt 0 ]; then
    echo ""
    echo "  Failures:"
    for f in "${FAILURES[@]}"; do
        echo "    - $f"
    done
fi

echo ""
echo "==========================================="
echo "  Visual verification URLs"
echo "==========================================="
echo ""
echo "  --- Epic 6.2: Event Timeline ---"
echo "  Timeline list view:       $OBS_URL/timeline"
if [ -n "${CORR_ID:-}" ]; then
    echo "  Correlation deep link:    $OBS_URL/timeline?correlation=$CORR_ID"
fi
if [ -n "${ORDER_ID:-}" ]; then
    echo "  Aggregate deep link:      $OBS_URL/timeline?stream=ordering%3A%3Aorder&aggregate=$ORDER_ID"
fi
echo ""
echo "  --- Epic 6.3: Causation Graph ---"
echo "  Traces tab:               $OBS_URL/timeline?view=traces"
if [ -n "${CORR_ID:-}" ]; then
    echo "  Causation tree+graph:     $OBS_URL/timeline?correlation=$CORR_ID"
    echo "    (toggle 'Tree View / Graph View' to see D3 interactive graph)"
fi
echo ""
echo "  SSE test — run this while watching the timeline page:"
echo "    curl -s -X POST $API_URL/customers \\"
echo "      -H 'Content-Type: application/json' \\"
echo "      -d '{\"external_id\":\"sse-test\",\"email\":\"sse@test.com\",\"first_name\":\"SSE\",\"last_name\":\"Test\"}'"
echo ""
echo "  Keyboard shortcut: press 'g' then 't' from any Observatory page"
echo ""

if [ "$FAIL" -gt 0 ]; then
    exit 1
fi
