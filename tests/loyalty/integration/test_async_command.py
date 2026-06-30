"""Integration test for asynchronous command processing (`asynchronous=True`).

`POST /loyalty/accounts/{id}/earn-async` enqueues the EarnPoints command and returns
202 Accepted without waiting for the handler — the only async-command path in ShopStream.
Under the inline (memory) broker the command is processed immediately; under a real broker
(Postgres/Redis test env, dev, prod) the loyalty engine drains the queue. We assert the
202 contract, which holds in either case.
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


class TestAsyncEarn:
    def test_earn_async_returns_202_accepted(self, client):
        account_id = client.post("/loyalty/accounts", json={"customer_id": "cust-async"}).json()["account_id"]

        resp = client.post(f"/loyalty/accounts/{account_id}/earn-async", json={"amount": 100})
        assert resp.status_code == 202
        assert resp.json()["status"] == "accepted"

    def test_earn_async_rejects_non_positive(self, client):
        account_id = client.post("/loyalty/accounts", json={"customer_id": "cust-async-2"}).json()["account_id"]
        resp = client.post(f"/loyalty/accounts/{account_id}/earn-async", json={"amount": 0})
        assert resp.status_code == 422  # Pydantic gt=0, validated before enqueue
