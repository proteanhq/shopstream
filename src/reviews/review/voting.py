"""VoteOnReview — record a helpful/unhelpful vote on a review.

Cannot vote on own review. Cannot vote twice.
"""

from protean.fields import Identifier, String
from protean.utils.globals import current_domain
from protean.utils.mixins import handle

from reviews.domain import reviews
from reviews.review.review import Review


@reviews.command(part_of="Review")
class VoteOnReview:
    review_id = Identifier(required=True)
    customer_id = Identifier(required=True)
    vote_type = String(required=True)  # "Helpful" or "Unhelpful"


@reviews.command_handler(part_of=Review)
class VoteOnReviewHandler:
    @handle(VoteOnReview)
    def vote_on_review(self, command):
        repo = current_domain.repository_for(Review)
        review = repo.get(command.review_id)

        review.vote(
            customer_id=command.customer_id,
            vote_type=command.vote_type,
        )

        repo.add(review)
