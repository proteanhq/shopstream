"""Shared BDD fixtures and step definitions for the Catalogue domain."""

import pytest
from catalogue.category.category import Category
from catalogue.category.events import (
    CategoryCreated,
    CategoryDeactivated,
    CategoryDetailsUpdated,
    CategoryReordered,
)
from catalogue.product.events import (
    ProductActivated,
    ProductArchived,
    ProductCreated,
    ProductDetailsUpdated,
    ProductDiscontinued,
    ProductImageAdded,
    ProductImageRemoved,
    TierPriceSet,
    VariantAdded,
    VariantPriceChanged,
)
from catalogue.product.product import (
    Price,
    Product,
)
from protean.exceptions import ValidationError
from pytest_bdd import given, parsers, then

# Map event name strings to classes for dynamic lookup
_PRODUCT_EVENT_CLASSES = {
    "ProductCreated": ProductCreated,
    "ProductDetailsUpdated": ProductDetailsUpdated,
    "VariantAdded": VariantAdded,
    "VariantPriceChanged": VariantPriceChanged,
    "TierPriceSet": TierPriceSet,
    "ProductActivated": ProductActivated,
    "ProductDiscontinued": ProductDiscontinued,
    "ProductArchived": ProductArchived,
    "ProductImageAdded": ProductImageAdded,
    "ProductImageRemoved": ProductImageRemoved,
}

_CATEGORY_EVENT_CLASSES = {
    "CategoryCreated": CategoryCreated,
    "CategoryDetailsUpdated": CategoryDetailsUpdated,
    "CategoryReordered": CategoryReordered,
    "CategoryDeactivated": CategoryDeactivated,
}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture()
def error():
    """Container for captured validation errors."""
    return {"exc": None}


# ---------------------------------------------------------------------------
# Given steps — Product
# ---------------------------------------------------------------------------
@given("a draft product", target_fixture="product")
def draft_product():
    product = Product.create(
        sku="TEST-SKU-001",
        seller_id="seller-1",
        title="Test Product",
        description="A test product description",
        category_id="cat-001",
    )
    product._events.clear()
    return product


@given("a draft product with a variant", target_fixture="product")
def draft_product_with_variant():
    product = Product.create(
        sku="TEST-SKU-001",
        seller_id="seller-1",
        title="Test Product",
        description="A test product description",
        category_id="cat-001",
    )
    product.add_variant(
        variant_sku="VAR-001",
        price=Price(base_price=29.99),
    )
    product._events.clear()
    return product


@given("an active product", target_fixture="product")
def active_product():
    product = Product.create(
        sku="TEST-SKU-001",
        seller_id="seller-1",
        title="Test Product",
        description="A test product description",
        category_id="cat-001",
    )
    product.add_variant(
        variant_sku="VAR-001",
        price=Price(base_price=29.99),
    )
    product.activate()
    product._events.clear()
    return product


@given("a discontinued product", target_fixture="product")
def discontinued_product():
    product = Product.create(
        sku="TEST-SKU-001",
        seller_id="seller-1",
        title="Test Product",
        description="A test product description",
        category_id="cat-001",
    )
    product.add_variant(
        variant_sku="VAR-001",
        price=Price(base_price=29.99),
    )
    product.activate()
    product.discontinue()
    product._events.clear()
    return product


@given("the product has an image", target_fixture="product")
def product_has_image(product):
    product.add_image(url="https://example.com/image1.jpg", alt_text="Image 1")
    product._events.clear()
    return product


@given("the product has 2 images", target_fixture="product")
def product_has_two_images(product):
    product.add_image(url="https://example.com/image1.jpg", alt_text="Image 1")
    product.add_image(url="https://example.com/image2.jpg", alt_text="Image 2")
    product._events.clear()
    return product


@given("the product has 10 images", target_fixture="product")
def product_has_ten_images(product):
    for i in range(10):
        product.add_image(
            url=f"https://example.com/image{i + 1}.jpg",
            alt_text=f"Image {i + 1}",
        )
    product._events.clear()
    return product


# ---------------------------------------------------------------------------
# Given steps — Category
# ---------------------------------------------------------------------------
@given("an active category", target_fixture="category")
def active_category():
    category = Category.create(name="Electronics")
    category._events.clear()
    return category


@given("an inactive category", target_fixture="category")
def inactive_category():
    category = Category.create(name="Old Category")
    category.deactivate()
    category._events.clear()
    return category


# ---------------------------------------------------------------------------
# Then steps (shared)
# ---------------------------------------------------------------------------
@then("the action fails with a validation error")
def action_fails_with_validation_error(error):
    assert error["exc"] is not None, "Expected a validation error but none was raised"
    assert isinstance(error["exc"], ValidationError)


@then(parsers.cfparse('the product status is "{status}"'))
def product_status_is(product, status):
    assert product.status == status


@then(parsers.cfparse('the product title is "{title}"'))
def product_title_is(product, title):
    assert product.title == title


@then(parsers.cfparse("a {event_type} product event is raised"))
def product_event_raised(product, event_type):
    event_cls = _PRODUCT_EVENT_CLASSES[event_type]
    assert any(
        isinstance(e, event_cls) for e in product._events
    ), f"No {event_type} event found. Events: {[type(e).__name__ for e in product._events]}"


@then(parsers.cfparse("a {event_type} category event is raised"))
def category_event_raised(category, event_type):
    event_cls = _CATEGORY_EVENT_CLASSES[event_type]
    assert any(
        isinstance(e, event_cls) for e in category._events
    ), f"No {event_type} event found. Events: {[type(e).__name__ for e in category._events]}"
