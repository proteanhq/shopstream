"""BDD tests for customer tier management."""

from identity.customer.events import TierUpgraded
from protean.exceptions import ValidationError
from pytest_bdd import parsers, scenarios, then, when

scenarios("features/customer_tier.feature")


# ---------------------------------------------------------------------------
# When steps
# ---------------------------------------------------------------------------
@when(parsers.cfparse('the customer is upgraded to "{new_tier}"'))
def upgrade_tier(customer, new_tier, error):
    try:
        customer.upgrade_tier(new_tier)
    except ValidationError as exc:
        error["exc"] = exc


# ---------------------------------------------------------------------------
# Then steps
# ---------------------------------------------------------------------------
@then(parsers.cfparse('the TierUpgraded event contains previous tier "{prev_tier}"'))
def event_has_previous_tier(customer, prev_tier):
    event = next(e for e in customer._events if isinstance(e, TierUpgraded))
    assert event.previous_tier == prev_tier


@then(parsers.cfparse('the TierUpgraded event contains new tier "{new_tier}"'))
def event_has_new_tier(customer, new_tier):
    event = next(e for e in customer._events if isinstance(e, TierUpgraded))
    assert event.new_tier == new_tier
