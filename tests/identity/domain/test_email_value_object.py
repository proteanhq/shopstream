import pytest
from identity.shared.email import EmailAddress
from protean.exceptions import ValidationError


def test_email_address_element_type():
    from protean.utils import DomainObjects

    assert EmailAddress.element_type == DomainObjects.VALUE_OBJECT


def test_email_address_requires_address():
    with pytest.raises(ValidationError):
        EmailAddress()


def test_email_address_has_max_length():
    with pytest.raises(ValidationError):
        EmailAddress(address="a" * 243 + "@example.com")


@pytest.mark.parametrize(
    "email",
    [
        "user@example.com",
        "user.name@example.com",
        "user+tag@example.com",
        "user@sub.domain.com",
        "user@example.co.uk",
        "user123@example.com",
        "user@[127.0.0.1]",
        "a@b.cc",
    ],
    ids=[
        "simple",
        "dotted_local",
        "plus_tag",
        "subdomain",
        "country_tld",
        "numeric_local",
        "ip_literal",
        "minimal",
    ],
)
def test_valid_email_addresses(email):
    vo = EmailAddress(address=email)
    assert vo.address == email


@pytest.mark.parametrize(
    "email",
    [
        "",
        "missing-at-sign",
        "@no-local.com",
        "no-domain@",
        "two@@ats.com",
        "user @space.com",
        "user\t@tab.com",
        "user\n@newline.com",
        ".leading-dot@example.com",
        "trailing-dot.@example.com",
        "user@.leading-dot-domain.com",
        "user@trailing-dot-domain.",
        "user@-leading-hyphen.com",
        "user@trailing-hyphen-.com",
        "user@no-tld",
        "user@double..dot.com",
        "double..dot@example.com",
        "semi;colon@example.com",
        "com,ma@example.com",
        "par(en@example.com",
        'qu"ote@example.com',
        "col:on@example.com",
        "less<than@example.com",
        "back\\slash@example.com",
    ],
    ids=[
        "empty",
        "no_at",
        "no_local",
        "no_domain",
        "double_at",
        "space_local",
        "tab_local",
        "newline_local",
        "leading_dot_local",
        "trailing_dot_local",
        "leading_dot_domain",
        "trailing_dot_domain",
        "leading_hyphen_domain",
        "trailing_hyphen_domain",
        "no_tld",
        "double_dot_domain",
        "double_dot_local",
        "semicolon",
        "comma",
        "parenthesis",
        "quote",
        "colon",
        "less_than",
        "backslash",
    ],
)
def test_invalid_email_addresses(email):
    with pytest.raises((ValueError, ValidationError)):
        EmailAddress(address=email)
