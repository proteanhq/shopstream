"""A tiny voucher-issuing port that can fail.

Stands in for an external voucher provider. Issuance fails deterministically when the
reward code signals it (contains ``FAIL``), so the saga's compensation path can be driven
in tests and demos without real flakiness.
"""

import secrets
import string


class VoucherUnavailable(Exception):
    """Raised when a voucher cannot be issued for a reward code."""


def issue_voucher_code(reward_code):
    """Return a fresh voucher code, or raise ``VoucherUnavailable`` for ``FAIL`` codes."""
    if "FAIL" in (reward_code or "").upper():
        raise VoucherUnavailable(f"No vouchers available for reward '{reward_code}'")
    suffix = "".join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(8))
    return f"VCHR-{suffix}"
