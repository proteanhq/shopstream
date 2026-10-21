#!/usr/bin/env bash
set -uo pipefail

# Engine Drain Verification Script
#
# Drains a live Inventory engine with POST /drainz while inventory commands are
# flowing, then stops and restarts it, and checks that the read model reaches
# the counted totals with nothing left pending or dead-lettered:
#
#   1. The script starts its own Inventory engine and waits for /readyz 200.
#   2. It sends a steady stream of `receive 1 unit` commands through the API and
#      counts the ones that succeed (the hand totals).
#   3. Partway through it POSTs /drainz. /readyz must answer 503, the internal
#      Redis stream must keep growing (the outbox still publishes), and the
#      InventoryLevel read model must stop changing.
#   4. After the load ends it sends SIGTERM and times the shutdown, which must
#      finish inside the drain window (`[server] drain_timeout`).
#   5. It restarts the engine. InventoryLevel must reach the hand totals, every
#      Inventory consumer group must have 0 pending entries, and no `:dlq`
#      stream may have grown.
#   6. It sends SIGTERM to the idle engine and times it. An idle engine that
#      takes the whole window has a task that never finishes.
#
# Prerequisites:
#   make docker-up && make setup-db
#   make api                # terminal 1, port 8000
#   No Inventory engine running, local or compose: the script starts and stops
#   its own, and a second one would take messages from it.
#   uv, python3, curl and lsof on PATH.
#   PROTEAN_ENV unset: the store defaults below are the dev ones.
#
# Usage:
#   ./scripts/verify-drain.sh
#   LOAD_SECONDS=20 ./scripts/verify-drain.sh
#   REDIS_URL=... REDIS_EXTERNAL_URL=... INVENTORY_DATABASE_URL=... ./scripts/verify-drain.sh

# The engine command and the config read below expect the repo root.
cd "$(dirname "$0")/.." || exit 1

API_URL="${API_URL:-http://localhost:8000}"
# Inventory's `[server.health] port`. The engine binds it; this does not move it.
HEALTH_PORT="${HEALTH_PORT:-8130}"
HEALTH_URL="http://127.0.0.1:$HEALTH_PORT"
# The same stores the engine reads: `[brokers.default]`, `[brokers.global]` and
# `[databases.default]` in src/inventory/domain.toml, through the same variables.
INTERNAL_REDIS="${REDIS_URL:-redis://127.0.0.1:16379/3}"
GLOBAL_REDIS="${REDIS_EXTERNAL_URL:-redis://127.0.0.1:16379/15}"
PG_URL="${INVENTORY_DATABASE_URL:-postgresql://postgres:postgres@localhost:15432/inventory_local}"
# --no-sync leaves a hand-installed local Protean wheel in place.
ENGINE_CMD=(uv run --frozen --no-sync protean server --domain inventory.domain)
# The project's Python, found once: it has redis and psycopg2, and calling it
# directly skips a `uv run` start on every read.
PY="${PY:-$(uv run --frozen --no-sync python -c 'import sys; print(sys.executable)' 2>/dev/null)}"
ITEMS="${ITEMS:-5}"
LOAD_SECONDS="${LOAD_SECONDS:-12}"
# How long a drained engine gets to finish the batch it was handling.
SETTLE="${SETTLE:-3}"
CURL=(curl -s --max-time 10)

if [ -z "$PY" ] || ! "$PY" -c 'import psycopg2, redis' 2>/dev/null; then
    echo "  ERROR: no project Python with psycopg2 and redis. Run: uv sync --frozen --all-extras --all-groups"
    exit 1
fi
# Whole seconds, rounded up, so a float window still works in shell arithmetic.
DRAIN_TIMEOUT="${DRAIN_TIMEOUT:-$("$PY" -c 'import math, tomllib; print(math.ceil(tomllib.load(open("src/inventory/domain.toml", "rb"))["server"]["drain_timeout"]))')}"
case "$DRAIN_TIMEOUT" in
    ''|*[!0-9]*) echo "  ERROR: could not read [server] drain_timeout from src/inventory/domain.toml"; exit 1 ;;
esac
if [ "$ITEMS" -lt 1 ] || [ "$LOAD_SECONDS" -lt $(( 3 * SETTLE + 3 )) ]; then
    echo "  ERROR: need ITEMS >= 1 and LOAD_SECONDS >= 3 * SETTLE + 3, so the drain lands while the load runs"
    exit 1
fi

