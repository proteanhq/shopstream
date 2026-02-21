"""Application tests for ReportReview command handler."""

import pytest
from protean import current_domain
from protean.exceptions import ValidationError
from reviews.review.reporting import ReportReview
from reviews.review.review import Review
from reviews.review.submission import SubmitReview


def _submit_review(**overrides):
    defaults = {
        "product_id": "prod-report",
        "customer_id": "cust-report-author",
        "rating": 4,
        "title": "Review for reporting",
        "body": "This is a review body that is long enough for validation.",
    }
    defaults.update(overrides)
    return current_domain.process(SubmitReview(**defaults), asynchronous=False)


class TestReportReviewCommand:
    def test_report_persists(self):
        review_id = _submit_review(product_id="prod-rpt-1", customer_id="cust-rpt-1")
        current_domain.process(
            ReportReview(
                review_id=review_id,
                customer_id="cust-reporter-1",
                reason="Spam",
                detail="Contains promotional links",
            ),
            asynchronous=False,
        )
        review = current_domain.repository_for(Review).get(review_id)
        assert review.report_count == 1

    def test_self_report_rejected(self):
        review_id = _submit_review(product_id="prod-rpt-2", customer_id="cust-rpt-2")
        with pytest.raises(ValidationError) as exc:
            current_domain.process(
                ReportReview(
                    review_id=review_id,
                    customer_id="cust-rpt-2",
                    reason="Spam",
                ),
                asynchronous=False,
            )
        assert "Cannot report your own" in str(exc.value)
