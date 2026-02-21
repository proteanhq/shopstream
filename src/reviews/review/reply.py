"""AddSellerReply — add a reply from the product seller to a review.

Only one reply allowed per review, only on published reviews.
"""

from protean.fields import Identifier, Text
from protean.utils.globals import current_domain
from protean.utils.mixins import handle

from reviews.domain import reviews
from reviews.review.review import Review


@reviews.command(part_of="Review")
class AddSellerReply:
    review_id = Identifier(required=True)
    seller_id = Identifier(required=True)
    body = Text(required=True)


@reviews.command_handler(part_of=Review)
class AddSellerReplyHandler:
    @handle(AddSellerReply)
    def add_seller_reply(self, command):
        repo = current_domain.repository_for(Review)
        review = repo.get(command.review_id)

        review.add_seller_reply(
            seller_id=command.seller_id,
            body=command.body,
        )

        repo.add(review)
