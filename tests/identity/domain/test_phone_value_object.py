import pytest
from identity.shared.phone import PhoneNumber
from protean.exceptions import ValidationError
from protean.utils import DomainObjects


def test_phone_number_element_type():
    assert PhoneNumber.element_type == DomainObjects.VALUE_OBJECT


def test_phone_number_requires_number():
    with pytest.raises(ValidationError):
        PhoneNumber()


def test_phone_number_has_max_length():
    with pytest.raises(ValidationError):
        PhoneNumber(number="+" + "1" * 20)


@pytest.mark.parametrize(
    "number",
    [
        "+1-555-123-4567",
        "(555) 123-4567",
        "+44 20 7946 0958",
        "555-1234",
        "+1 (555) 123-4567",
        "1234567890",
        "+91 98765 43210",
        "+1-800-555-0199",
        "+61 2 1234 5678",
        "123",
    ],
    ids=[
        "us_international",
        "us_parens",
        "uk_international",
        "local_short",
        "us_full_parens",
        "digits_only",
        "india_international",
        "us_toll_free",
        "australia_international",
        "minimal_digits",
    ],
)
def test_valid_phone_numbers(number):
    vo = PhoneNumber(number=number)
    assert vo.number == number


@pytest.mark.parametrize(
    "number",
    [
        "",
        "abc-defg",
        "+1-555-abc-4567",
        "555.123.4567",
        "phone: 555-1234",
        "+",
        "---",
        "()",
        "123@456",
        "555#1234",
    ],
    ids=[
        "empty",
        "all_letters",
        "letters_mixed",
        "dots_separator",
        "text_prefix",
        "plus_only",
        "dashes_only",
        "parens_only",
        "at_sign",
        "hash_sign",
    ],
)
def test_invalid_phone_numbers(number):
    with pytest.raises((ValueError, ValidationError)):
        PhoneNumber(number=number)
