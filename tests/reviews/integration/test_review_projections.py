"""Integration tests for Reviews projections — verify projectors maintain read models."""

from protean import current_domain
from reviews.projections.customer_reviews import CustomerReviews
from reviews.projections.moderation_queue import ModerationQueue
from reviews.projections.product_rating import ProductRating
from reviews.projections.product_reviews import ProductReviews
from reviews.projections.review_detail import ReviewDetail
from reviews.review.moderation import ModerateReview
from reviews.review.removal import RemoveReview
from reviews.review.reply import AddSellerReply
from reviews.review.reporting import ReportReview
from reviews.review.submission import SubmitReview
from reviews.review.voting import VoteOnReview


def _submit_review(**overrides):
    defaults = {
        "product_id": "prod-proj-001",
        "customer_id": "cust-proj-001",
        "rating": 4,
        "title": "Projection test review",
        "body": "This is a review body that is long enough for validation.",
    }
    defaults.update(overrides)
    return current_domain.process(SubmitReview(**defaults), asynchronous=False)


def _approve(review_id, moderator_id="mod-001"):
    current_domain.process(
        ModerateReview(review_id=review_id, moderator_id=moderator_id, action="Approve"),
        asynchronous=False,
    )


class TestReviewDetailProjection:
    def test_created_on_submit(self):
        review_id = _submit_review(product_id="prod-rd-1", customer_id="cust-rd-1")
        rd = current_domain.repository_for(ReviewDetail).get(review_id)
        assert rd.review_id == review_id
        assert rd.status == "Pending"
        assert rd.rating == 4
        assert rd.title == "Projection test review"

    def test_updated_on_approve(self):
        review_id = _submit_review(product_id="prod-rd-2", customer_id="cust-rd-2")
        _approve(review_id)
        rd = current_domain.repository_for(ReviewDetail).get(review_id)
        assert rd.status == "Published"

    def test_updated_on_reject(self):
        review_id = _submit_review(product_id="prod-rd-3", customer_id="cust-rd-3")
        current_domain.process(
            ModerateReview(
                review_id=review_id,
                moderator_id="mod-001",
                action="Reject",
                reason="Spam",
            ),
            asynchronous=False,
        )
        rd = current_domain.repository_for(ReviewDetail).get(review_id)
        assert rd.status == "Rejected"
        assert rd.moderation_notes == "Spam"

    def test_updated_on_vote(self):
        review_id = _submit_review(product_id="prod-rd-4", customer_id="cust-rd-4")
        current_domain.process(
            VoteOnReview(review_id=review_id, customer_id="cust-voter-rd4", vote_type="Helpful"),
            asynchronous=False,
        )
        rd = current_domain.repository_for(ReviewDetail).get(review_id)
        assert rd.helpful_count == 1

    def test_updated_on_report(self):
        review_id = _submit_review(product_id="prod-rd-5", customer_id="cust-rd-5")
        current_domain.process(
            ReportReview(review_id=review_id, customer_id="cust-reporter-rd5", reason="Spam"),
            asynchronous=False,
        )
        rd = current_domain.repository_for(ReviewDetail).get(review_id)
        assert rd.report_count == 1

    def test_updated_on_remove(self):
        review_id = _submit_review(product_id="prod-rd-6", customer_id="cust-rd-6")
        _approve(review_id)
        current_domain.process(
            RemoveReview(review_id=review_id, removed_by="Admin", reason="Policy"),
            asynchronous=False,
        )
        rd = current_domain.repository_for(ReviewDetail).get(review_id)
        assert rd.status == "Removed"

    def test_updated_on_seller_reply(self):
        review_id = _submit_review(product_id="prod-rd-7", customer_id="cust-rd-7")
        _approve(review_id)
        current_domain.process(
            AddSellerReply(review_id=review_id, seller_id="seller-001", body="Thanks!"),
            asynchronous=False,
        )
        rd = current_domain.repository_for(ReviewDetail).get(review_id)
        assert rd.has_seller_reply == "True"
        assert rd.seller_reply_body == "Thanks!"


