#!/usr/bin/env bash
set -euo pipefail

# ShopStream Load Test Stack
#
# Starts all services needed for load testing and runs Locust.
# Ctrl-C stops everything cleanly via trap.
#
# Usage:
#   ./scripts/loadtest-stack.sh              # Default: 1 engine per domain
#   ./scripts/loadtest-stack.sh --scaled     # Scaled: 3 identity + 2 catalogue + 2 ordering + 2 inventory + 2 payments engines

SCALED=false
for arg in "$@"; do
    case $arg in
        --scaled) SCALED=true ;;
    esac
done

# All engine services
ALL_ENGINES="engine-identity engine-catalogue engine-ordering engine-inventory engine-payments"

# Track background PIDs for cleanup
PIDS=()

cleanup() {
    echo ""
    echo "[LOADTEST] Shutting down load test stack..."
    # Kill background process groups (not just the shell PID) so child
    # processes like Uvicorn are also terminated immediately.
    for pid in "${PIDS[@]}"; do
        kill -- -"$pid" 2>/dev/null || kill "$pid" 2>/dev/null || true
    done
    # Brief grace period, then force-kill any survivors
    sleep 1
    for pid in "${PIDS[@]}"; do
        kill -9 -- -"$pid" 2>/dev/null || kill -9 "$pid" 2>/dev/null || true
    done
    docker compose stop api $ALL_ENGINES 2>/dev/null || true
    wait 2>/dev/null || true
    echo "[LOADTEST] Done."
}
trap cleanup EXIT SIGINT SIGTERM

echo "=== ShopStream Load Test Stack ==="
echo ""

# 1. Infrastructure
echo "[1/5] Starting infrastructure services..."
make docker-up
sleep 3

# 2. Database setup
echo "[2/5] Setting up databases..."
make setup-db
make truncate-db

# 3. API + Engines via Docker
if [ "$SCALED" = true ]; then
    echo "[3/5] Starting API + scaled engines (3 identity, 2 catalogue, 2 ordering, 2 inventory, 2 payments)..."
    docker compose up -d api
    docker compose up -d \
        --scale engine-identity=3 \
        --scale engine-catalogue=2 \
        --scale engine-ordering=2 \
        --scale engine-inventory=2 \
        --scale engine-payments=2
else
    echo "[3/5] Starting API + engines..."
    docker compose up -d api $ALL_ENGINES
fi

sleep 3

# 4. Observatory (runs locally to access all domains)
echo "[4/5] Starting Observatory on :9000..."
make observatory &
PIDS+=($!)
sleep 2

# 5. Locust
echo "[5/5] Starting Locust on :8089..."
echo ""
echo "Dashboard URLs:"
echo "  Locust:      http://localhost:8089"
echo "  Observatory: http://localhost:9000"
echo "  API Docs:    http://localhost:8000/docs"
echo "  Prometheus:  http://localhost:9000/metrics"
echo ""
if [ "$SCALED" = true ]; then
    echo "Mode: SCALED (3 identity + 2 catalogue + 2 ordering + 2 inventory + 2 payments engine containers)"
else
    echo "Mode: DEFAULT (1 engine per domain)"
fi
echo ""

# Locust runs in foreground — Ctrl-C stops everything
poetry run locust -f loadtests/locustfile.py --host http://localhost:8000
