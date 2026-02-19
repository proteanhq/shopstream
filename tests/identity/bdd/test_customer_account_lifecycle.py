"""BDD tests for customer account lifecycle (suspend, reactivate, close)."""

from identity.customer.events import AccountSuspended
from protean.exceptions import ValidationError
from pytest_bdd import parsers, scenarios, then, when

scenarios("features/customer_account_lifecycle.feature")


# ---------------------------------------------------------------------------
# When steps
# ---------------------------------------------------------------------------
@when(parsers.cfparse('the account is suspended with reason "{reason}"'))
def suspend_account(customer, reason, error):
    try:
        customer.suspend(reason)
    except ValidationError as exc:
        error["exc"] = exc


@when("the account is reactivated")
def reactivate_account(customer, error):
    try:
        customer.reactivate()
    except ValidationError as exc:
        error["exc"] = exc


@when("the account is closed")
def close_account(customer, error):
    try:
        customer.close()
    except ValidationError as exc:
        error["exc"] = exc


# ---------------------------------------------------------------------------
# Then steps
# ---------------------------------------------------------------------------
@then(parsers.cfparse('an AccountSuspended event is raised with reason "{reason}"'))
def suspended_event_with_reason(customer, reason):
    events = [e for e in customer._events if isinstance(e, AccountSuspended)]
    assert len(events) == 1
    assert events[0].reason == reason
