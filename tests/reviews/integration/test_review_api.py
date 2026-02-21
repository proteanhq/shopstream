"""Integration tests for Reviews API endpoints via TestClient."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from protean.integrations.fastapi import register_exception_handlers
from reviews.api.routes import review_router


@pytest.fixture()
def client():
    app = FastAPI()
    app.include_router(review_router)
    register_exception_handlers(app)
    return TestClient(app)


def _submit_review(client, **overrides):
    defaults = {
        "product_id": "prod-api-001",
        "customer_id": "cust-api-001",
        "rating": 4,
        "title": "API Test Review",
        "body": "This is a review body submitted via the API that is long enough.",
    }
    defaults.update(overrides)
    response = client.post("/reviews", json=defaults)
    assert response.status_code == 201
    return response.json()["review_id"]


def _submit_and_approve(client, **overrides):
    review_id = _submit_review(client, **overrides)
    client.put(
        f"/reviews/{review_id}/moderate",
        json={"moderator_id": "mod-001", "action": "Approve"},
    )
    return review_id


class TestSubmitReviewAPI:
    def test_submit_returns_201(self, client):
        response = client.post(
            "/reviews",
            json={
                "product_id": "prod-api-s1",
                "customer_id": "cust-api-s1",
                "rating": 5,
                "title": "Excellent product",
                "body": "I absolutely love this product, it works perfectly!",
            },
        )
        assert response.status_code == 201
        assert "review_id" in response.json()

    def test_submit_with_optional_fields(self, client):
        response = client.post(
            "/reviews",
            json={
                "product_id": "prod-api-s2",
                "customer_id": "cust-api-s2",
                "rating": 4,
                "title": "Good product",
                "body": "Really decent product with nice features overall.",
                "variant_id": "var-001",
                "pros": ["Durable", "Good value"],
                "cons": ["A bit heavy"],
                "images": [{"url": "https://cdn.example.com/img.jpg", "alt_text": "Photo"}],
            },
        )
        assert response.status_code == 201

    def test_submit_duplicate_returns_error(self, client):
        _submit_review(client, product_id="prod-api-dup", customer_id="cust-api-dup")
        response = client.post(
            "/reviews",
            json={
                "product_id": "prod-api-dup",
                "customer_id": "cust-api-dup",
                "rating": 3,
                "title": "Duplicate review",
                "body": "This should fail because duplicate review.",
            },
        )
        assert response.status_code == 400


class TestEditReviewAPI:
    def test_edit_returns_200(self, client):
        review_id = _submit_review(client, product_id="prod-api-e1", customer_id="cust-api-e1")
        response = client.put(
            f"/reviews/{review_id}",
            json={"customer_id": "cust-api-e1", "title": "Updated title"},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    def test_edit_wrong_customer_returns_error(self, client):
        review_id = _submit_review(client, product_id="prod-api-e2", customer_id="cust-api-e2")
        response = client.put(
            f"/reviews/{review_id}",
            json={"customer_id": "cust-wrong", "title": "Hacked"},
        )
        assert response.status_code == 400


class TestModerateReviewAPI:
    def test_approve_returns_200(self, client):
        review_id = _submit_review(client, product_id="prod-api-m1", customer_id="cust-api-m1")
        response = client.put(
            f"/reviews/{review_id}/moderate",
            json={"moderator_id": "mod-001", "action": "Approve"},
        )
        assert response.status_code == 200

    def test_reject_returns_200(self, client):
        review_id = _submit_review(client, product_id="prod-api-m2", customer_id="cust-api-m2")
        response = client.put(
            f"/reviews/{review_id}/moderate",
            json={"moderator_id": "mod-001", "action": "Reject", "reason": "Spam"},
        )
        assert response.status_code == 200

    def test_reject_without_reason_returns_error(self, client):
        review_id = _submit_review(client, product_id="prod-api-m3", customer_id="cust-api-m3")
        response = client.put(
            f"/reviews/{review_id}/moderate",
            json={"moderator_id": "mod-001", "action": "Reject"},
        )
        assert response.status_code == 400


class TestVoteOnReviewAPI:
    def test_vote_returns_201(self, client):
        review_id = _submit_review(client, product_id="prod-api-v1", customer_id="cust-api-v1")
        response = client.post(
            f"/reviews/{review_id}/votes",
            json={"customer_id": "cust-voter-1", "vote_type": "Helpful"},
        )
        assert response.status_code == 201

    def test_self_vote_returns_error(self, client):
        review_id = _submit_review(client, product_id="prod-api-v2", customer_id="cust-api-v2")
        response = client.post(
            f"/reviews/{review_id}/votes",
            json={"customer_id": "cust-api-v2", "vote_type": "Helpful"},
        )
        assert response.status_code == 400


class TestReportReviewAPI:
    def test_report_returns_201(self, client):
        review_id = _submit_review(client, product_id="prod-api-r1", customer_id="cust-api-r1")
        response = client.post(
            f"/reviews/{review_id}/reports",
            json={"customer_id": "cust-reporter-1", "reason": "Spam"},
        )
        assert response.status_code == 201


class TestRemoveReviewAPI:
    def test_remove_published_returns_200(self, client):
        review_id = _submit_and_approve(client, product_id="prod-api-rm1", customer_id="cust-api-rm1")
        response = client.put(
            f"/reviews/{review_id}/remove",
            json={"removed_by": "Admin", "reason": "Policy violation"},
        )
        assert response.status_code == 200

    def test_remove_pending_returns_error(self, client):
        review_id = _submit_review(client, product_id="prod-api-rm2", customer_id="cust-api-rm2")
        response = client.put(
            f"/reviews/{review_id}/remove",
            json={"removed_by": "Admin", "reason": "Policy"},
        )
        assert response.status_code == 400


class TestSellerReplyAPI:
    def test_reply_returns_201(self, client):
        review_id = _submit_and_approve(client, product_id="prod-api-rp1", customer_id="cust-api-rp1")
        response = client.post(
            f"/reviews/{review_id}/reply",
            json={"seller_id": "seller-001", "body": "Thank you!"},
        )
        assert response.status_code == 201

    def test_reply_to_pending_returns_error(self, client):
        review_id = _submit_review(client, product_id="prod-api-rp2", customer_id="cust-api-rp2")
        response = client.post(
            f"/reviews/{review_id}/reply",
            json={"seller_id": "seller-001", "body": "Cannot reply"},
        )
        assert response.status_code == 400
