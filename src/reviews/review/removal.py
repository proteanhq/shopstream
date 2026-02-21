"""RemoveReview — remove a published review.

Reviews can only be removed from Published status. Removal is typically
performed by an admin, the customer, or the system (auto-moderation).
"""

from protean.fields import Identifier, String
from protean.utils.globals import current_domain
from protean.utils.mixins import handle

from reviews.domain import reviews
from reviews.review.review import Review


@reviews.command(part_of="Review")
class RemoveReview:
    review_id = Identifier(required=True)
    removed_by = String(required=True)  # "Customer", "Admin", "System"
    reason = String(required=True)


@reviews.command_handler(part_of=Review)
class RemoveReviewHandler:
    @handle(RemoveReview)
    def remove_review(self, command):
        repo = current_domain.repository_for(Review)
        review = repo.get(command.review_id)

        review.remove(
            removed_by=command.removed_by,
            reason=command.reason,
        )

        repo.add(review)
