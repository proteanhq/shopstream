"""Conversion of money amounts to exact decimals.

Money fields are ``Decimal(precision=19, scale=4)``, while event and command
fields still carry money as ``float``.
"""

import math
from decimal import Decimal

MONEY_SCALE = Decimal("0.0001")

# A float sum such as 0.1 + 0.2 misses its 4-place value by a few units in the
# last place, about 1e-16 of the value. A stray fifth decimal place, such as
# 10.00004, misses by far more than this tolerance at any amount below 1e8.
_FLOAT_ERROR = 1e-13


def to_money(value: float | int | Decimal | None) -> Decimal:
    """Convert an amount to a ``Decimal`` rounded to 4 decimal places.

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
    return amount.quantize(MONEY_SCALE)


def has_more_than_four_places(value: float) -> bool:
    """Tell whether a float amount carries a fifth decimal place or beyond.

    Float error from arithmetic does not count: ``0.1 + 0.2`` is a 4-place
    amount, ``10.00004`` is not.

    >>> has_more_than_four_places(0.1 + 0.2)
    False
    >>> has_more_than_four_places(10.00004)
    True
    """
    return not math.isclose(value, float(to_money(value)), rel_tol=_FLOAT_ERROR, abs_tol=0.0)
