"""Wide-event enrichment test (Protean 0.16 observability).

`SubmitReviewHandler` calls `bind_event_context(...)` to add review dimensions
(product_id, rating, verified_purchase) to the per-message `protean.access`
wide event. This asserts those fields land on the emitted log record during
synchronous command processing.
"""

import logging

from protean import current_domain

from reviews.review.submission import SubmitReview


def _submit(**overrides):
    defaults = {
        "product_id": "prod-wide-001",
        "customer_id": "cust-001",
        "rating": 5,
        "title": "Excellent",
        "body": "I really enjoyed this product, it exceeded expectations.",
    }
    defaults.update(overrides)
    return current_domain.process(SubmitReview(**defaults), asynchronous=False)


def _access_records(caplog):
    return [
        r
        for r in caplog.records
        if r.name == "protean.access" and getattr(r, "handler", "").startswith("SubmitReviewHandler")
    ]


class TestReviewWideEventEnrichment:
    def test_review_dimensions_on_wide_event(self, caplog):
        with caplog.at_level(logging.INFO, logger="protean.access"):
            _submit(product_id="prod-abc", rating=3)

        records = _access_records(caplog)
        assert records, "no protean.access wide event emitted for SubmitReviewHandler"
        rec = records[-1]
        assert getattr(rec, "product_id", None) == "prod-abc"
        assert getattr(rec, "rating", None) == 3
        # No VerifiedPurchases record seeded → unverified.
        assert getattr(rec, "verified_purchase", None) is False
