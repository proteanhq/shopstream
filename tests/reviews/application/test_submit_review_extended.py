"""Extended application tests for SubmitReview — edge cases."""

import json

from protean import current_domain
from reviews.review.moderation import ModerateReview
from reviews.review.removal import RemoveReview
from reviews.review.review import Review
from reviews.review.submission import SubmitReview


class TestResubmitAfterRemoval:
    def test_can_submit_after_previous_removed(self):
        """A removed review doesn't block a new submission for same product/customer."""
        review_id = current_domain.process(
            SubmitReview(
                product_id="prod-resub",
                customer_id="cust-resub",
                rating=4,
                title="First review",
                body="This is the first review body that is long enough.",
            ),
            asynchronous=False,
        )
        # Approve then remove
        current_domain.process(
            ModerateReview(
                review_id=review_id,
                moderator_id="mod-001",
                action="Approve",
            ),
            asynchronous=False,
        )
        current_domain.process(
            RemoveReview(
                review_id=review_id,
                removed_by="Admin",
                reason="Policy violation",
            ),
            asynchronous=False,
        )
        # Should be able to submit again
        new_id = current_domain.process(
            SubmitReview(
                product_id="prod-resub",
                customer_id="cust-resub",
                rating=5,
                title="Second review",
                body="This is the second review body that is long enough.",
            ),
            asynchronous=False,
        )
        assert new_id is not None
        review = current_domain.repository_for(Review).get(new_id)
        assert review.title == "Second review"


class TestEditPartialUpdates:
    def test_edit_only_pros(self):
        from reviews.review.editing import EditReview

        review_id = current_domain.process(
            SubmitReview(
                product_id="prod-partial-1",
                customer_id="cust-partial-1",
                rating=4,
                title="Partial edit test",
                body="This is a review body that is long enough for validation.",
            ),
            asynchronous=False,
        )
        current_domain.process(
            EditReview(
                review_id=review_id,
                customer_id="cust-partial-1",
                pros=json.dumps(["Good quality"]),
            ),
            asynchronous=False,
        )
        review = current_domain.repository_for(Review).get(review_id)
        assert json.loads(review.pros) == ["Good quality"]

    def test_edit_only_cons(self):
        from reviews.review.editing import EditReview

        review_id = current_domain.process(
            SubmitReview(
                product_id="prod-partial-2",
                customer_id="cust-partial-2",
                rating=4,
                title="Partial cons test",
                body="This is a review body that is long enough for validation.",
            ),
            asynchronous=False,
        )
        current_domain.process(
            EditReview(
                review_id=review_id,
                customer_id="cust-partial-2",
                cons=json.dumps(["Fragile"]),
            ),
            asynchronous=False,
        )
        review = current_domain.repository_for(Review).get(review_id)
        assert json.loads(review.cons) == ["Fragile"]

    def test_edit_body_only(self):
        from reviews.review.editing import EditReview

        review_id = current_domain.process(
            SubmitReview(
                product_id="prod-partial-3",
                customer_id="cust-partial-3",
                rating=4,
                title="Body only edit test",
                body="This is the original body that is long enough for validation.",
            ),
            asynchronous=False,
        )
        current_domain.process(
            EditReview(
                review_id=review_id,
                customer_id="cust-partial-3",
                body="This is the new body content that is long enough for validation.",
            ),
            asynchronous=False,
        )
        review = current_domain.repository_for(Review).get(review_id)
        assert review.body == "This is the new body content that is long enough for validation."
