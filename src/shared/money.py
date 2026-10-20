"""Conversion of money amounts to exact decimals.

Money fields on events, aggregates and projections are
``Decimal(precision=19, scale=4)``. The payments commands ``InitiatePayment``
and ``RequestRefund`` take a plain ``Decimal``, and ``Payment`` refuses an
amount with more than 4 places. A ``Decimal`` event field is written to the
event store and the shared bus as a string such as ``"49.9900"``. Payloads
written before that change, and messages still on the bus from that time,
carry the amount as a JSON number, so code that reads a raw payload parses
either form with ``parse_money``.
"""

import math
from decimal import Decimal, InvalidOperation
from typing import Any

MONEY_SCALE = Decimal("0.0001")

# Float arithmetic on amounts below about 1e9 leaves an error under 1e-7, even
# for a subtraction such as 100 - 99.99 whose error is relative to the
# operands, not to the result. A stray fifth decimal place moves the amount by
# at least 1e-5. Above 1e-7, the tolerance grows to a few units in the last
# place of the float, because a large float cannot hold its digits more
# exactly than that. It stops at half of 1e-5, so it never swallows a real
# fifth place.
_FLOAT_ERROR = 1e-7
_ULPS = 4
_MAX_TOLERANCE = 5e-6

# Float error shows only in the full digits of a float, such as
# 0.30000000000000004 or 0.0500000000001819 (from 5000.05 - 5000). An amount
# written with fewer significant digits, such as 49.99000001, is exactly what
# the caller wrote.
_FLOAT_ERROR_DIGITS = 15


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


def parse_money(value: float | int | str | Decimal | None) -> Decimal:
    """Parse an amount read from a raw payload into a 4-place ``Decimal``.

    A payload carries money as a JSON number (events written before money
    fields became ``Decimal``) or as a string such as ``"49.9900"``. Both
    forms go through ``str``, then are rounded half-even as ``to_money``
    does. ``None`` becomes zero. A bool, a string that is not a plain ASCII
    number (``"1_000"`` and ``"１２"`` are refused), and a non-finite amount
    raise ``ValueError``.

    >>> parse_money("49.9900")
    Decimal('49.9900')
    >>> parse_money(0.1 + 0.2)
    Decimal('0.3000')
    """
    if value is None:
        return to_money(None)
    if isinstance(value, bool) or not isinstance(value, float | int | str | Decimal):
        raise ValueError(f"Money amount must be a number or a numeric string, got {type(value).__name__}")
    text = str(value).strip()
    # Decimal also reads "1_000" and non-ASCII digits such as "１２". A client
    # does not send money in those forms, so they are refused as not a number.
    if not text.isascii() or "_" in text:
        raise ValueError(f"Money amount is not a number: {value!r}")
    try:
        amount = Decimal(text)
    except InvalidOperation:
        raise ValueError(f"Money amount is not a number: {value!r}") from None
    return to_money(amount)


def money_fields_as_text(data: dict[str, Any], *keys: str) -> dict[str, Any]:
    """Rewrite the named money fields of a payload dict as 4-place strings.

    Upcasters use it on old event payloads. Event versions before the
    ``Decimal`` change stored money as floats, and some of those floats carry
    arithmetic error (``3.3000000000000003``) that a scale-4 field rejects on
    replay. Each named field that is present and not ``None`` goes through
    ``parse_money``. Fields that are missing or
    ``None`` are left alone, so optional fields keep their meaning.

    >>> money_fields_as_text({"amount": 0.1 + 0.2, "tax": None}, "amount", "tax")
    {'amount': '0.3000', 'tax': None}
    """
    for key in keys:
        if data.get(key) is not None:
            data[key] = str(parse_money(data[key]))
    return data


def has_more_than_four_places(value: float | Decimal) -> bool:
    """Tell whether an amount carries a fifth decimal place or beyond.

    Float error from arithmetic does not count: ``0.1 + 0.2`` and
    ``100 - 99.99`` are 4-place amounts, ``10.00004`` is not. An amount counts
    as float error only when it is written with the full digits of a float (15
    or more significant digits) and sits within the tolerance of a 4-place
    amount. The tolerance is 1e-7, or 4 units in the last place of the float
    when that is larger (above about 1.3e8), and never more than 5e-6.

    A ``Decimal`` is judged the same way, and must also be the exact digits of
    a float, because a JSON number such as ``0.30000000000000004`` reaches the
    API as a ``Decimal`` with every digit of the float. A string such as
    ``"49.99000001"`` or ``"123456789012.12345"`` is a fifth place.

    >>> has_more_than_four_places(0.1 + 0.2)
    False
    >>> has_more_than_four_places(100 - 99.99)
    False
    >>> has_more_than_four_places(10.00004)
    True
    >>> has_more_than_four_places(Decimal("0.30000000000000004"))
    False
    >>> has_more_than_four_places(Decimal("49.99000001"))
    True
    """
    amount = value if isinstance(value, Decimal) else Decimal(repr(value))
    scaled = amount.scaleb(4)
    if scaled.is_finite() and scaled == scaled.to_integral_value():
        return False
    if len(amount.normalize().as_tuple().digits) < _FLOAT_ERROR_DIGITS:
        return True
    number = float(amount)
    if Decimal(repr(number)) != amount:
        return True
    tolerance = min(max(_FLOAT_ERROR, _ULPS * math.ulp(number)), _MAX_TOLERANCE)
    return abs(number - float(to_money(number))) > tolerance
