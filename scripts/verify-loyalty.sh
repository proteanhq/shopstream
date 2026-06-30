#!/usr/bin/env bash
set -euo pipefail

# Loyalty End-to-End Verification Script
#
# Drives the Loyalty HTTP API (/loyalty) against a running ShopStream stack and verifies
# the full CQRS pipeline: commands → outbox → Redis Streams → projectors (RewardAccountView
# DB, PointsLeaderboard cache, CampaignCatalog DB, RedemptionView DB), plus the application
# service (transfer), the active-campaign points multiplier, and the RedemptionSaga.
#
# Prerequisites:
#   make docker-up && make setup-db && make truncate-db
#   make api                # terminal 1 — port 8000
#   make engine-loyalty     # terminal 2 — advances projections + the RedemptionSaga
#
# Usage:
#   ./scripts/verify-loyalty.sh            # full run
#   API_URL=http://host:8000 ./scripts/verify-loyalty.sh

API_URL="${API_URL:-http://localhost:8000}"
# How long to wait for async projections / the saga to catch up (engine-driven).
SETTLE="${SETTLE:-2}"

PASS=0
FAIL=0
FAILURES=()

pass() { PASS=$((PASS + 1)); echo "  [PASS] $1"; }
fail() { FAIL=$((FAIL + 1)); FAILURES+=("$1"); echo "  [FAIL] $1"; }
check() { if [ "$1" -eq 0 ]; then pass "$2"; else fail "$2"; fi; }

section() {
    echo ""
    echo "==========================================="
    echo "  $1"
    echo "==========================================="
}

# Extract a JSON field via python3 (no jq dependency). Usage: jget <json> <key>
jget() { echo "$1" | python3 -c "import json,sys; print(json.load(sys.stdin)['$2'])"; }

# ============================================================
#  Preflight
# ============================================================
section "Preflight"
if ! curl -sf "$API_URL/health" > /dev/null 2>&1; then
    echo "  ERROR: API server not reachable at $API_URL — start it with: make api"
    exit 1
fi
pass "API server reachable"
echo "  NOTE: async projections + the RedemptionSaga require 'make engine-loyalty' running."

# ============================================================
#  Phase 1: Enrol + earn + redeem (RewardAccountView + PointsLeaderboard)
# ============================================================
section "Phase 1: Account, points, projections"

ACC=$(curl -sf -X POST "$API_URL/loyalty/accounts" -H 'Content-Type: application/json' \
    -d '{"customer_id":"verify-cust-1"}')
ACC_ID=$(jget "$ACC" account_id)
check $? "Enrol reward account (POST /loyalty/accounts)"

curl -sf -X POST "$API_URL/loyalty/accounts/$ACC_ID/earn" -H 'Content-Type: application/json' \
    -d '{"amount":300,"reason":"order"}' > /dev/null
check $? "Earn 300 points"

curl -sf -X POST "$API_URL/loyalty/accounts/$ACC_ID/redeem" -H 'Content-Type: application/json' \
    -d '{"amount":100,"reason":"voucher"}' > /dev/null
check $? "Redeem 100 points"

sleep "$SETTLE"
VIEW=$(curl -sf "$API_URL/loyalty/accounts/$ACC_ID")
BAL=$(jget "$VIEW" points_balance)
LIFE=$(jget "$VIEW" lifetime_points)
[ "$BAL" = "200" ]; check $? "RewardAccountView balance == 200 (got $BAL)"
[ "$LIFE" = "300" ]; check $? "RewardAccountView lifetime == 300 (got $LIFE)"

STANDING=$(curl -sf "$API_URL/loyalty/accounts/$ACC_ID/points")
SBAL=$(jget "$STANDING" points_balance)
[ "$SBAL" = "200" ]; check $? "PointsLeaderboard (cache) balance == 200 (got $SBAL)"

# ============================================================
#  Phase 2: Transfer (application service)
# ============================================================
section "Phase 2: Points transfer"

TGT=$(curl -sf -X POST "$API_URL/loyalty/accounts" -H 'Content-Type: application/json' \
    -d '{"customer_id":"verify-cust-2"}')
TGT_ID=$(jget "$TGT" account_id)
RESULT=$(curl -sf -X POST "$API_URL/loyalty/transfers" -H 'Content-Type: application/json' \
    -d "{\"source_account_id\":\"$ACC_ID\",\"target_account_id\":\"$TGT_ID\",\"amount\":50}")
SRC_BAL=$(jget "$RESULT" source_balance)
TGT_BAL=$(jget "$RESULT" target_balance)
[ "$SRC_BAL" = "150" ]; check $? "Transfer source balance == 150 (got $SRC_BAL)"
[ "$TGT_BAL" = "50" ]; check $? "Transfer target balance == 50 (got $TGT_BAL)"