PASS=0
FAIL=0
FAILURES=()
RUN_ID="drain-$(date +%s)"
WORK_DIR="$(mktemp -d)"
ENGINE_LOG="$WORK_DIR/engine.log"
# The `uv run` that launched the engine, so cleanup can stop an engine that never got ready.
LAUNCH_PID=""
ENGINE_PID=""
LOAD_PID=""

pass() { PASS=$((PASS + 1)); echo "  [PASS] $1"; }
fail() { FAIL=$((FAIL + 1)); FAILURES+=("$1"); echo "  [FAIL] $1"; }
check() { if [ "$1" -eq 0 ]; then pass "$2"; else fail "$2"; fi; }

section() {
    echo ""
    echo "==========================================="
    echo "  $1"
    echo "==========================================="
}

jget() { echo "$1" | "$PY" -c "import json,sys; print(json.load(sys.stdin)['$2'])" 2>/dev/null; }
code_of() { "${CURL[@]}" -o /dev/null -w "%{http_code}" "$@"; }
now() { "$PY" -c "import time; print(time.monotonic())"; }

cleanup() {
    local pid
    [ -n "$LOAD_PID" ] && kill "$LOAD_PID" 2>/dev/null
    for pid in "$ENGINE_PID" "$LAUNCH_PID"; do
        if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
            kill -TERM "$pid" 2>/dev/null
        fi
    done
    echo ""
    echo "  Engine logs: $WORK_DIR"
}
trap cleanup EXIT

# Runs a Python program read from stdin.
py() { "$PY" - "$@"; }

# on_hand per item in the InventoryLevel table, as `id=on_hand` lines. With
# `--xlen`, a last line with the length of the internal InventoryItem stream,
# read in the same process so the two values are close in time.
read_levels() {
    py "$PG_URL" "$WORK_DIR/items" "$INTERNAL_REDIS" "${1:-}" <<'EOF'
import sys
import psycopg2
import redis
pg_url, items, redis_url, flag = sys.argv[1:5]
ids = open(items, encoding="utf-8").read().split()
with psycopg2.connect(pg_url) as conn, conn.cursor() as cur:
    cur.execute("SELECT inventory_item_id, on_hand FROM inventory_level WHERE inventory_item_id = ANY(%s)", (ids,))
    found = dict(cur.fetchall())
for i in ids:
    print(f"{i}={found.get(i, 'missing')}")
if flag == "--xlen":
    print(redis.Redis.from_url(redis_url).xlen("inventory::inventory_item"))
EOF
}

# `bus stream group pending` for every Inventory consumer group: the groups on
# Inventory's own streams, and the Inventory subscribers' groups on the shared bus.
pending_per_group() {
    py "$INTERNAL_REDIS" "$GLOBAL_REDIS" <<'EOF'
import sys
import redis
for bus, url, streams, groups in (
    ("internal", sys.argv[1], "inventory::*", ""),
    ("global", sys.argv[2], "*", "inventory."),
):
    r = redis.Redis.from_url(url, decode_responses=True)
    for key in r.scan_iter(match=streams, _type="stream"):
        if key.endswith(":dlq"):
            continue
        for group in r.xinfo_groups(key):
            if group["name"].startswith(groups):
                print(f"{bus} {key} {group['name']} {group['pending']}")
EOF
}

# Entries in Inventory's own `:dlq` streams plus every `:dlq` stream on the shared bus.
dlq_entries() {
    py "$INTERNAL_REDIS" "$GLOBAL_REDIS" <<'EOF'
import sys
import redis
total = 0
for url, streams in ((sys.argv[1], "inventory::*:dlq"), (sys.argv[2], "*:dlq")):
    r = redis.Redis.from_url(url)
    total += sum(r.xlen(key) for key in r.scan_iter(match=streams, _type="stream"))
print(total)
EOF
}

# The pid listening on the health port: the engine process itself, not `uv run`.
engine_pid() { lsof -t -nP -iTCP:"$HEALTH_PORT" -sTCP:LISTEN 2>/dev/null | head -1; }

start_engine() {
    ENGINE_PID=""
    "${ENGINE_CMD[@]}" >> "$ENGINE_LOG" 2>&1 &
    LAUNCH_PID=$!
    for _ in $(seq 1 60); do
        kill -0 "$LAUNCH_PID" 2>/dev/null || return 1
        if [ "$(code_of "$HEALTH_URL/readyz")" = "200" ]; then
            ENGINE_PID="$(engine_pid)"
            [ -n "$ENGINE_PID" ]
            return
        fi
        sleep 1
    done
    return 1
}

