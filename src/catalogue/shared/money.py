"""Money value object for monetary amounts with currency."""

from protean import invariant
from protean.exceptions import ValidationError
from protean.fields import Float, String

from catalogue.domain import catalogue

VALID_CURRENCIES = frozenset(
    {
        "USD",
        "EUR",
        "GBP",
        "JPY",
        "CAD",
        "AUD",
        "CHF",
        "CNY",
        "INR",
        "MXN",
        "BRL",
        "KRW",
        "SGD",
        "HKD",
        "NOK",
        "SEK",
        "DKK",
        "NZD",
        "ZAR",
        "TWD",
    }
)


@catalogue.value_object
class Money:
    """Value object representing a monetary amount with currency."""

    amount: Float(required=True, min_value=0.0)
    currency: String(max_length=3, default="USD")

    @invariant.post
    def currency_must_be_valid_iso_4217(self):
        if self.currency not in VALID_CURRENCIES:
            raise ValidationError({"currency": [f"Unsupported currency: {self.currency}"]})