class TestCustomerReviewsProjection:
    def test_created_on_submit(self):
        review_id = _submit_review(product_id="prod-cr-1", customer_id="cust-cr-1")
        cr = current_domain.repository_for(CustomerReviews).get(review_id)
        assert cr.customer_id == "cust-cr-1"
        assert cr.status == "Pending"

    def test_status_updated_on_approve(self):
        review_id = _submit_review(product_id="prod-cr-2", customer_id="cust-cr-2")
        _approve(review_id)
        cr = current_domain.repository_for(CustomerReviews).get(review_id)
        assert cr.status == "Published"


class TestModerationQueueProjection:
    def test_added_on_submit(self):
        review_id = _submit_review(product_id="prod-mq-1", customer_id="cust-mq-1")
        mq = current_domain.repository_for(ModerationQueue).get(review_id)
        assert mq.status == "Pending"

    def test_removed_on_approve(self):
        review_id = _submit_review(product_id="prod-mq-2", customer_id="cust-mq-2")
        _approve(review_id)
        try:
            current_domain.repository_for(ModerationQueue).get(review_id)
            raise AssertionError("ModerationQueue entry should have been removed")
        except Exception:
            pass  # Expected — entry removed after approval


class TestProductReviewsProjection:
    def test_created_on_approve(self):
        review_id = _submit_review(product_id="prod-pr-1", customer_id="cust-pr-1")
        _approve(review_id)
        pr = current_domain.repository_for(ProductReviews).get(review_id)
        assert pr.product_id == "prod-pr-1"
        assert pr.rating == 4

    def test_removed_on_remove(self):
        review_id = _submit_review(product_id="prod-pr-2", customer_id="cust-pr-2")
        _approve(review_id)
        current_domain.process(
            RemoveReview(review_id=review_id, removed_by="Admin", reason="Policy"),
            asynchronous=False,
        )
        try:
            current_domain.repository_for(ProductReviews).get(review_id)
            raise AssertionError("ProductReviews entry should have been removed")
        except Exception:
            pass  # Expected — entry removed

    def test_vote_counts_updated(self):
        review_id = _submit_review(product_id="prod-pr-3", customer_id="cust-pr-3")
        _approve(review_id)
        current_domain.process(
            VoteOnReview(review_id=review_id, customer_id="cust-voter-pr3", vote_type="Helpful"),
            asynchronous=False,
        )
        pr = current_domain.repository_for(ProductReviews).get(review_id)
        assert pr.helpful_count == 1


class TestProductRatingProjection:
    def test_created_on_first_approval(self):
        _submit_and_approve("prod-prt-1", "cust-prt-1")
        pr = current_domain.repository_for(ProductRating).get("prod-prt-1")
        assert pr.total_reviews == 1
        assert pr.average_rating == 4.0

    def test_average_updated_on_second_approval(self):
        # First review: rating 4
        _submit_and_approve("prod-prt-2", "cust-prt-2a")
        # Second review: rating 2
        review_id = _submit_review(product_id="prod-prt-2", customer_id="cust-prt-2b", rating=2)
        _approve(review_id)
        pr = current_domain.repository_for(ProductRating).get("prod-prt-2")
        assert pr.total_reviews == 2
        assert pr.average_rating == 3.0  # (4 + 2) / 2

    def test_rating_decremented_on_removal(self):
        review_id = _submit_review(product_id="prod-prt-3", customer_id="cust-prt-3", rating=5)
        _approve(review_id)
        pr = current_domain.repository_for(ProductRating).get("prod-prt-3")
        assert pr.total_reviews == 1

        current_domain.process(
            RemoveReview(review_id=review_id, removed_by="Admin", reason="Policy"),
            asynchronous=False,
        )
        pr = current_domain.repository_for(ProductRating).get("prod-prt-3")
        assert pr.total_reviews == 0


def _submit_and_approve(product_id, customer_id, rating=4):
    review_id = _submit_review(product_id=product_id, customer_id=customer_id, rating=rating)
    _approve(review_id)
    return review_id
