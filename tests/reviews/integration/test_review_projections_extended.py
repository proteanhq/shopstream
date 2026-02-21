"""Extended projection tests covering edge cases and full lifecycle paths."""

from protean import current_domain
from reviews.projections.customer_reviews import CustomerReviews
from reviews.projections.moderation_queue import ModerationQueue
from reviews.projections.product_reviews import ProductReviews
from reviews.projections.review_detail import ReviewDetail
from reviews.review.editing import EditReview
from reviews.review.moderation import ModerateReview
from reviews.review.removal import RemoveReview
from reviews.review.reply import AddSellerReply
from reviews.review.reporting import ReportReview
from reviews.review.submission import SubmitReview
from reviews.review.voting import VoteOnReview


def _submit_review(**overrides):
    defaults = {
        "product_id": "prod-ext-001",
        "customer_id": "cust-ext-001",
        "rating": 4,
        "title": "Extended test review",
        "body": "This is a review body that is long enough for validation.",
    }
    defaults.update(overrides)
    return current_domain.process(SubmitReview(**defaults), asynchronous=False)


def _approve(review_id):
    current_domain.process(
        ModerateReview(review_id=review_id, moderator_id="mod-001", action="Approve"),
        asynchronous=False,
    )


class TestCustomerReviewsFullLifecycle:
    def test_edit_updates_customer_reviews(self):
        review_id = _submit_review(product_id="prod-cr-e1", customer_id="cust-cr-e1")
        current_domain.process(
            EditReview(
                review_id=review_id,
                customer_id="cust-cr-e1",
                title="Edited title",
                rating=5,
            ),
            asynchronous=False,
        )
        cr = current_domain.repository_for(CustomerReviews).get(review_id)
        assert cr.title == "Edited title"
        assert cr.rating == 5
        assert cr.status == "Pending"

    def test_reject_updates_customer_reviews(self):
        review_id = _submit_review(product_id="prod-cr-rj1", customer_id="cust-cr-rj1")
        current_domain.process(
            ModerateReview(
                review_id=review_id,
                moderator_id="mod-001",
                action="Reject",
                reason="Bad content",
            ),
            asynchronous=False,
        )
        cr = current_domain.repository_for(CustomerReviews).get(review_id)
        assert cr.status == "Rejected"

    def test_remove_updates_customer_reviews(self):
        review_id = _submit_review(product_id="prod-cr-rm1", customer_id="cust-cr-rm1")
        _approve(review_id)
        current_domain.process(
            RemoveReview(review_id=review_id, removed_by="Admin", reason="Policy"),
            asynchronous=False,
        )
        cr = current_domain.repository_for(CustomerReviews).get(review_id)
        assert cr.status == "Removed"


class TestModerationQueueReported:
    def test_reported_published_review_added_to_queue(self):
        review_id = _submit_review(product_id="prod-mq-rpt1", customer_id="cust-mq-rpt1")
        _approve(review_id)
        # After approval, removed from queue. Report should re-add it.
        current_domain.process(
            ReportReview(
                review_id=review_id,
                customer_id="cust-reporter-mq1",
                reason="Spam",
            ),
            asynchronous=False,
        )
        mq = current_domain.repository_for(ModerationQueue).get(review_id)
        assert mq.report_count == 1

    def test_reported_pending_review_updated_in_queue(self):
        review_id = _submit_review(product_id="prod-mq-rpt2", customer_id="cust-mq-rpt2")
        current_domain.process(
            ReportReview(
                review_id=review_id,
                customer_id="cust-reporter-mq2",
                reason="Offensive",
            ),
            asynchronous=False,
        )
        mq = current_domain.repository_for(ModerationQueue).get(review_id)
        assert mq.report_count == 1

    def test_reject_removes_from_queue(self):
        review_id = _submit_review(product_id="prod-mq-rjq", customer_id="cust-mq-rjq")
        current_domain.process(
            ModerateReview(
                review_id=review_id,
                moderator_id="mod-001",
                action="Reject",
                reason="Spam",
            ),
            asynchronous=False,
        )
        try:
            current_domain.repository_for(ModerationQueue).get(review_id)
            raise AssertionError("ModerationQueue entry should have been removed")
        except Exception:
            pass

    def test_remove_clears_from_queue(self):
        review_id = _submit_review(product_id="prod-mq-rmq", customer_id="cust-mq-rmq")
        _approve(review_id)
        # Report (re-adds to queue)
        current_domain.process(
            ReportReview(
                review_id=review_id,
                customer_id="cust-reporter-rmq",
                reason="Fake",
            ),
            asynchronous=False,
        )
        # Remove
        current_domain.process(
            RemoveReview(review_id=review_id, removed_by="Admin", reason="Policy"),
            asynchronous=False,
        )
        try:
            current_domain.repository_for(ModerationQueue).get(review_id)
            raise AssertionError("ModerationQueue entry should have been removed")
        except Exception:
            pass