# Sends SIGTERM to the engine and prints the seconds until it exits, or
# `gone` if it had already exited before the signal.
stop_engine() {
    local start end
    kill -0 "$ENGINE_PID" 2>/dev/null || { echo gone; return; }
    start=$(now)
    kill -TERM "$ENGINE_PID"
    for _ in $(seq 1 $(( (DRAIN_TIMEOUT + 15) * 10 ))); do
        kill -0 "$ENGINE_PID" 2>/dev/null || break
        sleep 0.1
    done
    end=$(now)
    "$PY" -c "print(f'{$end - $start:.1f}')"
}

within_window() { [ "$1" != gone ] && "$PY" -c "import sys; sys.exit(0 if float('$1') < $DRAIN_TIMEOUT else 1)"; }

# A stop that did not finish leaves the engine holding the health port, so the
# next start would bind the port above it. Stop here instead.
require_stopped() {
    if kill -0 "$ENGINE_PID" 2>/dev/null; then
        echo "  ERROR: the engine (pid $ENGINE_PID) is still running $(( DRAIN_TIMEOUT + 15 ))s after SIGTERM. Killing it."
        kill -KILL "$ENGINE_PID" 2>/dev/null
        exit 1
    fi
}

# ============================================================
#  Preflight
# ============================================================
section "Preflight"
if ! "${CURL[@]}" -f "$API_URL/health" > /dev/null 2>&1; then
    echo "  ERROR: API server not reachable at $API_URL. Start it with: make api"
    exit 1
fi
pass "API server reachable"
if ! command -v lsof > /dev/null; then
    echo "  ERROR: lsof is not installed; the script needs it to find the engine's pid."
    exit 1
fi
if [ "$(code_of "$HEALTH_URL/healthz")" != "000" ]; then
    echo "  ERROR: something already answers on $HEALTH_URL. Stop the running Inventory engine first."
    exit 1
fi
pass "No Inventory engine on $HEALTH_URL"

start_engine; check $? "Inventory engine started and /readyz answers 200"
[ -n "$ENGINE_PID" ] || { echo "  ERROR: the engine did not start. See $ENGINE_LOG"; exit 1; }
DLQ_BEFORE=$(dlq_entries)

# ============================================================
#  Phase 1: Seed items, then load
# ============================================================
section "Phase 1: Seed $ITEMS items and send receive commands"

: > "$WORK_DIR/items"
for n in $(seq 1 "$ITEMS"); do
    BODY="{\"product_id\":\"$RUN_ID-p$n\",\"variant_id\":\"$RUN_ID-v$n\",\"warehouse_id\":\"$RUN_ID-w\",\"sku\":\"DRAIN-$n\",\"initial_quantity\":0}"
    RES=$("${CURL[@]}" -f -X POST "$API_URL/inventory" -H 'Content-Type: application/json' -d "$BODY")
    ID=$(jget "$RES" inventory_item_id)
    [ -n "$ID" ] && echo "$ID" >> "$WORK_DIR/items"
done
[ "$(wc -l < "$WORK_DIR/items")" -eq "$ITEMS" ]; check $? "Initialized $ITEMS inventory items"

# One `receive 1` per item per round. Each 200 is one unit the read model must show.
: > "$WORK_DIR/received"
load() {
    local end=$(( $(date +%s) + LOAD_SECONDS )) id
    while [ "$(date +%s)" -lt "$end" ]; do
        while read -r id; do
            if [ "$(code_of -X PUT "$API_URL/inventory/$id/receive" -H 'Content-Type: application/json' -d '{"quantity":1}')" = "200" ]; then
                echo "$id" >> "$WORK_DIR/received"
            fi
        done < "$WORK_DIR/items"
    done
}
load &
LOAD_PID=$!

# ============================================================
#  Phase 2: Drain while the load runs
# ============================================================
section "Phase 2: POST /drainz partway through"

sleep $(( LOAD_SECONDS / 3 ))
DRAIN=$("${CURL[@]}" -X POST "$HEALTH_URL/drainz")
[ "$(jget "$DRAIN" status)" = "draining" ]; check $? "POST /drainz answers status=draining"
[ "$(jget "$DRAIN" pid)" = "$ENGINE_PID" ]; check $? "/drainz pid is the engine's pid ($ENGINE_PID)"

CODE=$(code_of "$HEALTH_URL/readyz")
[ "$CODE" = "503" ]; check $? "/readyz answers 503 while draining (got $CODE)"
CODE=$(code_of "$HEALTH_URL/healthz")
[ "$CODE" = "200" ]; check $? "/healthz still answers 200 (got $CODE)"

