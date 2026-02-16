"""SKU value object for stock keeping unit codes."""

import re

from protean import invariant
from protean.exceptions import ValidationError
from protean.fields import String

from catalogue.domain import catalogue


@catalogue.value_object
class SKU:
    """Value object for stock keeping unit codes.

    Format: alphanumeric + hyphens, 3-50 chars.
    E.g., "ELEC-PHN-001", "SHOE-RUN-BLK-42"
    """

    code: String(required=True, max_length=50, min_length=3)

    @invariant.post
    def code_must_be_valid_format(self):
        code = self.code

        if not re.match(r"^[A-Za-z0-9-]+$", code):
            raise ValidationError({"code": ["SKU must contain only alphanumeric characters and hyphens"]})

        if code.startswith("-") or code.endswith("-"):
            raise ValidationError({"code": ["SKU must not start or end with a hyphen"]})

        if "--" in code:
            raise ValidationError({"code": ["SKU must not contain consecutive hyphens"]})
