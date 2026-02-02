from identity.domain import identity
from identity.model.value_objects import EmailAddress
from protean.fields import String, ValueObject


@identity.aggregate
class Customer:
    """Customer aggregate root."""

    # Fields
    external_id = String(required=True, max_length=255, unique=True)
    email = ValueObject(EmailAddress, required=True)
