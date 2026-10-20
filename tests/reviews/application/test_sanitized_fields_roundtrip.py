"""Sanitized review fields keep their escaped value across save and reload.

Protean cleans a `sanitize=True` field again when it loads a row, so a value that
grew on each round trip would eventually break the `max_length` bound.
"""

from protean import current_domain

from reviews.review.review import Review


def test_escaped_values_are_unchanged_after_save_and_reload():
    review = Review.submit(
        product_id="prod-roundtrip",
        customer_id="cust-roundtrip",
        rating=4,
        title="Salt & pepper <set>",
        body="Grinds fine & coarse, size 1 < size 2, it's great.",
        images=[{"url": "https://cdn.example.com/a.jpg?w=1&h=2", "alt_text": "Front & back"}],
    )
    repo = current_domain.repository_for(Review)

    for _ in range(3):
        repo.add(review)
        review = repo.get(review.id)

    assert review.title == "Salt &amp; pepper &lt;set&gt;"
    assert review.body == "Grinds fine &amp; coarse, size 1 &lt; size 2, it's great."
    assert review.images[0].alt_text == "Front &amp; back"
    assert review.images[0].url == "https://cdn.example.com/a.jpg?w=1&h=2"


def test_body_of_typed_entities_survives_save_and_reload():
    typed = "&amp;" * 4
    review = Review.submit(
        product_id="prod-roundtrip",
        customer_id="cust-roundtrip",
        rating=4,
        title="Entities",
        body=typed,
    )
    repo = current_domain.repository_for(Review)

    repo.add(review)
    review = repo.get(review.id)

    assert review.body == typed
