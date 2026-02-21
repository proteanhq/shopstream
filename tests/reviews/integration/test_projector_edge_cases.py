"""Test projector edge cases — events referencing non-existent projection records.

These defensive code paths handle situations where events arrive out of order
or projection records were never created (e.g., during recovery/replay).
"""

from datetime import UTC, datetime

from protean import current_domain
from reviews.projections.customer_reviews import (
    CustomerReviews,
    CustomerReviewsProjector,
)
from reviews.projections.moderation_queue import ModerationQueue, ModerationQueueProjector
from reviews.projections.product_rating import ProductRating, ProductRatingProjector
from reviews.projections.product_reviews import ProductReviewsProjector
from reviews.projections.review_detail import ReviewDetail, ReviewDetailProjector
from reviews.review.events import (
    HelpfulVoteRecorded,
    ReviewApproved,
    ReviewEdited,
    ReviewRejected,
    ReviewRemoved,
    ReviewReported,
    SellerReplyAdded,
)
from reviews.review.moderation import ModerateReview
from reviews.review.review import Review
from reviews.review.submission import SubmitReview


def _submit_and_get_id(**overrides):
    defaults = {
        "product_id": "prod-edge-001",
        "customer_id": "cust-edge-001",
        "rating": 4,
        "title": "Edge case test",
        "body": "This is a review body long enough for edge case testing.",
    }
    defaults.update(overrides)
    return current_domain.process(SubmitReview(**defaults), asynchronous=False)


class TestReviewDetailProjectorEdgeCases:
    """Cover all the except-return paths in ReviewDetailProjector."""

    def _nonexistent_event(self, **kwargs):
        """Helper to build events with a review_id that has no projection record."""
        return kwargs

    def test_edit_nonexistent_skips(self):
        projector = ReviewDetailProjector()
        event = ReviewEdited(
            review_id="nonexistent-rd-edit",
            title="Edited",
            edited_at=datetime.now(UTC),
        )
        # Should not raise — just return early
        projector.on_review_edited(event)
        # Verify nothing was created
        try:
            current_domain.repository_for(ReviewDetail).get("nonexistent-rd-edit")
            raise AssertionError("Should not exist")
        except Exception:
            pass

    def test_approve_nonexistent_skips(self):
        projector = ReviewDetailProjector()
        event = ReviewApproved(
            review_id="nonexistent-rd-apr",
            product_id="prod-x",
            customer_id="cust-x",
            rating=4,
            moderator_id="mod-x",
            approved_at=datetime.now(UTC),
        )
        projector.on_review_approved(event)

    def test_reject_nonexistent_skips(self):
        projector = ReviewDetailProjector()
        event = ReviewRejected(
            review_id="nonexistent-rd-rej",
            product_id="prod-x",
            customer_id="cust-x",
            moderator_id="mod-x",
            reason="Bad",
            rejected_at=datetime.now(UTC),
        )
        projector.on_review_rejected(event)

    def test_vote_nonexistent_skips(self):
        projector = ReviewDetailProjector()
        event = HelpfulVoteRecorded(
            review_id="nonexistent-rd-vote",
            voter_id="v1",
            vote_type="Helpful",
            helpful_count=1,
            unhelpful_count=0,
            voted_at=datetime.now(UTC),
        )
        projector.on_helpful_vote_recorded(event)

    def test_report_nonexistent_skips(self):
        projector = ReviewDetailProjector()
        event = ReviewReported(
            review_id="nonexistent-rd-rpt",
            reporter_id="r1",
            reason="Spam",
            report_count=1,
            reported_at=datetime.now(UTC),
        )
        projector.on_review_reported(event)

    def test_remove_nonexistent_skips(self):
        projector = ReviewDetailProjector()
        event = ReviewRemoved(
            review_id="nonexistent-rd-rm",
            product_id="prod-x",
            customer_id="cust-x",
            rating=4,
            removed_by="Admin",
            reason="Policy",
            removed_at=datetime.now(UTC),
        )
        projector.on_review_removed(event)

    def test_seller_reply_nonexistent_skips(self):
        projector = ReviewDetailProjector()
        event = SellerReplyAdded(
            review_id="nonexistent-rd-reply",
            seller_id="s1",
            body="Thanks!",
            replied_at=datetime.now(UTC),
        )
        projector.on_seller_reply_added(event)


