"""Shared value objects used across multiple aggregates."""

from protean import invariant
from protean.fields import String

from identity.domain import identity


@identity.value_object
class EmailAddress:
    """Value object for email addresses."""

    address = String(required=True, max_length=254)

    @invariant.post
    def verify_email_address(self):
        """Ensure that the email address follows a basic valid structure."""
        email = self.address

        if " " in email or "\t" in email or "\n" in email:
            raise ValueError(f"Invalid email address: {email!r}")

        if email.count("@") != 1:
            raise ValueError(f"Invalid email address: {email!r}")

        local_part, domain_part = email.split("@", 1)

        if not local_part or local_part.startswith(".") or local_part.endswith("."):
            raise ValueError(f"Invalid email address: {email!r}")

        if not domain_part or domain_part.startswith(".") or domain_part.endswith("."):
            raise ValueError(f"Invalid email address: {email!r}")

        if domain_part.startswith("-") or domain_part.endswith("-"):
            raise ValueError(f"Invalid email address: {email!r}")

        if "." not in domain_part and not (domain_part.startswith("[") and domain_part.endswith("]")):
            raise ValueError(f"Invalid email address: {email!r}")

        if ".." in local_part or ".." in domain_part:
            raise ValueError(f"Invalid email address: {email!r}")

        for forbidden in (";", ",", "(", ")", '"', ":", "<", ">", "[", "]", "\\"):
            if forbidden in email and not (
                forbidden in "[]" and domain_part.startswith("[") and domain_part.endswith("]")
            ):
                raise ValueError(f"Invalid email address: {email!r}")