# ============================================================
#  Phase 3: Campaign + active-multiplier on earning
# ============================================================
section "Phase 3: Campaign multiplier"

CAMP=$(curl -sf -X POST "$API_URL/loyalty/campaigns" -H 'Content-Type: application/json' \
    -d '{"campaign_code":"VERIFY2X","name":"Verify Double","discount_type":"points_multiplier","discount_value":2}')
CAMP_ID=$(jget "$CAMP" campaign_id)
check $? "Launch points_multiplier campaign"
curl -sf -X POST "$API_URL/loyalty/campaigns/$CAMP_ID/activate" > /dev/null
check $? "Activate campaign"
sleep "$SETTLE"

MULT_ACC=$(curl -sf -X POST "$API_URL/loyalty/accounts" -H 'Content-Type: application/json' \
    -d '{"customer_id":"verify-cust-mult"}')
MULT_ID=$(jget "$MULT_ACC" account_id)
curl -sf -X POST "$API_URL/loyalty/accounts/$MULT_ID/earn" -H 'Content-Type: application/json' \
    -d '{"amount":100,"reason":"order"}' > /dev/null
sleep "$SETTLE"
MULT_VIEW=$(curl -sf "$API_URL/loyalty/accounts/$MULT_ID")
MULT_BAL=$(jget "$MULT_VIEW" points_balance)
[ "$MULT_BAL" = "200" ]; check $? "Active 2x campaign doubled 100 → 200 (got $MULT_BAL)"

ACTIVE=$(curl -sf "$API_URL/loyalty/campaigns?status=active")
echo "$ACTIVE" | python3 -c "import json,sys; assert any(c['campaign_id']=='$CAMP_ID' for c in json.load(sys.stdin))"
check $? "CampaignCatalog lists the active campaign"

# ============================================================
#  Phase 4: Redemption (RedemptionSaga)
# ============================================================
section "Phase 4: Redemption saga"

RACC=$(curl -sf -X POST "$API_URL/loyalty/accounts" -H 'Content-Type: application/json' \
    -d '{"customer_id":"verify-cust-redeem"}')
RACC_ID=$(jget "$RACC" account_id)
curl -sf -X POST "$API_URL/loyalty/accounts/$RACC_ID/earn" -H 'Content-Type: application/json' \
    -d '{"amount":500,"reason":"order"}' > /dev/null
sleep "$SETTLE"

RED=$(curl -sf -X POST "$API_URL/loyalty/redemptions" -H 'Content-Type: application/json' \
    -d "{\"account_id\":\"$RACC_ID\",\"points\":120,\"reward_code\":\"GIFT25\"}")
RED_ID=$(jget "$RED" redemption_id)
check $? "Request redemption (starts the saga)"
sleep "$SETTLE"
RED_VIEW=$(curl -sf "$API_URL/loyalty/redemptions/$RED_ID")
RED_STATUS=$(jget "$RED_VIEW" status)
case "$RED_STATUS" in
    points_reserved|voucher_issued|completed)
        pass "Redemption progressed (status=$RED_STATUS)" ;;
    *)
        fail "Redemption did not progress (status=$RED_STATUS; is engine-loyalty running?)" ;;
esac

# ============================================================
#  Phase 5: Edge cases / validation
# ============================================================
section "Phase 5: Edge cases"

CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$API_URL/loyalty/accounts/$ACC_ID/redeem" \
    -H 'Content-Type: application/json' -d '{"amount":999999,"reason":"x"}')
[ "$CODE" -ge 400 ] && [ "$CODE" -lt 500 ]; check $? "Over-redemption rejected with 4xx (got $CODE)"

CODE=$(curl -s -o /dev/null -w "%{http_code}" "$API_URL/loyalty/accounts/does-not-exist")
[ "$CODE" = "404" ]; check $? "Unknown account → 404 (got $CODE)"

CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$API_URL/loyalty/accounts/$ACC_ID/earn" \
    -H 'Content-Type: application/json' -d '{"amount":0,"reason":"x"}')
[ "$CODE" = "422" ]; check $? "Non-positive earn rejected with 422 (got $CODE)"

# ============================================================
#  Summary
# ============================================================
section "Summary"
echo "  PASS: $PASS"
echo "  FAIL: $FAIL"
if [ "$FAIL" -gt 0 ]; then
    echo ""
    echo "  Failures:"
    for f in "${FAILURES[@]}"; do echo "    - $f"; done
    exit 1
fi
echo ""
echo "  All loyalty checks passed."
