"""BDD tests for review moderation."""

from protean.exceptions import ValidationError
from pytest_bdd import parsers, scenarios, when

scenarios("features/review_moderation.feature")


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
    parsers.cfparse('the review is rejected by moderator "{moderator_id}" with reason "{reason}"'),
    target_fixture="review",
)
def reject_review(review, moderator_id, reason):
    review.reject(moderator_id=moderator_id, reason=reason)
    return review
