"""Integration tests for the Loyalty redemption API endpoints via TestClient.

Processing ``RequestRedemption`` synchronously starts the RedemptionSaga, which reserves
points and records the redemption. Full saga completion needs sync PM cascade
(proteanhq/protean#1048), so the end-to-end completion check is ``xfail`` until that lands.
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from protean.integrations.fastapi import register_exception_handlers

from loyalty.api.routes import loyalty_router


@pytest.fixture()
def client():
    app = FastAPI()
    app.include_router(loyalty_router)
    register_exception_handlers(app)
    return TestClient(app)


def _funded_account(client, customer_id="cust-redeem-api", points=500):
    account_id = client.post("/loyalty/accounts", json={"customer_id": customer_id}).json()["account_id"]
    client.post(f"/loyalty/accounts/{account_id}/earn", json={"amount": points, "reason": "seed"})
    return account_id


class TestRedemptionEndpoints:
    def test_request_starts_saga_and_reserves_points(self, client):
        account_id = _funded_account(client, points=500)
        resp = client.post(
            "/loyalty/redemptions",
            json={"account_id": account_id, "points": 150, "reward_code": "GIFT10"},
        )
        assert resp.status_code == 201, resp.text
        redemption_id = resp.json()["redemption_id"]

        view = client.get(f"/loyalty/redemptions/{redemption_id}").json()
        assert view["points"] == 150
        assert view["status"] in ("requested", "points_reserved")

        # The saga's reserve step spent the points on the account.
        account = client.get(f"/loyalty/accounts/{account_id}").json()
        assert account["points_balance"] == 350

    @pytest.mark.xfail(
        reason="proteanhq/protean#1048 — multi-step process managers don't cascade under "
        "event_processing=sync; the redemption stops before 'completed'. Flip when fixed.",
        strict=True,
    )
    def test_request_drives_saga_to_completion(self, client):
        account_id = _funded_account(client, customer_id="cust-redeem-api-done", points=500)
        resp = client.post(
            "/loyalty/redemptions",
            json={"account_id": account_id, "points": 100, "reward_code": "GIFT10"},
        )
        redemption_id = resp.json()["redemption_id"]
        assert client.get(f"/loyalty/redemptions/{redemption_id}").json()["status"] == "completed"

    def test_get_unknown_redemption_404(self, client):
        assert client.get("/loyalty/redemptions/does-not-exist").status_code == 404

    def test_non_positive_points_rejected_by_schema(self, client):
        resp = client.post(
            "/loyalty/redemptions",
            json={"account_id": "acc-api-2", "points": 0, "reward_code": "GIFT10"},
        )
        assert resp.status_code == 422  # Pydantic gt=0
