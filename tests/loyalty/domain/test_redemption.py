"""Domain tests for the Redemption aggregate and the voucher port."""

import pytest
from protean.exceptions import ValidationError

from loyalty.redemption.events import (
    PointsReserved,
    RedemptionCompensated,
    RedemptionCompleted,
    RedemptionRequested,
    VoucherIssuanceFailed,
    VoucherIssued,
)
from loyalty.redemption.redemption import Redemption
from loyalty.redemption.voucher import VoucherUnavailable, issue_voucher_code


def _request(points=100, reward_code="GIFT10"):
    return Redemption.request(account_id="acc-1", points=points, reward_code=reward_code)


class TestRedemptionLifecycle:
    def test_request_starts_in_requested_and_raises_event(self):
        r = _request()
        assert r.status == "requested"
        assert r.account_id == "acc-1"
        assert isinstance(r._events[-1], RedemptionRequested)

    def test_reserve_issue_complete_flow(self):
        r = _request()
        r.reserve_points()
        assert r.status == "points_reserved"
        assert isinstance(r._events[-1], PointsReserved)

        r.issue_voucher("VCHR-123")
        assert r.status == "voucher_issued"
        assert r.voucher_code == "VCHR-123"
        assert isinstance(r._events[-1], VoucherIssued)

        r.complete()
        assert r.status == "completed"
        assert isinstance(r._events[-1], RedemptionCompleted)

    def test_fail_then_compensate_flow(self):
        r = _request(points=80)
        r.reserve_points()
        r.fail_voucher("sold out")
        assert isinstance(r._events[-1], VoucherIssuanceFailed)
        assert r.failure_reason == "sold out"

        r.compensate(refunded_points=80, reason="sold out")
        assert r.status == "compensated"
        evt = r._events[-1]
        assert isinstance(evt, RedemptionCompensated)
        assert evt.refunded_points == 80

    def test_non_positive_points_rejected(self):
        with pytest.raises(ValidationError):
            Redemption.request(account_id="acc-1", points=0, reward_code="GIFT")


class TestVoucherPort:
    def test_issues_a_code_for_normal_reward(self):
        code = issue_voucher_code("GIFT10")
        assert code.startswith("VCHR-")

    def test_fail_codes_raise(self):
        with pytest.raises(VoucherUnavailable):
            issue_voucher_code("FAIL-STOCK")
