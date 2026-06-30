"""Integration tests for the Loyalty redemption API endpoints via TestClient.

Processing ``RequestRedemption`` synchronously starts the RedemptionSaga, which reserves
points and advances the redemption to ``points_reserved``; the voucher/complete/compensate
steps run under the loyalty engine (the saga's full logic is unit-tested separately).
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
        assert view["status"] == "points_reserved"
        assert view["points"] == 150

        # The saga's reserve step spent the points on the account.
        account = client.get(f"/loyalty/accounts/{account_id}").json()
        assert account["points_balance"] == 350

    def test_get_unknown_redemption_404(self, client):
        assert client.get("/loyalty/redemptions/does-not-exist").status_code == 404

    def test_non_positive_points_rejected_by_schema(self, client):
        resp = client.post(
            "/loyalty/redemptions",
            json={"account_id": "acc-api-2", "points": 0, "reward_code": "GIFT10"},
        )
        assert resp.status_code == 422  # Pydantic gt=0
