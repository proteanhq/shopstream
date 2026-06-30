"""BDD steps for points transfer (TransferPoints domain service)."""

from protean.exceptions import ValidationError
from pytest_bdd import given, parsers, scenarios, then, when

from loyalty.reward.reward_account import RewardAccount
from loyalty.reward.transfer import TransferPoints

scenarios("features/points_transfer.feature")


def _funded(customer_id, points):
    account = RewardAccount.enroll(customer_id=customer_id)
    if points:
        account.earn_points(points)
    account._events.clear()
    return account


@given(
    parsers.cfparse("a source account with {source:d} points and a target account with {target:d} points"),
    target_fixture="accounts",
)
def two_accounts(source, target):
    return {"source": _funded("cust-src", source), "target": _funded("cust-tgt", target)}


@given(
    parsers.cfparse("a source account with {source:d} points and a closed target account"),
    target_fixture="accounts",
)
def source_and_closed_target(source):
    target = _funded("cust-tgt", 0)
    target.close()
    return {"source": _funded("cust-src", source), "target": target}


@when(parsers.cfparse("{amount:d} points are transferred from source to target"))
def transfer(accounts, amount, error):
    try:
        TransferPoints(accounts["source"], accounts["target"])(amount)
    except ValidationError as exc:
        error["exc"] = exc


@then(parsers.cfparse("the source balance is {balance:d}"))
def source_balance_is(accounts, balance):
    assert accounts["source"].points_balance == balance


@then(parsers.cfparse("the target balance is {balance:d}"))
def target_balance_is(accounts, balance):
    assert accounts["target"].points_balance == balance


@then("the transfer fails with a validation error")
def transfer_fails(error):
    assert error["exc"] is not None
    assert isinstance(error["exc"], ValidationError)
