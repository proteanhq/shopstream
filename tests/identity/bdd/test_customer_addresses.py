"""BDD tests for customer address management."""

from protean.exceptions import ValidationError
from pytest_bdd import parsers, scenarios, then, when

scenarios("features/customer_addresses.feature")


# ---------------------------------------------------------------------------
# When steps
# ---------------------------------------------------------------------------
@when(parsers.cfparse('the customer adds an address "{street}" "{city}" "{postal_code}" "{country}"'))
def add_address(customer, street, city, postal_code, country, error):
    try:
        customer.add_address(
            street=street,
            city=city,
            postal_code=postal_code,
            country=country,
        )
    except ValidationError as exc:
        error["exc"] = exc


@when(
    parsers.cfparse('the customer adds an address "{street}" "{city}" "{postal_code}" "{country}" with label "{label}"')
)
def add_address_with_label(customer, street, city, postal_code, country, label, error):
    try:
        customer.add_address(
            label=label,
            street=street,
            city=city,
            postal_code=postal_code,
            country=country,
        )
    except ValidationError as exc:
        error["exc"] = exc


@when(parsers.cfparse('the customer updates the address street to "{street}"'))
def update_address_street(customer, street):
    address = customer.addresses[0]
    customer.update_address(address.id, street=street)


@when("the non-default address is removed")
def remove_non_default_address(customer, error):
    non_default = next(a for a in customer.addresses if not a.is_default)
    try:
        customer.remove_address(non_default.id)
    except ValidationError as exc:
        error["exc"] = exc


@when("the default address is removed")
def remove_default_address(customer, error):
    default = next(a for a in customer.addresses if a.is_default)
    try:
        customer.remove_address(default.id)
    except ValidationError as exc:
        error["exc"] = exc


@when("the last address is removed")
def remove_last_address(customer, error):
    address = customer.addresses[0]
    try:
        customer.remove_address(address.id)
    except ValidationError as exc:
        error["exc"] = exc


@when("the second address is set as default")
def set_second_as_default(customer):
    second = customer.addresses[1]
    customer.set_default_address(second.id)


# ---------------------------------------------------------------------------
# Then steps
# ---------------------------------------------------------------------------
@then(parsers.cfparse("the customer has {count:d} address"))
def customer_has_n_addresses_singular(customer, count):
    assert len(customer.addresses) == count


@then(parsers.cfparse("the customer has {count:d} addresses"))
def customer_has_n_addresses(customer, count):
    assert len(customer.addresses) == count


@then("the address is the default")
def address_is_default(customer):
    assert customer.addresses[-1].is_default is True


@then("the first address is still the default")
def first_is_default(customer):
    assert customer.addresses[0].is_default is True


@then(parsers.cfparse('the address label is "{label}"'))
def address_label_is(customer, label):
    assert customer.addresses[-1].label == label


@then(parsers.cfparse('the address street is "{street}"'))
def address_street_is(customer, street):
    assert customer.addresses[0].street == street


@then("the remaining address is the default")
def remaining_is_default(customer):
    assert len(customer.addresses) == 1
    assert customer.addresses[0].is_default is True


@then("the second address is the default")
def second_is_default(customer):
    assert customer.addresses[1].is_default is True


@then("the first address is no longer default")
def first_not_default(customer):
    assert customer.addresses[0].is_default is False
