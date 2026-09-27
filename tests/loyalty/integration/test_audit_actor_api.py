"""API tests for the `X-Actor-Id` header reaching the loyalty audit fields.

These go through the full ShopStream `app`, so the header passes through the real
middleware stack. The actor must be bound inside the domain context that
`DomainContextMiddleware` pushes for the request, or the save cannot see it.
"""

import asyncio

import pytest
from fastapi.testclient import TestClient
from protean import current_domain, g

from loyalty.reward.reward_account import RewardAccount


@pytest.fixture()
def client():
    from app import app

    return TestClient(app)


def _enroll(client, customer_id, headers=None):
    resp = client.post("/loyalty/accounts", json={"customer_id": customer_id}, headers=headers or {})
    assert resp.status_code == 201, resp.text
    return current_domain.repository_for(RewardAccount).get(resp.json()["account_id"])


class TestActorHeader:
    def test_each_request_records_its_own_actor(self, client):
        alice = _enroll(client, "cust-actor-a", {"X-Actor-Id": "alice"})
        bob = _enroll(client, "cust-actor-b", {"X-Actor-Id": "bob"})

        assert (alice.created_by, alice.updated_by) == ("alice", "alice")
        assert (bob.created_by, bob.updated_by) == ("bob", "bob")

    def test_request_without_header_records_system(self, client):
        _enroll(client, "cust-actor-first", {"X-Actor-Id": "alice"})

        account = _enroll(client, "cust-actor-none")

        assert account.created_by == "system"
        assert account.updated_by == "system"

    def test_later_request_changes_updated_by_only(self, client):
        account = _enroll(client, "cust-actor-later", {"X-Actor-Id": "alice"})

        resp = client.post(
            f"/loyalty/accounts/{account.id}/earn",
            json={"amount": 25},
            headers={"X-Actor-Id": "bob"},
        )
        assert resp.status_code == 200, resp.text

        account = current_domain.repository_for(RewardAccount).get(account.id)
        assert account.points_balance == 25
        assert account.created_by == "alice"
        assert account.updated_by == "bob"


class TestActorHeaderCleanup:
    def test_blank_header_records_system(self, client):
        account = _enroll(client, "cust-actor-blank", {"X-Actor-Id": "   "})

        assert account.created_by == "system"

    def test_surrounding_spaces_are_stripped(self, client):
        account = _enroll(client, "cust-actor-spaces", {"X-Actor-Id": "  bob  "})

        assert account.created_by == "bob"

    def test_oversized_header_is_cut_to_the_field_length(self, client):
        account = _enroll(client, "cust-actor-long", {"X-Actor-Id": "a" * 300})

        assert account.created_by == "a" * 255

    def test_header_that_is_not_utf8_is_decoded_with_replacement(self):
        # The test client re-encodes header values, so this drives the middleware with a
        # raw ASGI scope to get bytes that are not valid UTF-8 through to it.
        from app import UserContextMiddleware

        seen = {}

        async def downstream(scope, receive, send):
            seen["actor_id"] = g.actor_id
            seen["user_id"] = g.user_id

        scope = {"type": "http", "headers": [(b"x-actor-id", b"\xffbob"), (b"x-user-id", b"\xfe42")]}
        asyncio.run(UserContextMiddleware(downstream)(scope, None, None))

        assert seen == {"actor_id": "\ufffdbob", "user_id": "\ufffd42"}


class TestUserHeader:
    def test_user_id_reaches_the_event_metadata(self, client):
        account = _enroll(client, "cust-user-meta", {"X-User-Id": "user-42"})

        messages = current_domain.event_store.store.read(f"loyalty::reward_account-{account.id}")

        assert messages
        assert all(message.metadata.extensions.get("user_id") == "user-42" for message in messages)
