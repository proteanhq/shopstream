"""BDD steps for the Redemption aggregate state machine and the voucher port."""

from pytest_bdd import parsers, scenarios, then, when

from loyalty.redemption.redemption import Redemption
from loyalty.redemption.voucher import VoucherUnavailable, issue_voucher_code

scenarios("features/redemption.feature")


@when(parsers.cfparse("a redemption is requested for {points:d} points"), target_fixture="redemption")
def request_redemption(points):
    return Redemption.request(account_id="acc-bdd", points=points, reward_code="GIFT10")


@when("points are reserved")
def reserve(redemption):
    redemption.reserve_points()


@when(parsers.cfparse('a voucher "{code}" is issued'))
def issue(redemption, code):
    redemption.issue_voucher(code)


@when(parsers.cfparse('voucher issuance fails with reason "{reason}"'))
def fail(redemption, reason):
    redemption.fail_voucher(reason)


@when("the redemption is completed")
def complete(redemption):
    redemption.complete()


@when(parsers.cfparse("the redemption is compensated for {points:d} points"))
def compensate(redemption, points):
    redemption.compensate(refunded_points=points, reason="sold out")


@when(parsers.cfparse('a voucher code is requested for reward "{reward_code}"'), target_fixture="voucher_result")
def request_voucher_code(reward_code):
    try:
        return {"code": issue_voucher_code(reward_code), "error": None}
    except VoucherUnavailable as exc:
        return {"code": None, "error": exc}


@then("voucher issuance is unavailable")
def voucher_unavailable(voucher_result):
    assert isinstance(voucher_result["error"], VoucherUnavailable)


@then("a voucher code is returned")
def voucher_returned(voucher_result):
    assert voucher_result["code"] and voucher_result["code"].startswith("VCHR-")