sleep "$SETTLE"
SNAPSHOT=$(read_levels --xlen)
LEVELS_AT_DRAIN=$(echo "$SNAPSHOT" | sed '$d')
STREAM_AT_DRAIN=$(echo "$SNAPSHOT" | tail -1)

wait "$LOAD_PID"
LOAD_PID=""
sleep "$SETTLE"
SNAPSHOT=$(read_levels --xlen)
LEVELS_AFTER_LOAD=$(echo "$SNAPSHOT" | sed '$d')
STREAM_AFTER_LOAD=$(echo "$SNAPSHOT" | tail -1)

[ "$STREAM_AFTER_LOAD" -gt "$STREAM_AT_DRAIN" ]
check $? "The outbox kept publishing while draining (stream $STREAM_AT_DRAIN -> $STREAM_AFTER_LOAD entries)"
[ "$LEVELS_AT_DRAIN" = "$LEVELS_AFTER_LOAD" ]
check $? "InventoryLevel stopped changing while draining"

# ============================================================
#  Phase 3: SIGTERM the drained engine
# ============================================================
section "Phase 3: SIGTERM the drained engine, after the load"

DRAINED_SECONDS=$(stop_engine)
[ "$DRAINED_SECONDS" != gone ]; check $? "Drained engine was still running at SIGTERM"
! kill -0 "$ENGINE_PID" 2>/dev/null; check $? "Drained engine exited"
within_window "$DRAINED_SECONDS"; check $? "Drained engine stopped in ${DRAINED_SECONDS}s, inside the ${DRAIN_TIMEOUT}s window"
require_stopped

# ============================================================
#  Phase 4: Restart and catch up
# ============================================================
section "Phase 4: Restart, catch up, compare with the hand totals"

start_engine; check $? "Engine restarted and /readyz answers 200"
[ -n "$ENGINE_PID" ] || { echo "  ERROR: the engine did not restart. See $ENGINE_LOG"; exit 1; }

EXPECTED=$(while read -r id; do echo "$id=$(grep -cx "$id" "$WORK_DIR/received")"; done < "$WORK_DIR/items")
LEVELS=""
for _ in $(seq 1 60); do
    LEVELS=$(read_levels)
    [ "$LEVELS" = "$EXPECTED" ] && break
    sleep 1
done
TOTAL=$(wc -l < "$WORK_DIR/received" | tr -d ' ')
[ "$LEVELS" = "$EXPECTED" ]; check $? "InventoryLevel on_hand matches the hand totals ($TOTAL units across $ITEMS items)"
if [ "$LEVELS" != "$EXPECTED" ]; then
    echo "    expected: $(echo "$EXPECTED" | tr '\n' ' ')"
    echo "    got:      $(echo "$LEVELS" | tr '\n' ' ')"
fi

sleep "$SETTLE"
PENDING=$(pending_per_group)
echo "$PENDING" | sed 's/^/    /'
[ -n "$PENDING" ] && ! echo "$PENDING" | awk '$4 != 0 {bad=1} END {exit !bad}'
check $? "XPENDING is 0 for every Inventory consumer group"
DLQ_AFTER=$(dlq_entries)
[ "$DLQ_AFTER" = "$DLQ_BEFORE" ]; check $? "No message was dead-lettered (DLQ entries $DLQ_BEFORE -> $DLQ_AFTER)"

# ============================================================
#  Phase 5: SIGTERM an idle engine
# ============================================================
section "Phase 5: SIGTERM the idle engine"

IDLE_SECONDS=$(stop_engine)
[ "$IDLE_SECONDS" != gone ]; check $? "Idle engine was still running at SIGTERM"
! kill -0 "$ENGINE_PID" 2>/dev/null; check $? "Idle engine exited"
within_window "$IDLE_SECONDS"; check $? "Idle engine stopped in ${IDLE_SECONDS}s, inside the ${DRAIN_TIMEOUT}s window"
require_stopped

# ============================================================
#  Summary
# ============================================================
section "Summary"
echo "  Shutdown after the drain (load finished): ${DRAINED_SECONDS}s"
echo "  Shutdown when idle:                       ${IDLE_SECONDS}s"
echo "  PASS: $PASS"
echo "  FAIL: $FAIL"
if [ "$FAIL" -gt 0 ]; then
    echo ""
    echo "  Failures:"
    for f in "${FAILURES[@]}"; do echo "    - $f"; done
    exit 1
fi
echo ""
echo "  All drain checks passed."
