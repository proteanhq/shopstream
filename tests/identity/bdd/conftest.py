"""Shared BDD fixtures and step definitions for the Identity domain."""

from datetime import date

import pytest
from identity.customer.customer import Customer, CustomerStatus, CustomerTier
from identity.customer.events import (
    AccountClosed,
    AccountReactivated,
    AccountSuspended,
    AddressAdded,
    AddressRemoved,
    AddressUpdated,
    CustomerRegistered,
    DefaultAddressChanged,
    ProfileUpdated,
    TierUpgraded,
)
from protean.exceptions import ValidationError
from pytest_bdd import given, parsers, then

# Map event name strings to classes for dynamic lookup
_EVENT_CLASSES = {
    "CustomerRegistered": CustomerRegistered,
    "ProfileUpdated": ProfileUpdated,
    "AddressAdded": AddressAdded,
    "AddressUpdated": AddressUpdated,
    "AddressRemoved": AddressRemoved,
    "DefaultAddressChanged": DefaultAddressChanged,
    "AccountSuspended": AccountSuspended,
    "AccountReactivated": AccountReactivated,
    "AccountClosed": AccountClosed,
    "TierUpgraded": TierUpgraded,
}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture()
def error():
    """Container for captured validation errors."""
    return {"exc": None}


# ---------------------------------------------------------------------------
# Given steps
# ---------------------------------------------------------------------------
@given("a registered customer", target_fixture="customer")
def registered_customer():
    customer = Customer.register(
        external_id="EXT-001",
        email="test@example.com",
        first_name="Test",
        last_name="User",
    )
    customer._events.clear()
    return customer


@given("the account is suspended")
def account_is_suspended(customer):
    customer.suspend("Test suspension")
    customer._events.clear()


@given("the account is closed")
def account_is_closed(customer):
    if customer.status == CustomerStatus.ACTIVE.value or customer.status == CustomerStatus.SUSPENDED.value:
        customer.close()
    customer._events.clear()


@given("the customer has a default address", target_fixture="customer")
def customer_with_default_address(customer):
    customer.add_address(
        street="100 Default St",
        city="DefaultCity",
        postal_code="00001",
        country="US",
    )
    customer._events.clear()
    return customer


@given("the customer has 2 addresses", target_fixture="customer")
def customer_with_two_addresses(customer):
    customer.add_address(
        street="100 First St",
        city="CityA",
        postal_code="00001",
        country="US",
    )
    customer.add_address(
        street="200 Second St",
        city="CityB",
        postal_code="00002",
        country="US",
    )
    customer._events.clear()
    return customer


@given("the customer has 10 addresses", target_fixture="customer")
def customer_with_ten_addresses(customer):
    for i in range(10):
        customer.add_address(
            street=f"{i + 1} Street",
            city=f"City{i}",
            postal_code=f"{10000 + i}",
            country="US",
        )
    customer._events.clear()
    return customer


@given(parsers.cfparse('the customer has phone number "{phone}"'))
def customer_has_phone(customer, phone):
    customer.update_profile(phone=phone)
    customer._events.clear()


@given(parsers.cfparse('the customer tier is "{tier}"'))
def customer_at_tier(customer, tier):
    if tier != CustomerTier.STANDARD.value:
        customer.upgrade_tier(tier)
        customer._events.clear()


# ---------------------------------------------------------------------------
# Then steps (shared)
# ---------------------------------------------------------------------------
@then("the action fails with a validation error")
def action_fails_with_validation_error(error):
    assert error["exc"] is not None, "Expected a validation error but none was raised"
    assert isinstance(error["exc"], ValidationError)


@then("the registration fails with a validation error")
def registration_fails(error):
    assert error["exc"] is not None, "Expected a validation error but none was raised"
    assert isinstance(error["exc"], ValidationError)


@then(parsers.cfparse('the customer status is "{status}"'))
def customer_status_is(customer, status):
    assert customer.status == status


@then(parsers.cfparse('the customer tier is "{tier}"'))
def customer_tier_is(customer, tier):
    assert customer.tier == tier


@then(parsers.cfparse('the customer profile first name is "{first_name}"'))
def profile_first_name_is(customer, first_name):
    assert customer.profile.first_name == first_name


@then(parsers.cfparse('the customer profile last name is "{last_name}"'))
def profile_last_name_is(customer, last_name):
    assert customer.profile.last_name == last_name


@then(parsers.cfparse('the customer profile phone number is "{phone}"'))
def profile_phone_is(customer, phone):
    assert customer.profile.phone is not None
    assert customer.profile.phone.number == phone


@then(parsers.cfparse('the customer profile date of birth is "{dob}"'))
def profile_dob_is(customer, dob):
    assert customer.profile.date_of_birth == date.fromisoformat(dob)


@then("the customer has no phone number")
def customer_has_no_phone(customer):
    assert customer.profile.phone is None


@then("the customer has a registered_at timestamp")
def has_registered_at(customer):
    assert customer.registered_at is not None


@then("the customer has no last_login_at timestamp")
def no_last_login(customer):
    assert customer.last_login_at is None


@then(parsers.cfparse("a {event_type} event is raised"))
def generic_event_raised(customer, event_type):
    event_cls = _EVENT_CLASSES[event_type]
    assert any(
        isinstance(e, event_cls) for e in customer._events
    ), f"No {event_type} event found. Events: {[type(e).__name__ for e in customer._events]}"


@then(parsers.cfparse("an {event_type} event is raised"))
def generic_event_raised_an(customer, event_type):
    event_cls = _EVENT_CLASSES[event_type]
    assert any(
        isinstance(e, event_cls) for e in customer._events
    ), f"No {event_type} event found. Events: {[type(e).__name__ for e in customer._events]}"
