"""EditReview — edit an existing review.

Only the original author can edit, only in PENDING or REJECTED status.
Editing a rejected review re-submits it to moderation (PENDING).
"""

import json

from protean.exceptions import ValidationError
from protean.fields import Identifier, Integer, String, Text
from protean.utils.globals import current_domain
from protean.utils.mixins import handle

from reviews.domain import reviews
from reviews.review.review import Review


@reviews.command(part_of="Review")
class EditReview:
    review_id = Identifier(required=True)
    customer_id = Identifier(required=True)  # Must match original author
    title = String(max_length=200)
    body = Text()
    rating = Integer()
    pros = Text()  # JSON array of strings
    cons = Text()  # JSON array of strings


@reviews.command_handler(part_of=Review)
class EditReviewHandler:
    @handle(EditReview)
    def edit_review(self, command):
        repo = current_domain.repository_for(Review)
        review = repo.get(command.review_id)

        # Verify ownership
        if str(review.customer_id) != str(command.customer_id):
            raise ValidationError({"customer_id": ["Only the review author can edit this review"]})

        # Build kwargs with sentinel for unset fields
        kwargs = {}
        if command.title is not None:
            kwargs["title"] = command.title
        if command.body is not None:
            kwargs["body"] = command.body
        if command.rating is not None:
            kwargs["rating"] = command.rating
        if command.pros is not None:
            kwargs["pros"] = json.loads(command.pros)
        if command.cons is not None:
            kwargs["cons"] = json.loads(command.cons)

        review.edit(**kwargs)
        repo.add(review)
