"""Repository.get_or_none on the Review aggregate: a hit loads child entities, a miss is None."""

from protean import current_domain

from reviews.review.moderation import ModerateReview
from reviews.review.reply import AddSellerReply
from reviews.review.review import Review
from reviews.review.submission import SubmitReview
from reviews.review.voting import VoteOnReview


def _review_with_vote_and_reply():
    review_id = current_domain.process(
        SubmitReview(
            product_id="prod-gon-1",
            customer_id="cust-gon-author",
            rating=5,
            title="Review with children",
            body="This is a review body that is long enough for validation.",
        ),
        asynchronous=False,
    )
    current_domain.process(
        ModerateReview(review_id=review_id, moderator_id="mod-001", action="Approve"),
        asynchronous=False,
    )
    current_domain.process(
        VoteOnReview(review_id=review_id, customer_id="cust-gon-voter", vote_type="Helpful"),
        asynchronous=False,
    )
    current_domain.process(
        AddSellerReply(review_id=review_id, seller_id="seller-gon", body="Thanks for the review!"),
        asynchronous=False,
    )
    return review_id


class TestReviewGetOrNone:
    def test_hit_loads_votes_and_reply(self):
        review_id = _review_with_vote_and_reply()
        repo = current_domain.repository_for(Review)

        review = repo.get_or_none(review_id)

        assert review is not None
        assert str(review.id) == review_id
        assert len(review.votes) == 1
        assert str(review.votes[0].customer_id) == "cust-gon-voter"
        assert review.votes[0].vote_type == "Helpful"
        assert len(review.reply) == 1
        assert review.reply[0].body == "Thanks for the review!"
        assert str(review.reply[0].seller_id) == "seller-gon"

    def test_hit_matches_get(self):
        review_id = _review_with_vote_and_reply()
        repo = current_domain.repository_for(Review)

        via_get_or_none = repo.get_or_none(review_id)
        via_get = repo.get(review_id)

        assert via_get_or_none.to_dict() == via_get.to_dict()

    def test_miss_returns_none(self):
        assert current_domain.repository_for(Review).get_or_none("missing-review-id") is None
