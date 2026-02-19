"""BDD tests for customer profile management."""

from pytest_bdd import parsers, scenarios, when

scenarios("features/customer_profile.feature")


# ---------------------------------------------------------------------------
# When steps
# ---------------------------------------------------------------------------
@when(parsers.cfparse('the customer updates their profile with first name "{first_name}"'))
def update_first_name(customer, first_name):
    customer.update_profile(first_name=first_name)


@when(parsers.cfparse('the customer updates their profile with last name "{last_name}"'))
def update_last_name(customer, last_name):
    customer.update_profile(last_name=last_name)


@when(parsers.cfparse('the customer updates their profile with phone "{phone}"'))
def update_phone(customer, phone):
    customer.update_profile(phone=phone)


@when(parsers.cfparse('the customer updates their profile with date of birth "{dob}"'))
def update_dob(customer, dob):
    from datetime import date

    customer.update_profile(date_of_birth=date.fromisoformat(dob))


@when(parsers.cfparse('the customer updates their profile with name "{first}" "{last}"'))
def update_name(customer, first, last):
    customer.update_profile(first_name=first, last_name=last)


@when("the customer updates their profile with no phone")
def clear_phone(customer):
    customer.update_profile(phone=None)
