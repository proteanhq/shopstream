"""Integration tests for the Loyalty API endpoints via TestClient."""

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


def _enroll(client, customer_id="cust-api-1", **overrides):
    body = {"customer_id": customer_id}
    body.update(overrides)
    resp = client.post("/loyalty/accounts", json=body)
    assert resp.status_code == 201, resp.text
    return resp.json()["account_id"]


class TestLoyaltyWriteEndpoints:
    def test_enroll_returns_account_id(self, client):
        resp = client.post("/loyalty/accounts", json={"customer_id": "cust-1"})
        assert resp.status_code == 201
        assert "account_id" in resp.json()

    def test_earn_then_read_account(self, client):
        account_id = _enroll(client)
        assert client.post(f"/loyalty/accounts/{account_id}/earn", json={"amount": 120}).status_code == 200

        view = client.get(f"/loyalty/accounts/{account_id}").json()
        assert view["points_balance"] == 120
        assert view["lifetime_points"] == 120
        assert view["status"] == "Active"

    def test_redeem_lowers_balance_not_lifetime(self, client):
        account_id = _enroll(client)
        client.post(f"/loyalty/accounts/{account_id}/earn", json={"amount": 120})
        assert client.post(f"/loyalty/accounts/{account_id}/redeem", json={"amount": 50}).status_code == 200

        view = client.get(f"/loyalty/accounts/{account_id}").json()
        assert view["points_balance"] == 70
        assert view["lifetime_points"] == 120

    def test_transfer_between_accounts(self, client):
        source = _enroll(client, customer_id="cust-src")
        client.post(f"/loyalty/accounts/{source}/earn", json={"amount": 100})
        target = _enroll(client, customer_id="cust-tgt")

        resp = client.post(
            "/loyalty/transfers",
            json={"source_account_id": source, "target_account_id": target, "amount": 40},
        )
        assert resp.status_code == 200
        assert resp.json() == {"source_balance": 60, "target_balance": 40}

    def test_redeem_over_balance_is_rejected(self, client):
        account_id = _enroll(client)
        client.post(f"/loyalty/accounts/{account_id}/earn", json={"amount": 30})
        resp = client.post(f"/loyalty/accounts/{account_id}/redeem", json={"amount": 50})
        assert resp.status_code >= 400


class TestLoyaltyReadEndpoints:
    def test_get_unknown_account_404(self, client):
        assert client.get("/loyalty/accounts/does-not-exist").status_code == 404

    def test_points_standing_from_cache_projection(self, client):
        account_id = _enroll(client)
        client.post(f"/loyalty/accounts/{account_id}/earn", json={"amount": 75})

        resp = client.get(f"/loyalty/accounts/{account_id}/points")
        assert resp.status_code == 200
        assert resp.json()["points_balance"] == 75

    def test_earn_non_positive_rejected_by_schema(self, client):
        account_id = _enroll(client)
        resp = client.post(f"/loyalty/accounts/{account_id}/earn", json={"amount": 0})
        assert resp.status_code == 422  # Pydantic gt=0