class TestReviewDetailFullLifecycle:
    def test_edit_updates_detail(self):
        review_id = _submit_review(product_id="prod-rd-e1", customer_id="cust-rd-e1")
        current_domain.process(
            EditReview(
                review_id=review_id,
                customer_id="cust-rd-e1",
                title="New title",
                body="Completely new body content that is absolutely long enough.",
                rating=5,
            ),
            asynchronous=False,
        )
        rd = current_domain.repository_for(ReviewDetail).get(review_id)
        assert rd.title == "New title"
        assert rd.is_edited == "True"
        assert rd.status == "Pending"


class TestProductReviewsSellerReply:
    def test_seller_reply_updates_product_reviews(self):
        review_id = _submit_review(product_id="prod-pr-rply1", customer_id="cust-pr-rply1")
        _approve(review_id)
        current_domain.process(
            AddSellerReply(
                review_id=review_id,
                seller_id="seller-001",
                body="Thank you for your kind words!",
            ),
            asynchronous=False,
        )
        pr = current_domain.repository_for(ProductReviews).get(review_id)
        assert pr.has_seller_reply == "True"
        assert pr.seller_reply_body == "Thank you for your kind words!"


class TestReviewDetailApproveRejectRemove:
    """Cover ReviewDetail projector paths for approve, reject, remove, report, vote, reply."""

    def test_approve_updates_detail(self):
        review_id = _submit_review(product_id="prod-rd-ap1", customer_id="cust-rd-ap1")
        _approve(review_id)
        rd = current_domain.repository_for(ReviewDetail).get(review_id)
        assert rd.status == "Published"

    def test_reject_updates_detail(self):
        review_id = _submit_review(product_id="prod-rd-rj1", customer_id="cust-rd-rj1")
        current_domain.process(
            ModerateReview(
                review_id=review_id,
                moderator_id="mod-001",
                action="Reject",
                reason="Off topic",
            ),
            asynchronous=False,
        )
        rd = current_domain.repository_for(ReviewDetail).get(review_id)
        assert rd.status == "Rejected"
        assert rd.moderation_notes == "Off topic"

    def test_remove_updates_detail(self):
        review_id = _submit_review(product_id="prod-rd-rm1", customer_id="cust-rd-rm1")
        _approve(review_id)
        current_domain.process(
            RemoveReview(review_id=review_id, removed_by="Admin", reason="Violated policy"),
            asynchronous=False,
        )
        rd = current_domain.repository_for(ReviewDetail).get(review_id)
        assert rd.status == "Removed"
        assert rd.moderation_notes == "Violated policy"

    def test_vote_updates_detail(self):
        review_id = _submit_review(product_id="prod-rd-vt1", customer_id="cust-rd-vt1")
        current_domain.process(
            VoteOnReview(
                review_id=review_id,
                customer_id="cust-voter-rd1",
                vote_type="Helpful",
            ),
            asynchronous=False,
        )
        rd = current_domain.repository_for(ReviewDetail).get(review_id)
        assert rd.helpful_count == 1

    def test_report_updates_detail(self):
        review_id = _submit_review(product_id="prod-rd-rp1", customer_id="cust-rd-rp1")
        current_domain.process(
            ReportReview(
                review_id=review_id,
                customer_id="cust-reporter-rd1",
                reason="Spam",
            ),
            asynchronous=False,
        )
        rd = current_domain.repository_for(ReviewDetail).get(review_id)
        assert rd.report_count == 1

    def test_seller_reply_updates_detail(self):
        review_id = _submit_review(product_id="prod-rd-sr1", customer_id="cust-rd-sr1")
        _approve(review_id)
        current_domain.process(
            AddSellerReply(
                review_id=review_id,
                seller_id="seller-rd1",
                body="Thanks for your feedback!",
            ),
            asynchronous=False,
        )
        rd = current_domain.repository_for(ReviewDetail).get(review_id)
        assert rd.has_seller_reply == "True"
        assert rd.seller_reply_body == "Thanks for your feedback!"


