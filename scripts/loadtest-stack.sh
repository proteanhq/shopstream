#!/usr/bin/env bash
set -euo pipefail

# ShopStream Load Test Stack
#
# Starts all services needed for load testing and runs Locust.
# Ctrl-C stops everything cleanly via trap.
#
# Usage:
#   ./scripts/loadtest-stack.sh              # Default: 1 engine per domain
#   ./scripts/loadtest-stack.sh --scaled     # Scaled: 3 identity + 2 catalogue engines

SCALED=false
for arg in "$@"; do
    case $arg in
        --scaled) SCALED=true ;;
    esac
done

# Track background PIDs for cleanup
PIDS=()

cleanup() {
    echo ""
    echo "[LOADTEST] Shutting down load test stack..."
    for pid in "${PIDS[@]}"; do
        kill "$pid" 2>/dev/null || true
    done
    docker compose stop api engine-identity engine-catalogue 2>/dev/null || true
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
    echo "[3/5] Starting API + scaled engines (3 identity, 2 catalogue)..."
    docker compose up -d api
    docker compose up -d --scale engine-identity=3 --scale engine-catalogue=2
else
    echo "[3/5] Starting API + engines..."
    docker compose up -d api engine-identity engine-catalogue
fi

sleep 3

# 4. Observatory (runs locally to access both domains)
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
    echo "Mode: SCALED (3 identity + 2 catalogue engine containers)"
else
    echo "Mode: DEFAULT (1 identity + 1 catalogue engine)"
fi
echo ""

# Locust runs in foreground — Ctrl-C stops everything
poetry run locust -f loadtests/locustfile.py --host http://localhost:8000
