"""Shared BDD fixtures and step definitions for the Reviews domain."""

import pytest
from protean.exceptions import ValidationError
from pytest_bdd import given, parsers, then
from reviews.review.events import (
    HelpfulVoteRecorded,
    ReviewApproved,
    ReviewEdited,
    ReviewRejected,
    ReviewRemoved,
    ReviewReported,
    ReviewSubmitted,
    SellerReplyAdded,
)
from reviews.review.review import Review

_REVIEW_EVENT_CLASSES = {
    "ReviewSubmitted": ReviewSubmitted,
    "ReviewEdited": ReviewEdited,
    "ReviewApproved": ReviewApproved,
    "ReviewRejected": ReviewRejected,
    "HelpfulVoteRecorded": HelpfulVoteRecorded,
    "ReviewReported": ReviewReported,
    "ReviewRemoved": ReviewRemoved,
    "SellerReplyAdded": SellerReplyAdded,
}


@pytest.fixture()
def error():
    """Container for captured validation errors."""
    return {"exc": None}


# ---------------------------------------------------------------------------
# Given steps
# ---------------------------------------------------------------------------
@given("a pending review", target_fixture="review")
def pending_review():
    review = Review.submit(
        product_id="prod-bdd",
        customer_id="cust-bdd",
        rating=4,
        title="BDD Test Review",
        body="This is a BDD test review body that is long enough.",
    )
    review._events.clear()
    return review


@given(
    parsers.cfparse('a pending review by customer "{customer_id}"'),
    target_fixture="review",
)
def pending_review_by_customer(customer_id):
    review = Review.submit(
        product_id="prod-bdd",
        customer_id=customer_id,
        rating=4,
        title="BDD Test Review",
        body="This is a BDD test review body that is long enough.",
    )
    review._events.clear()
    return review


@given("a published review", target_fixture="review")
def published_review():
    review = Review.submit(
        product_id="prod-bdd-pub",
        customer_id="cust-bdd-pub",
        rating=4,
        title="Published Review",
        body="This is a published review body that is long enough.",
    )
    review._events.clear()
    review.approve(moderator_id="mod-001")
    review._events.clear()
    return review


@given(parsers.cfparse('customer "{customer_id}" has voted "{vote_type}"'))
def customer_has_voted(review, customer_id, vote_type):
    review.vote(customer_id=customer_id, vote_type=vote_type)
    review._events.clear()


# ---------------------------------------------------------------------------
# Then steps
# ---------------------------------------------------------------------------
@then(parsers.cfparse('the review status is "{status}"'))
def review_status_is(review, status):
    assert review.status == status


@then("the review action fails with a validation error")
def review_action_fails(error):
    assert error["exc"] is not None, "Expected a validation error but none was raised"
    assert isinstance(error["exc"], ValidationError)


@then(parsers.cfparse("a {event_type} event is raised"))
def review_event_raised(review, event_type):
    event_cls = _REVIEW_EVENT_CLASSES[event_type]
    assert any(
        isinstance(e, event_cls) for e in review._events
    ), f"No {event_type} event found. Events: {[type(e).__name__ for e in review._events]}"


@then(parsers.cfparse("the review has {count:d} images"))
def review_has_n_images(review, count):
    assert len(review.images) == count


@then("the review has pros and cons")
def review_has_pros_and_cons(review):
    assert review.pros is not None
    assert review.cons is not None


@then(parsers.cfparse("the review helpful count is {count:d}"))
def review_helpful_count(review, count):
    assert review.helpful_count == count


@then("the review is marked as edited")
def review_is_edited(review):
    assert review.is_edited is True


@then("the review has a seller reply")
def review_has_seller_reply(review):
    assert len(review.reply) == 1
