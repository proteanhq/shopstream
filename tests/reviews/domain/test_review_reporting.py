"""Tests for Review reporting — report reasons, self-report guard, count tracking."""

import json

import pytest
from protean.exceptions import ValidationError
from reviews.review.review import ReportReason, Review


def _make_review(**overrides):
    defaults = {
        "product_id": "prod-001",
        "customer_id": "cust-001",
        "rating": 4,
        "title": "Great product",
        "body": "I really enjoyed this product, it exceeded expectations.",
    }
    defaults.update(overrides)
    return Review.submit(**defaults)


class TestReportReview:
    def test_report_increments_count(self):
        review = _make_review()
        review._events.clear()
        review.report(customer_id="cust-002", reason=ReportReason.SPAM.value)
        assert review.report_count == 1

    def test_report_stores_reason_in_json(self):
        review = _make_review()
        review._events.clear()
        review.report(
            customer_id="cust-002",
            reason=ReportReason.SPAM.value,
            detail="Contains promotional links",
        )
        reports = json.loads(review.reported_reasons)
        assert len(reports) == 1
        assert reports[0]["customer_id"] == "cust-002"
        assert reports[0]["reason"] == ReportReason.SPAM.value
        assert reports[0]["detail"] == "Contains promotional links"

    def test_multiple_reports_accumulate(self):
        review = _make_review()
        review._events.clear()
        review.report(customer_id="cust-002", reason=ReportReason.SPAM.value)
        review._events.clear()
        review.report(customer_id="cust-003", reason=ReportReason.OFFENSIVE.value)
        assert review.report_count == 2
        reports = json.loads(review.reported_reasons)
        assert len(reports) == 2

    def test_report_updates_timestamp(self):
        review = _make_review()
        original = review.updated_at
        review._events.clear()
        review.report(customer_id="cust-002", reason=ReportReason.FAKE.value)
        assert review.updated_at >= original


class TestReportRaisesEvent:
    def test_report_raises_event(self):
        review = _make_review()
        review._events.clear()
        review.report(
            customer_id="cust-002",
            reason=ReportReason.SPAM.value,
            detail="Links in review",
        )
        assert len(review._events) == 1
        event = review._events[0]
        assert event.__class__.__name__ == "ReviewReported"
        assert str(event.review_id) == str(review.id)
        assert str(event.reporter_id) == "cust-002"
        assert event.reason == ReportReason.SPAM.value
        assert event.detail == "Links in review"
        assert event.report_count == 1


class TestSelfReportGuard:
    def test_cannot_report_own_review(self):
        review = _make_review()
        review._events.clear()
        with pytest.raises(ValidationError) as exc:
            review.report(customer_id="cust-001", reason=ReportReason.SPAM.value)
        assert "Cannot report your own review" in str(exc.value)
