"""Value objects for the Example aggregate."""

from protean.fields import String

from shopstream.domain import customer


@customer.value_object
class Address:
    """Example value object for demonstration."""

    street = String(max_length=100)
    city = String(max_length=50)
    state = String(max_length=50)
    postal_code = String(max_length=10)
    country = String(max_length=50, default="USA")
