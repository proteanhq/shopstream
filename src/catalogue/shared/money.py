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
    """A monetary amount paired with an ISO 4217 currency code.

    Supports 20 major currencies. Amount must be non-negative. Used for
    representing prices, totals, and other financial values.

    Examples:
        >>> price = Money(amount=19.99, currency="USD")
        >>> (price.amount, price.currency)
        (19.99, 'USD')
        >>> Money(amount=5).currency  # currency defaults to USD
        'USD'
        >>> try:
        ...     Money(amount=-1, currency="USD")
        ... except ValidationError:
        ...     print("negative amount rejected")
        negative amount rejected
        >>> try:
        ...     Money(amount=5, currency="XYZ")
        ... except ValidationError:
        ...     print("unsupported currency rejected")
        unsupported currency rejected
    """

    amount: Float(required=True, min_value=0.0)
    currency: String(max_length=3, default="USD")

    @invariant.post
    def currency_must_be_valid_iso_4217(self):
        if self.currency not in VALID_CURRENCIES:
            raise ValidationError({"currency": [f"Unsupported currency: {self.currency}"]})
