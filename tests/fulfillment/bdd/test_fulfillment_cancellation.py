"""BDD tests for fulfillment cancellation."""

from protean.exceptions import ValidationError
from pytest_bdd import parsers, scenarios, when

scenarios("features/fulfillment_cancellation.feature")


@when(
    parsers.cfparse('the fulfillment is cancelled with reason "{reason}"'),
    target_fixture="ff",
)
def cancel_fulfillment(ff, reason):
    ff.cancel(reason)
    return ff


@when("delivery is confirmed", target_fixture="ff")
def confirm_delivery(ff):
    ff.record_delivery()
    return ff


@when(
    parsers.cfparse('cancellation is attempted with reason "{reason}"'),
    target_fixture="ff",
)
def attempt_cancellation(ff, reason, error):
    try:
        ff.cancel(reason)
    except ValidationError as exc:
        error["exc"] = exc
    return ff
