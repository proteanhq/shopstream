"""BDD tests for review voting."""

from protean.exceptions import ValidationError
from pytest_bdd import parsers, scenarios, when

scenarios("features/review_voting.feature")


@when(
    parsers.cfparse('customer "{customer_id}" votes "{vote_type}" on the review'),
    target_fixture="review",
)
def vote_on_review(review, customer_id, vote_type, error):
    try:
        review.vote(customer_id=customer_id, vote_type=vote_type)
    except ValidationError as exc:
        error["exc"] = exc
    return review
