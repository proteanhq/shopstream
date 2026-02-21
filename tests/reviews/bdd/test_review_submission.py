"""BDD tests for review submission."""

from protean.exceptions import ValidationError
from pytest_bdd import parsers, scenarios, when
from reviews.review.review import Review

scenarios("features/review_submission.feature")


@when(
    parsers.cfparse('a customer submits a review for product "{product_id}" with rating {rating:d}'),
    target_fixture="review",
)
def submit_review(product_id, rating):
    return Review.submit(
        product_id=product_id,
        customer_id="cust-bdd-sub",
        rating=rating,
        title="BDD Submission Test",
        body="This is a BDD test review body that is long enough.",
    )


@when(
    parsers.cfparse("a customer submits a review with {count:d} images"),
    target_fixture="review",
)
def submit_review_with_images(count):
    return Review.submit(
        product_id="prod-bdd-img",
        customer_id="cust-bdd-img",
        rating=4,
        title="Review with images",
        body="This is a review with images that is long enough.",
        images=[{"url": f"https://cdn.example.com/img{i}.jpg"} for i in range(count)],
    )


@when("a customer submits a review with pros and cons", target_fixture="review")
def submit_review_with_pros_cons():
    return Review.submit(
        product_id="prod-bdd-pc",
        customer_id="cust-bdd-pc",
        rating=4,
        title="Review with pros and cons",
        body="This is a review with pros and cons long enough.",
        pros=["Durable", "Good value"],
        cons=["Heavy"],
    )


@when(
    parsers.cfparse('a customer submits a review with body "{body}"'),
    target_fixture="review",
)
def submit_review_short_body(body, error):
    try:
        return Review.submit(
            product_id="prod-bdd-short",
            customer_id="cust-bdd-short",
            rating=4,
            title="Short body test",
            body=body,
        )
    except ValidationError as exc:
        error["exc"] = exc
        # Return a dummy so fixtures don't fail
        return Review.submit(
            product_id="prod-bdd-fallback",
            customer_id="cust-bdd-fallback",
            rating=4,
            title="Fallback",
            body="This is a fallback review for error testing.",
        )
