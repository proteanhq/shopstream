"""BDD steps for the reward account lifecycle."""

from protean.exceptions import ValidationError
from pytest_bdd import parsers, scenarios, when

from loyalty.reward.reward_account import RewardAccount

scenarios("features/rewards_lifecycle.feature")


@when("a customer enrols in the rewards program", target_fixture="account")
def enrol():
    return RewardAccount.enroll(customer_id="cust-bdd-new")


@when(parsers.cfparse("the account earns {points:d} points"))
def earn(account, points, error):
    try:
        account.earn_points(points)
    except ValidationError as exc:
        error["exc"] = exc


@when(parsers.cfparse("the account redeems {points:d} points"))
def redeem(account, points, error):
    try:
        account.redeem_points(points)
    except ValidationError as exc:
        error["exc"] = exc


@when("the account is closed")
def close(account):
    account.close()
