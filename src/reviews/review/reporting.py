"""ReportReview — report a review for moderation.

Cannot report own review. Multiple customers can report the same review.
"""

from protean.fields import Identifier, String
from protean.utils.globals import current_domain
from protean.utils.mixins import handle

from reviews.domain import reviews
from reviews.review.review import Review


@reviews.command(part_of="Review")
class ReportReview:
    review_id = Identifier(required=True)
    customer_id = Identifier(required=True)
    reason = String(required=True)  # ReportReason enum value
    detail = String(max_length=500)


@reviews.command_handler(part_of=Review)
class ReportReviewHandler:
    @handle(ReportReview)
    def report_review(self, command):
        repo = current_domain.repository_for(Review)
        review = repo.get(command.review_id)

        review.report(
            customer_id=command.customer_id,
            reason=command.reason,
            detail=command.detail,
        )

        repo.add(review)
