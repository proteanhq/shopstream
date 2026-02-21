"""ModerateReview — approve or reject a review.

Moderators can approve pending reviews for publication or reject them
with a required reason.
"""

from protean.exceptions import ValidationError
from protean.fields import Identifier, String
from protean.utils.globals import current_domain
from protean.utils.mixins import handle

from reviews.domain import reviews
from reviews.review.review import ModerationAction, Review


@reviews.command(part_of="Review")
class ModerateReview:
    review_id = Identifier(required=True)
    moderator_id = Identifier(required=True)
    action = String(required=True)  # "Approve" or "Reject"
    reason = String()  # Required for rejection


@reviews.command_handler(part_of=Review)
class ModerateReviewHandler:
    @handle(ModerateReview)
    def moderate_review(self, command):
        repo = current_domain.repository_for(Review)
        review = repo.get(command.review_id)

        action = ModerationAction(command.action)

        if action == ModerationAction.APPROVE:
            review.approve(
                moderator_id=command.moderator_id,
                notes=command.reason,
            )
        else:  # ModerationAction.REJECT
            if not command.reason:
                raise ValidationError({"reason": ["Reason is required when rejecting a review"]})
            review.reject(
                moderator_id=command.moderator_id,
                reason=command.reason,
            )

        repo.add(review)
