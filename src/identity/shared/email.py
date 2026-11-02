"""EmailAddress value object for validated email addresses."""

from protean import invariant
from protean.fields import String

from identity.domain import identity


@identity.value_object
class EmailAddress:
    """A validated email address conforming to standard format rules.

    Enforces structural validity: exactly one @, valid local and domain parts,
    no consecutive dots, no forbidden characters. Used across contexts wherever
    an email is required.
    """

    address: str = String(required=True, max_length=254)

    @invariant.post
    def verify_email_address(self) -> None:
        """Ensure that the email address follows a basic valid structure."""
        if not _is_valid_email(self.address):
            raise ValueError(f"Invalid email address: {self.address!r}")


_FORBIDDEN_CHARS = (";", ",", "(", ")", '"', ":", "<", ">", "[", "]", "\\")


def _is_valid_email(email: str) -> bool:
    if any(whitespace in email for whitespace in " \t\n") or email.count("@") != 1:
        return False

    local_part, domain_part = email.split("@", 1)
    return (
        _is_valid_local_part(local_part)
        and _is_valid_domain_part(domain_part)
        and not _has_forbidden_char(email, domain_part)
    )


def _is_ip_literal(domain_part: str) -> bool:
    return domain_part.startswith("[") and domain_part.endswith("]")


def _is_valid_local_part(local_part: str) -> bool:
    return (
        bool(local_part) and not local_part.startswith(".") and not local_part.endswith(".") and ".." not in local_part
    )


def _is_valid_domain_part(domain_part: str) -> bool:
    if not domain_part or domain_part.startswith(".") or domain_part.endswith(".") or ".." in domain_part:
        return False
    if _is_ip_literal(domain_part):
        return True
    labels = domain_part.split(".")
    return len(labels) > 1 and not any(label.startswith("-") or label.endswith("-") for label in labels)


def _has_forbidden_char(email: str, domain_part: str) -> bool:
    # With an IP literal domain (user@[192.168.0.1]) brackets are allowed anywhere in the address.
    allowed = "[]" if _is_ip_literal(domain_part) else ""
    return any(char in email and char not in allowed for char in _FORBIDDEN_CHARS)