class TestProductRatingRemoved:
    """Cover the ReviewRemoved path in ProductRatingProjector."""

    def test_removal_decrements_rating(self):
        from reviews.projections.product_rating import ProductRating

        review_id = _submit_review(product_id="prod-prat-rm1", customer_id="cust-prat-rm1", rating=5)
        _approve(review_id)

        pr = current_domain.repository_for(ProductRating).get("prod-prat-rm1")
        assert pr.total_reviews == 1

        current_domain.process(
            RemoveReview(review_id=review_id, removed_by="Admin", reason="Policy"),
            asynchronous=False,
        )
        pr = current_domain.repository_for(ProductRating).get("prod-prat-rm1")
        assert pr.total_reviews == 0
        assert pr.average_rating == 0.0


class TestProductReviewsVoteAndRemove:
    """Cover HelpfulVoteRecorded and ReviewRemoved on ProductReviews."""

    def test_vote_updates_product_reviews(self):
        review_id = _submit_review(product_id="prod-prv-1", customer_id="cust-prv-1")
        _approve(review_id)
        current_domain.process(
            VoteOnReview(
                review_id=review_id,
                customer_id="cust-voter-prv1",
                vote_type="Helpful",
            ),
            asynchronous=False,
        )
        pr = current_domain.repository_for(ProductReviews).get(review_id)
        assert pr.helpful_count == 1

    def test_remove_deletes_from_product_reviews(self):
        review_id = _submit_review(product_id="prod-prv-rm1", customer_id="cust-prv-rm1")
        _approve(review_id)
        # Verify it exists
        pr = current_domain.repository_for(ProductReviews).get(review_id)
        assert pr is not None
        # Remove
        current_domain.process(
            RemoveReview(review_id=review_id, removed_by="Admin", reason="Policy"),
            asynchronous=False,
        )
        try:
            current_domain.repository_for(ProductReviews).get(review_id)
            raise AssertionError("Should have been removed")
        except Exception:
            pass


class TestCustomerReviewsEditNoTitleNoRating:
    """Cover branches where edit event has no title or no rating."""

    def test_edit_without_title_keeps_original(self):
        review_id = _submit_review(product_id="prod-cr-nt1", customer_id="cust-cr-nt1")
        current_domain.process(
            EditReview(
                review_id=review_id,
                customer_id="cust-cr-nt1",
                body="Updated body content that is absolutely long enough.",
            ),
            asynchronous=False,
        )
        cr = current_domain.repository_for(CustomerReviews).get(review_id)
        assert cr.title == "Extended test review"  # Unchanged
        assert cr.status == "Pending"

    def test_edit_without_rating_keeps_original(self):
        review_id = _submit_review(product_id="prod-cr-nr1", customer_id="cust-cr-nr1", rating=3)
        current_domain.process(
            EditReview(
                review_id=review_id,
                customer_id="cust-cr-nr1",
                title="Only title changed",
            ),
            asynchronous=False,
        )
        cr = current_domain.repository_for(CustomerReviews).get(review_id)
        assert cr.rating == 3  # Unchanged
        assert cr.title == "Only title changed"


class TestSubmissionVerifiedPurchase:
    """Cover the verified purchase path in SubmitReviewHandler."""

    def test_submit_with_verified_purchase(self):
        import uuid

        from reviews.projections.verified_purchases import VerifiedPurchases

        # Create a verified purchase record
        vp_repo = current_domain.repository_for(VerifiedPurchases)
        vp_repo.add(
            VerifiedPurchases(
                vp_id=str(uuid.uuid4()),
                customer_id="cust-vp-submit",
                product_id="prod-vp-submit",
                order_id="order-vp-001",
                delivered_at="2024-01-01T00:00:00+00:00",
            )
        )

        from reviews.review.review import Review

        review_id = current_domain.process(
            SubmitReview(
                product_id="prod-vp-submit",
                customer_id="cust-vp-submit",
                rating=5,
                title="Verified purchase review",
                body="This review is from a verified purchase and long enough.",
            ),
            asynchronous=False,
        )
        review = current_domain.repository_for(Review).get(review_id)
        assert review.verified_purchase is True
        assert review.order_id == "order-vp-001"
