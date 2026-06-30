"""Integration tests for the Loyalty campaign API endpoints via TestClient."""

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


def _launch(client, code="SUMMER10", discount_type="percentage", discount_value=10):
    resp = client.post(
        "/loyalty/campaigns",
        json={
            "campaign_code": code,
            "name": "Summer Sale",
            "discount_type": discount_type,
            "discount_value": discount_value,
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["campaign_id"]


class TestCampaignWriteEndpoints:
    def test_launch_returns_campaign_id_and_draft(self, client):
        campaign_id = _launch(client)
        view = client.get(f"/loyalty/campaigns/{campaign_id}").json()
        assert view["status"] == "draft"
        assert view["campaign_code"] == "SUMMER10"

    def test_lifecycle_transitions(self, client):
        campaign_id = _launch(client)
        assert client.post(f"/loyalty/campaigns/{campaign_id}/activate").status_code == 200
        assert client.get(f"/loyalty/campaigns/{campaign_id}").json()["status"] == "active"

        assert client.post(f"/loyalty/campaigns/{campaign_id}/pause", json={"reason": "budget"}).status_code == 200
        assert client.get(f"/loyalty/campaigns/{campaign_id}").json()["status"] == "paused"

        assert client.post(f"/loyalty/campaigns/{campaign_id}/expire").status_code == 200
        assert client.get(f"/loyalty/campaigns/{campaign_id}").json()["status"] == "expired"

    def test_invalid_transition_returns_4xx(self, client):
        campaign_id = _launch(client)  # draft
        resp = client.post(f"/loyalty/campaigns/{campaign_id}/pause", json={})
        assert resp.status_code >= 400

    def test_launch_rejects_non_positive_discount(self, client):
        resp = client.post(
            "/loyalty/campaigns",
            json={"campaign_code": "BAD", "name": "x", "discount_type": "percentage", "discount_value": 0},
        )
        assert resp.status_code == 422  # Pydantic gt=0


class TestCampaignReadEndpoints:
    def test_get_unknown_campaign_404(self, client):
        assert client.get("/loyalty/campaigns/does-not-exist").status_code == 404

    def test_list_filters_by_status(self, client):
        draft_id = _launch(client, code="DRAFTONE")
        active_id = _launch(client, code="ACTIVEONE")
        client.post(f"/loyalty/campaigns/{active_id}/activate")

        active = client.get("/loyalty/campaigns", params={"status": "active"}).json()
        active_ids = {c["campaign_id"] for c in active}
        assert active_id in active_ids
        assert draft_id not in active_ids

        all_campaigns = client.get("/loyalty/campaigns").json()
        all_ids = {c["campaign_id"] for c in all_campaigns}
        assert {draft_id, active_id} <= all_ids


class TestMultiplierThroughApi:
    def _enroll(self, client, customer_id="cust-api-mult"):
        resp = client.post("/loyalty/accounts", json={"customer_id": customer_id})
        assert resp.status_code == 201
        return resp.json()["account_id"]

    def test_active_multiplier_boosts_earnings_via_api(self, client):
        account_id = self._enroll(client)
        campaign_id = _launch(client, code="DOUBLE", discount_type="points_multiplier", discount_value=2)
        client.post(f"/loyalty/campaigns/{campaign_id}/activate")

        client.post(f"/loyalty/accounts/{account_id}/earn", json={"amount": 100})
        view = client.get(f"/loyalty/accounts/{account_id}").json()
        assert view["points_balance"] == 200
