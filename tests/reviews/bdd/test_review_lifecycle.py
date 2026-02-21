"""BDD tests for review lifecycle."""

from protean.exceptions import ValidationError
from pytest_bdd import parsers, scenarios, when
from reviews.review.review import Review

scenarios("features/review_lifecycle.feature")


@when(
    parsers.cfparse('a customer submits a review for product "{product_id}" with rating {rating:d}'),
    target_fixture="review",
)
def submit_review(product_id, rating):
    return Review.submit(
        product_id=product_id,
        customer_id="cust-bdd-lc",
        rating=rating,
        title="Lifecycle test review",
        body="This is a lifecycle test review body that is long enough.",
    )


@when(
    parsers.cfparse('the review is approved by moderator "{moderator_id}"'),
    target_fixture="review",
)
def approve_review(review, moderator_id, error):
    try:
        review.approve(moderator_id=moderator_id)
    except ValidationError as exc:
        error["exc"] = exc
    return review


@when(
    parsers.cfparse('the review is removed by "{removed_by}" for reason "{reason}"'),
    target_fixture="review",
)
def remove_review(review, removed_by, reason):
    review.remove(removed_by=removed_by, reason=reason)
    return review


@when(
    parsers.cfparse('the review is rejected by moderator "{moderator_id}" with reason "{reason}"'),
    target_fixture="review",
)
def reject_review(review, moderator_id, reason):
    review.reject(moderator_id=moderator_id, reason=reason)
    return review


@when(
    parsers.cfparse('the review body is edited to "{new_body}"'),
    target_fixture="review",
)
def edit_review_body(review, new_body):
    review.edit(body=new_body)
    return review


@when(
    parsers.cfparse('seller "{seller_id}" replies with "{reply_body}"'),
    target_fixture="review",
)
def seller_replies(review, seller_id, reply_body):
    review.add_seller_reply(seller_id=seller_id, body=reply_body)
    return review
