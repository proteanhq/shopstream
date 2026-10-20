"""Tests for HTML escaping on the review free-text fields.

`Review.title`, `Review.body`, `Review.moderation_notes`, `SellerReply.body` and
`ReviewImage.alt_text` declare `sanitize=True`. Protean checks `max_length` on the
escaped value, so an input inside the bound can still be rejected once `&`
becomes `&amp;`. `ReviewImage.url` stays raw, because escaping `&` would break a
query string.
"""

import pytest
from protean.exceptions import ValidationError

from reviews.review.review import Review, ReviewImage

BODY = "I really enjoyed this product, it exceeded expectations."


def _make_review(**overrides):
    defaults = {
        "product_id": "prod-001",
        "customer_id": "cust-001",
        "rating": 4,
        "title": "Great product",
        "body": BODY,
    }
    defaults.update(overrides)
    return Review.submit(**defaults)


class TestTitleSanitization:
    # 190 + 5 = 195 characters as typed; each `&` becomes `&amp;`, so 215 once escaped.
    GROWS_PAST_BOUND = "a" * 190 + "&&&&&"

    def test_ampersand_is_stored_escaped(self):
        review = _make_review(title="Salt & pepper grinder")
        assert review.title == "Salt &amp; pepper grinder"

    def test_title_within_bound_that_grows_past_it_is_rejected_on_submit(self):
        assert len(self.GROWS_PAST_BOUND) <= 200
        with pytest.raises(ValidationError) as exc:
            _make_review(title=self.GROWS_PAST_BOUND)
        assert "title" in exc.value.messages

    def test_title_within_bound_that_grows_past_it_is_rejected_on_edit(self):
        review = _make_review()
        with pytest.raises(ValidationError) as exc:
            review.edit(title=self.GROWS_PAST_BOUND)
        assert "title" in exc.value.messages

    def test_escaped_title_survives_reassignment_unchanged(self):
        review = _make_review(title="Salt & pepper grinder")
        review.edit(title=review.title)
        assert review.title == "Salt &amp; pepper grinder"


class TestAltTextSanitization:
    # 250 + 2 = 252 characters as typed, 260 once escaped.
    GROWS_PAST_BOUND = "a" * 250 + "&&"

    def test_alt_text_within_bound_that_grows_past_it_is_rejected_on_submit(self):
        assert len(self.GROWS_PAST_BOUND) <= 255
        with pytest.raises(ValidationError) as exc:
            _make_review(images=[{"url": "https://cdn.example.com/a.jpg", "alt_text": self.GROWS_PAST_BOUND}])
        assert "alt_text" in exc.value.messages

    def test_alt_text_ampersand_is_stored_escaped(self):
        review = _make_review(images=[{"url": "https://cdn.example.com/a.jpg", "alt_text": "Front & back"}])
        assert review.images[0].alt_text == "Front &amp; back"


class TestUrlIsNotSanitized:
    def test_query_string_ampersand_is_stored_unchanged(self):
        url = "https://cdn.example.com/img.jpg?w=200&h=100"
        review = _make_review(images=[{"url": url, "alt_text": "Front"}])
        assert review.images[0].url == url

    def test_url_constructed_directly_is_stored_unchanged(self):
        image = ReviewImage(url="https://cdn.example.com/img.jpg?a=1&b=2")
        assert image.url == "https://cdn.example.com/img.jpg?a=1&b=2"


class TestTextFieldSanitization:
    RAW = "Size 1 < size 2 & fits well, would buy again."
    ESCAPED = "Size 1 &lt; size 2 &amp; fits well, would buy again."

    def test_body_is_stored_escaped(self):
        review = _make_review(body=self.RAW)
        assert review.body == self.ESCAPED

    def test_body_script_tag_is_escaped(self):
        review = _make_review(body="<script>alert(1)</script> nice product overall")
        assert review.body == "&lt;script&gt;alert(1)&lt;/script&gt; nice product overall"

    def test_moderation_notes_on_approve_are_stored_escaped(self):
        review = _make_review()
        review.approve(moderator_id="mod-001", notes=self.RAW)
        assert review.moderation_notes == self.ESCAPED

    def test_moderation_notes_on_reject_are_stored_escaped(self):
        review = _make_review()
        review.reject(moderator_id="mod-001", reason=self.RAW)
        assert review.moderation_notes == self.ESCAPED

    def test_seller_reply_body_is_stored_escaped(self):
        review = _make_review()
        review.approve(moderator_id="mod-001")
        review.add_seller_reply(seller_id="seller-001", body=self.RAW)
        assert review.reply[0].body == self.ESCAPED
