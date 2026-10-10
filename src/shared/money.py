"""Conversion of money amounts to exact decimals.

Money fields are ``Decimal(precision=19, scale=4)``, while event and command
fields still carry money as ``float``.
"""

from decimal import Decimal

MONEY_SCALE = Decimal("0.0001")


def to_money(value: float | int | Decimal | None) -> Decimal:
    """Convert an amount to a ``Decimal`` rounded to 4 decimal places.

    A float goes through ``str`` first, because ``Decimal(0.1)`` keeps the full
    binary expansion of the float. Rounding is needed as well: a float total
    such as ``3 * 19.99`` is ``59.970000000000006``, which a scale-4 field
    rejects. ``None`` becomes zero.

    >>> to_money(0.1) + to_money(0.2)
    Decimal('0.3000')
    >>> to_money(3 * 19.99)
    Decimal('59.9700')
    >>> to_money(None)
    Decimal('0.0000')
    """
    if value is None:
        return Decimal(0).quantize(MONEY_SCALE)
    if isinstance(value, float):
        value = Decimal(str(value))
    return Decimal(value).quantize(MONEY_SCALE)
