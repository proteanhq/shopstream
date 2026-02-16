"""PhoneNumber value object for validated phone numbers."""

import re

from protean import invariant
from protean.fields import String

from identity.domain import identity


@identity.value_object
class PhoneNumber:
    """Value object for phone numbers.

    Accepts digits, spaces, hyphens, parentheses, and an optional leading +.
    """

    number: String(required=True, max_length=20)

    @invariant.post
    def validate_phone_format(self):
        """Ensure the phone number contains only valid characters and structure."""
        number = self.number

        # Must contain at least one digit
        if not re.search(r"\d", number):
            raise ValueError(f"Invalid phone number: {number!r}")

        # Only allow: digits, spaces, hyphens, parentheses, leading +
        if not re.match(r"^\+?[\d\s\-()]+$", number):
            raise ValueError(f"Invalid phone number: {number!r}")
