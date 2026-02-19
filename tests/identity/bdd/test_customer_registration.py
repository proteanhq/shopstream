"""BDD tests for customer registration."""

from identity.customer.customer import Customer
from identity.customer.events import CustomerRegistered
from protean.exceptions import ValidationError
from pytest_bdd import parsers, scenarios, then, when

scenarios("features/customer_registration.feature")


# ---------------------------------------------------------------------------
# When steps
# ---------------------------------------------------------------------------
@when(
    parsers.cfparse('a customer registers with external ID "{ext_id}" and email "{email}"'),
    target_fixture="customer",
)
def register_with_id_and_email(ext_id, email, error):
    try:
        customer = Customer.register(
            external_id=ext_id,
            email=email,
            first_name="Test",
            last_name="User",
        )
        return customer
    except (ValidationError, Exception) as exc:
        error["exc"] = exc
        # Return a minimal customer-like object so Then steps don't crash
        return Customer.__new__(Customer)


@when(
    parsers.cfparse('a customer registers with external ID "{ext_id}" email "{email}" name "{first}" "{last}"'),
    target_fixture="customer",
)
def register_with_full_profile(ext_id, email, first, last, error):
    try:
        return Customer.register(
            external_id=ext_id,
            email=email,
            first_name=first,
            last_name=last,
        )
    except (ValidationError, Exception) as exc:
        error["exc"] = exc
        return Customer.__new__(Customer)


@when(
    parsers.cfparse(
        'a customer registers with external ID "{ext_id}" email "{email}" name "{first}" "{last}" and phone "{phone}"'
    ),
    target_fixture="customer",
)
def register_with_phone(ext_id, email, first, last, phone, error):
    try:
        return Customer.register(
            external_id=ext_id,
            email=email,
            first_name=first,
            last_name=last,
            phone=phone,
        )
    except (ValidationError, Exception) as exc:
        error["exc"] = exc
        return Customer.__new__(Customer)


# ---------------------------------------------------------------------------
# Then steps
# ---------------------------------------------------------------------------
@then(parsers.cfparse('the CustomerRegistered event contains external_id "{ext_id}"'))
def event_has_external_id(customer, ext_id):
    event = next(e for e in customer._events if isinstance(e, CustomerRegistered))
    assert event.external_id == ext_id


@then(parsers.cfparse('the CustomerRegistered event contains email "{email}"'))
def event_has_email(customer, email):
    event = next(e for e in customer._events if isinstance(e, CustomerRegistered))
    assert event.email == email


@then(parsers.cfparse('the CustomerRegistered event contains first_name "{first_name}"'))
def event_has_first_name(customer, first_name):
    event = next(e for e in customer._events if isinstance(e, CustomerRegistered))
    assert event.first_name == first_name
