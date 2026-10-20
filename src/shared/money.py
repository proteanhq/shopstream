"""Conversion of money amounts to exact decimals.

Money fields are ``Decimal(precision=19, scale=4)``, while event and command
fields still carry money as ``float``.
"""

import math
from decimal import Decimal, InvalidOperation

MONEY_SCALE = Decimal("0.0001")

# Float arithmetic on amounts below about 1e9 leaves an error under 1e-7, even
# for a subtraction such as 100 - 99.99 whose error is relative to the
# operands, not to the result. A stray fifth decimal place moves the amount by
# at least 1e-5. Above 1e-7, the tolerance grows to a few units in the last
# place of the float, because a large float cannot hold its digits more
# exactly than that.
_FLOAT_ERROR = 1e-7
_ULPS = 4


def to_money(value: float | int | Decimal | None) -> Decimal:
    """Convert an amount to a ``Decimal`` rounded half-even to 4 decimal places.

    A float goes through ``str`` first, because ``Decimal(0.1)`` keeps the full
    binary expansion of the float. Rounding is needed as well: a float sum
    such as ``0.1 + 0.2`` is ``0.30000000000000004``, which a scale-4 field
    rejects. ``None`` becomes zero.

    >>> to_money(0.1) + to_money(0.2)
    Decimal('0.3000')
    >>> to_money(0.1 + 0.2)
    Decimal('0.3000')
    >>> to_money(None)
    Decimal('0.0000')
    """
    if value is None:
        return Decimal(0).quantize(MONEY_SCALE)
    if isinstance(value, bool) or not isinstance(value, float | int | Decimal):
        raise TypeError(f"Money amount must be a number, got {type(value).__name__}")
    amount = Decimal(str(value)) if isinstance(value, float) else Decimal(value)
    if not amount.is_finite():
        raise ValueError(f"Money amount must be finite, got {value}")
    try:
        return amount.quantize(MONEY_SCALE)
    except InvalidOperation:
        # quantize fails once the result needs more than the 28 digits of the
        # default decimal context, for example 1e30 at 4 places.
        raise ValueError(f"Money amount is too large, got {value}") from None


def has_more_than_four_places(value: float) -> bool:
    """Tell whether a float amount carries a fifth decimal place or beyond.

    Float error from arithmetic does not count: ``0.1 + 0.2`` and
    ``100 - 99.99`` are 4-place amounts, ``10.00004`` is not. A place that
    moves the amount by less than 1e-7 counts as float error, so it is rounded
    off rather than caught.

    >>> has_more_than_four_places(0.1 + 0.2)
    False
    >>> has_more_than_four_places(100 - 99.99)
    False
    >>> has_more_than_four_places(10.00004)
    True
    """
    tolerance = max(_FLOAT_ERROR, _ULPS * math.ulp(value))
    return abs(value - float(to_money(value))) > tolerance
