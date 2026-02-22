"""BDD tests for delivery exceptions."""

from protean.exceptions import ValidationError
from pytest_bdd import parsers, scenarios, when

scenarios("features/delivery_exception.feature")


@when(
    parsers.cfparse('a delivery exception is recorded with reason "{reason}" at "{location}"'),
    target_fixture="ff",
)
def record_exception(ff, reason, location):
    ff.record_exception(reason, location)
    return ff


@when(
    parsers.cfparse('a tracking event "{status}" is recorded at "{location}"'),
    target_fixture="ff",
)
def add_tracking_event(ff, status, location):
    ff.add_tracking_event(status, location, f"Tracking: {status}")
    return ff


@when("delivery is confirmed", target_fixture="ff")
def confirm_delivery(ff):
    ff.record_delivery()
    return ff


@when(
    parsers.cfparse('a delivery exception is attempted with reason "{reason}"'),
    target_fixture="ff",
)
def attempt_exception(ff, reason, error):
    try:
        ff.record_exception(reason)
    except ValidationError as exc:
        error["exc"] = exc
    return ff
