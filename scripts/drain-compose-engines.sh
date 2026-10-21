#!/usr/bin/env bash
set -uo pipefail

# Drain every running compose engine container before it is stopped.
#
# On SIGTERM, Protean does not run the messages left in a stream batch. They
# stay pending under a consumer name no restarted engine reads again
# (proteanhq/protean#1929). `docker compose stop` and `down` send SIGTERM at
# once, so this POSTs /drainz inside each engine container (every replica of a
# scaled service), then waits for the batches in hand to finish. /drainz gives
# no signal when a batch is done, so the wait is a fixed DRAIN_WAIT seconds.
#
# Usage:
#   ./scripts/drain-compose-engines.sh          # drain, then wait 5 seconds
#   DRAIN_WAIT=10 ./scripts/drain-compose-engines.sh
#
# A container that does not answer gets a warning and does not stop the run,
# so `make docker-down` still tears the stack down.

DRAIN_WAIT="${DRAIN_WAIT:-5}"

health_port() {
    case "$1" in
        engine-identity) echo 8100 ;;
        engine-catalogue) echo 8110 ;;
        engine-ordering) echo 8120 ;;
        engine-inventory) echo 8130 ;;
        engine-payments) echo 8140 ;;
        engine-fulfillment) echo 8150 ;;
        engine-reviews) echo 8160 ;;
        engine-notifications) echo 8170 ;;
        engine-loyalty) echo 8180 ;;
        *) return 1 ;;
    esac
}

drained=0
while IFS=$'\t' read -r service container; do
    port=$(health_port "$service") || continue
    if docker exec "$container" curl -fsS -m 5 -o /dev/null -X POST "http://127.0.0.1:$port/drainz"; then
        echo "[DRAIN] $container draining"
        drained=$((drained + 1))
    else
        echo "[DRAIN] WARNING: $container did not answer POST /drainz on port $port" >&2
    fi
done < <(docker compose ps --status running --format '{{.Service}}	{{.Name}}' 2>/dev/null)

if [ "$drained" -gt 0 ]; then
    echo "[DRAIN] Waiting ${DRAIN_WAIT}s for $drained engine(s) to finish their batches..."
    sleep "$DRAIN_WAIT"
fi
