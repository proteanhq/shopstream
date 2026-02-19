"""BDD tests for category management."""

import json

from catalogue.category.category import Category
from protean.exceptions import ValidationError
from pytest_bdd import parsers, scenarios, then, when

scenarios("features/category_management.feature")


# ---------------------------------------------------------------------------
# When steps
# ---------------------------------------------------------------------------
@when(
    parsers.cfparse('a category is created with name "{name}"'),
    target_fixture="category",
)
def create_category(name):
    return Category.create(name=name)


@when(
    parsers.cfparse('a category is created with name "{name}" under parent "{parent_id}" at level {level:d}'),
    target_fixture="category",
)
def create_subcategory(name, parent_id, level):
    return Category.create(name=name, parent_category_id=parent_id, level=level)


@when(parsers.cfparse('the category name is updated to "{name}"'))
def update_category_name(category, name):
    category.update_details(name=name)


@when(parsers.cfparse("the category attributes are updated to '{attributes}'"))
def update_category_attributes(category, attributes):
    category.update_details(attributes=json.loads(attributes))


@when(parsers.cfparse("the category display order is changed to {order:d}"))
def reorder_category(category, order):
    category.reorder(order)


@when("the category is deactivated")
def deactivate_category(category, error):
    try:
        category.deactivate()
    except ValidationError as exc:
        error["exc"] = exc


# ---------------------------------------------------------------------------
# Then steps
# ---------------------------------------------------------------------------
@then(parsers.cfparse('the category name is "{name}"'))
def category_name_is(category, name):
    assert category.name == name


@then(parsers.cfparse("the category level is {level:d}"))
def category_level_is(category, level):
    assert category.level == level


@then("the category is active")
def category_is_active(category):
    assert category.is_active is True


@then("the category is inactive")
def category_is_inactive(category):
    assert category.is_active is False


@then("the category has attributes")
def category_has_attributes(category):
    assert category.attributes is not None


@then(parsers.cfparse("the category display order is {order:d}"))
def category_display_order_is(category, order):
    assert category.display_order == order
