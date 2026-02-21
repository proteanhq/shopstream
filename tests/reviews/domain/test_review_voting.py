"""Tests for Review voting — helpful/unhelpful votes, self-vote guard, duplicate guard."""

import pytest
from protean.exceptions import ValidationError
from reviews.review.review import Review, VoteType


def _make_review(**overrides):
    defaults = {
        "product_id": "prod-001",
        "customer_id": "cust-001",
        "rating": 4,
        "title": "Great product",
        "body": "I really enjoyed this product, it exceeded expectations.",
    }
    defaults.update(overrides)
    return Review.submit(**defaults)


class TestHelpfulVote:
    def test_helpful_vote_increments_count(self):
        review = _make_review()
        review._events.clear()
        review.vote(customer_id="cust-002", vote_type=VoteType.HELPFUL.value)
        assert review.helpful_count == 1
        assert review.unhelpful_count == 0

    def test_unhelpful_vote_increments_count(self):
        review = _make_review()
        review._events.clear()
        review.vote(customer_id="cust-002", vote_type=VoteType.UNHELPFUL.value)
        assert review.unhelpful_count == 1
        assert review.helpful_count == 0

    def test_vote_adds_entity(self):
        review = _make_review()
        review._events.clear()
        review.vote(customer_id="cust-002", vote_type=VoteType.HELPFUL.value)
        assert len(review.votes) == 1
        assert str(review.votes[0].customer_id) == "cust-002"
        assert review.votes[0].vote_type == VoteType.HELPFUL.value

    def test_multiple_voters(self):
        review = _make_review()
        review._events.clear()
        review.vote(customer_id="cust-002", vote_type=VoteType.HELPFUL.value)
        review._events.clear()
        review.vote(customer_id="cust-003", vote_type=VoteType.HELPFUL.value)
        review._events.clear()
        review.vote(customer_id="cust-004", vote_type=VoteType.UNHELPFUL.value)
        assert review.helpful_count == 2
        assert review.unhelpful_count == 1
        assert len(review.votes) == 3

    def test_vote_updates_timestamp(self):
        review = _make_review()
        original = review.updated_at
        review._events.clear()
        review.vote(customer_id="cust-002", vote_type=VoteType.HELPFUL.value)
        assert review.updated_at >= original


class TestVoteRaisesEvent:
    def test_vote_raises_event(self):
        review = _make_review()
        review._events.clear()
        review.vote(customer_id="cust-002", vote_type=VoteType.HELPFUL.value)
        assert len(review._events) == 1
        event = review._events[0]
        assert event.__class__.__name__ == "HelpfulVoteRecorded"
        assert str(event.review_id) == str(review.id)
        assert str(event.voter_id) == "cust-002"
        assert event.vote_type == VoteType.HELPFUL.value
        assert event.helpful_count == 1
        assert event.unhelpful_count == 0


class TestSelfVoteGuard:
    def test_cannot_vote_on_own_review(self):
        review = _make_review()
        review._events.clear()
        with pytest.raises(ValidationError) as exc:
            review.vote(customer_id="cust-001", vote_type=VoteType.HELPFUL.value)
        assert "Cannot vote on your own review" in str(exc.value)


class TestDuplicateVoteGuard:
    def test_cannot_vote_twice(self):
        review = _make_review()
        review._events.clear()
        review.vote(customer_id="cust-002", vote_type=VoteType.HELPFUL.value)
        review._events.clear()

        with pytest.raises(ValidationError) as exc:
            review.vote(customer_id="cust-002", vote_type=VoteType.UNHELPFUL.value)
        assert "already voted" in str(exc.value)

    def test_cannot_vote_same_type_twice(self):
        review = _make_review()
        review._events.clear()
        review.vote(customer_id="cust-002", vote_type=VoteType.HELPFUL.value)
        review._events.clear()

        with pytest.raises(ValidationError) as exc:
            review.vote(customer_id="cust-002", vote_type=VoteType.HELPFUL.value)
        assert "already voted" in str(exc.value)