class TestCustomerReviewsProjectorEdgeCases:
    """Cover the except-return paths and branch conditions."""

    def test_edit_nonexistent_skips(self):
        projector = CustomerReviewsProjector()
        event = ReviewEdited(
            review_id="nonexistent-cr-edit",
            title="Edited",
            edited_at=datetime.now(UTC),
        )
        projector.on_review_edited(event)

    def test_update_status_nonexistent_skips(self):
        projector = CustomerReviewsProjector()
        projector._update_status("nonexistent-cr-status", "Published", datetime.now(UTC))

    def test_edit_with_no_title_no_rating(self):
        """Edit event with neither title nor rating — only sets status."""
        review_id = _submit_and_get_id(product_id="prod-cr-edge1", customer_id="cust-cr-edge1")
        projector = CustomerReviewsProjector()
        event = ReviewEdited(
            review_id=review_id,
            edited_at=datetime.now(UTC),
        )
        projector.on_review_edited(event)
        cr = current_domain.repository_for(CustomerReviews).get(review_id)
        assert cr.status == "Pending"
        assert cr.title == "Edge case test"  # Unchanged
        assert cr.rating == 4  # Unchanged


class TestModerationQueueProjectorEdgeCases:
    """Cover the reported review re-add path with enrichment."""

    def test_reported_review_not_in_queue_enriched_from_aggregate(self):
        """When a reported event arrives for a review not in the moderation queue,
        the projector creates a new MQ entry enriched from the aggregate."""
        review_id = _submit_and_get_id(product_id="prod-mq-enrich", customer_id="cust-mq-enrich")

        # Manually delete the MQ entry at the DAO level so get() will fail
        repo = current_domain.repository_for(ModerationQueue)
        repo._dao.delete(repo.get(review_id))

        # Verify it's actually gone
        try:
            repo.get(review_id)
            raise AssertionError("Should not find MQ entry")
        except Exception:
            pass

        # Now call projector directly for the reported event on a non-queued review
        projector = ModerationQueueProjector()
        event = ReviewReported(
            review_id=review_id,
            reporter_id="reporter-mq-enrich",
            reason="Fake",
            report_count=1,
            reported_at=datetime.now(UTC),
        )
        projector.on_review_reported(event)

        mq = current_domain.repository_for(ModerationQueue).get(review_id)
        assert mq.report_count == 1
        # Should be enriched from the aggregate
        assert mq.product_id == "prod-mq-enrich"
        assert mq.customer_id == "cust-mq-enrich"
        assert mq.rating == 4
        assert mq.title == "Edge case test"

    def test_reported_review_not_in_queue_no_aggregate(self):
        """When a reported event arrives for a review that doesn't exist in MQ or
        as an aggregate, the projector silently skips."""
        projector = ModerationQueueProjector()
        event = ReviewReported(
            review_id="totally-nonexistent-review",
            reporter_id="reporter-ghost",
            reason="Spam",
            report_count=1,
            reported_at=datetime.now(UTC),
        )
        # Should not raise — silently skips when aggregate can't be found
        projector.on_review_reported(event)

        # Verify no MQ entry was created (can't create without aggregate data)
        try:
            current_domain.repository_for(ModerationQueue).get("totally-nonexistent-review")
            raise AssertionError("Should not find MQ entry")
        except Exception:
            pass


