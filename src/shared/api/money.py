"""Pydantic types for money in API requests and responses.

A request may send an amount as a JSON number or as a string. A response sends
it as a string with 4 places, such as ``"49.9900"``, so a client never reads
money back through a binary float.
"""

from decimal import Decimal
from typing import Annotated

from pydantic import AfterValidator, PlainSerializer

from shared.money import has_more_than_four_places, to_money


def _four_place_money(value: Decimal) -> Decimal:
    # A JSON number such as 0.1 + 0.2 arrives with every digit of the float
    # (0.30000000000000004). That is float error and is rounded off. A real
    # fifth place is refused rather than rounded to a different amount.
    if has_more_than_four_places(value):
        raise ValueError(f"Amount ({value}) must have no more than 4 decimal places")
    return to_money(value)


MoneyIn = Annotated[Decimal, AfterValidator(_four_place_money)]
"""A request amount: a JSON number or a string, returned as a 4-place ``Decimal``."""

MoneyOut = Annotated[Decimal, PlainSerializer(lambda value: str(to_money(value)), return_type=str)]
"""A response amount, sent as a 4-place string. A ``Decimal`` keeps the places
it was given, so the memory store returns ``Decimal("49.99")``, while a
``NUMERIC(19, 4)`` column in Postgres returns ``Decimal("49.9900")``. Padding to
4 places sends both as ``"49.9900"``."""