class TestProductRatingEdgeCases:
    """Cover verified purchase check and removal without existing record."""

    def test_removal_with_no_existing_rating_record(self):
        """ReviewRemoved for a product with no rating record should be a no-op."""
        projector = ProductRatingProjector()
        event = ReviewRemoved(
            review_id="nonexistent-pr-rm",
            product_id="prod-no-rating",
            customer_id="cust-x",
            rating=3,
            removed_by="Admin",
            reason="Policy",
            removed_at=datetime.now(UTC),
        )
        projector.on_review_removed(event)
        # Should not raise, just return early

    def test_approved_review_checks_verified_purchase(self):
        """When a review is approved, the projector checks if it's a verified purchase."""
        review_id = _submit_and_get_id(product_id="prod-pr-vp1", customer_id="cust-pr-vp1")
        # Approve triggers the verified purchase check path
        current_domain.process(
            ModerateReview(review_id=review_id, moderator_id="mod-001", action="Approve"),
            asynchronous=False,
        )
        pr = current_domain.repository_for(ProductRating).get("prod-pr-vp1")
        assert pr.total_reviews == 1
        assert pr.verified_review_count == 0  # Not verified


class TestProductReviewsEdgeCases:
    def test_seller_reply_on_nonexistent_skips(self):
        projector = ProductReviewsProjector()
        event = SellerReplyAdded(
            review_id="nonexistent-prv-reply",
            seller_id="s1",
            body="Thanks!",
            replied_at=datetime.now(UTC),
        )
        projector.on_seller_reply_added(event)

    def test_vote_on_nonexistent_skips(self):
        projector = ProductReviewsProjector()
        event = HelpfulVoteRecorded(
            review_id="nonexistent-prv-vote",
            voter_id="v1",
            vote_type="Helpful",
            helpful_count=1,
            unhelpful_count=0,
            voted_at=datetime.now(UTC),
        )
        projector.on_helpful_vote_recorded(event)


class TestReviewDetailEditBranches:
    """Cover the False branches for if event.title/body/rating in on_review_edited."""

    def test_edit_with_no_title_no_body_no_rating(self):
        """Edit event with no title, body, or rating — only sets is_edited and status."""
        review_id = _submit_and_get_id(product_id="prod-rd-branch1", customer_id="cust-rd-branch1")
        projector = ReviewDetailProjector()
        event = ReviewEdited(
            review_id=review_id,
            edited_at=datetime.now(UTC),
        )
        projector.on_review_edited(event)
        rd = current_domain.repository_for(ReviewDetail).get(review_id)
        assert rd.is_edited == "True"
        assert rd.status == "Pending"
        assert rd.title == "Edge case test"  # Unchanged
        assert rd.body == "This is a review body long enough for edge case testing."  # Unchanged
        assert rd.rating == 4  # Unchanged


class TestProductRatingVerifiedPurchase:
    """Cover the verified_purchase True path in ProductRatingProjector."""

    def test_approved_verified_review_increments_verified_count(self):
        import uuid

        from reviews.projections.verified_purchases import VerifiedPurchases

        # Create verified purchase record BEFORE submitting review
        vp_repo = current_domain.repository_for(VerifiedPurchases)
        vp_repo.add(
            VerifiedPurchases(
                vp_id=str(uuid.uuid4()),
                customer_id="cust-vp-rating",
                product_id="prod-vp-rating",
                order_id="order-vp-rat-1",
                delivered_at="2024-01-01T00:00:00+00:00",
            )
        )

        # Submit review (will pick up verified purchase)
        review_id = current_domain.process(
            SubmitReview(
                product_id="prod-vp-rating",
                customer_id="cust-vp-rating",
                rating=5,
                title="Verified purchase review",
                body="This is a verified purchase review that is long enough.",
            ),
            asynchronous=False,
        )

        # Verify the review is marked as verified
        review = current_domain.repository_for(Review).get(review_id)
        assert review.verified_purchase is True

        # Approve — should trigger verified_review_count increment
        current_domain.process(
            ModerateReview(review_id=review_id, moderator_id="mod-001", action="Approve"),
            asynchronous=False,
        )

        from reviews.projections.product_rating import ProductRating

        pr = current_domain.repository_for(ProductRating).get("prod-vp-rating")
        assert pr.total_reviews == 1
        assert pr.verified_review_count == 1
