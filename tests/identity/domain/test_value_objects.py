"""Tests for value objects in the identity domain."""

import pytest
from identity.model.value_objects import EmailAddress
from protean.exceptions import ValidationError
from protean.utils import DomainObjects


class TestEmailAddress:
    """Test suite for EmailAddress value object."""

    def test_email_address_is_value_object(self):
        """Test that EmailAddress is registered as a value object."""
        assert EmailAddress.element_type == DomainObjects.VALUE_OBJECT

    @pytest.mark.parametrize(
        "email_address",
        [
            "user@example.com",
            "user@mail.example.com",
            "user+tag@example.com",
            "first.last@example.com",
            "user@my-company.com",
            "user123@example456.com",
            "user_name@example.com",
            "user-name@example.com",
            "user.name@example.com",
            "User@Example.COM",
            "user@example.co.uk",
            "user@[192.168.1.1]",
        ],
        ids=[
            "basic",
            "subdomain",
            "plus_addressing",
            "dots_in_local",
            "hyphen_in_domain",
            "with_numbers",
            "underscore_in_local",
            "hyphen_in_local",
            "dots_in_local_2",
            "case_preserved",
            "international_domain",
            "ip_domain",
        ],
    )
    def test_create_valid_email_addresses(self, email_address):
        """Test creating EmailAddress with various valid formats."""
        email = EmailAddress(address=email_address)
        assert email.address == email_address

    def test_create_email_with_max_length(self):
        """Test creating an EmailAddress at maximum allowed length (254 chars)."""
        # Create a valid email address that is exactly 254 characters
        # Format: local@domain (max 64 chars for local, rest for domain)
        local_part = "a" * 60  # 60 chars
        domain_part = "b" * 189 + ".com"  # 189 + 4 = 193 chars
        email_str = f"{local_part}@{domain_part}"  # 60 + 1 + 193 = 254 chars

        email = EmailAddress(address=email_str)
        assert email.address == email_str
        assert len(email.address) == 254

    @pytest.mark.parametrize(
        "invalid_email,error_type,match_pattern",
        [
            ("userexample.com", ValueError, "Invalid email address: 'userexample.com'"),
            ("@", ValueError, "Invalid email address: '@'"),
            ("user@@example.com", ValueError, "Invalid email address: 'user@@example.com'"),
            ("   ", ValueError, "Invalid email address:"),
            ("@example.com", ValueError, None),
            ("user@", ValueError, None),
            ("user@-example.com", ValueError, "Invalid email address:"),
            ("user@example-", ValueError, "Invalid email address:"),
            ("user@examplecom", ValueError, "Invalid email address:"),
            ("user..name@example.com", ValueError, "Invalid email address:"),
            ("user@example..com", ValueError, "Invalid email address:"),
            ("user;name@example.com", ValueError, "Invalid email address:"),
            ("user,name@example.com", ValueError, "Invalid email address:"),
            ("user(name)@example.com", ValueError, "Invalid email address:"),
            ('user"name"@example.com', ValueError, "Invalid email address:"),
            ("user:name@example.com", ValueError, "Invalid email address:"),
            ("user<name>@example.com", ValueError, "Invalid email address:"),
            ("user\\name@example.com", ValueError, "Invalid email address:"),
        ],
        ids=[
            "missing_at_symbol",
            "only_at_symbol",
            "multiple_at_symbols",
            "whitespace_only",
            "starts_with_at",
            "ends_with_at",
            "domain_starts_with_hyphen",
            "domain_ends_with_hyphen",
            "domain_without_dot_not_ip",
            "consecutive_dots_in_local",
            "consecutive_dots_in_domain",
            "semicolon_in_email",
            "comma_in_email",
            "parentheses_in_email",
            "quotes_in_email",
            "colon_in_email",
            "angle_brackets_in_email",
            "backslash_in_email",
        ],
    )
    def test_invalid_email_formats(self, invalid_email, error_type, match_pattern):
        """Test that invalid email formats raise appropriate errors."""
        if match_pattern:
            with pytest.raises(error_type, match=match_pattern):
                EmailAddress(address=invalid_email)
        else:
            with pytest.raises(error_type):
                EmailAddress(address=invalid_email)

    @pytest.mark.parametrize(
        "invalid_input,match_pattern",
        [
            ("", "is required"),
            (None, "address"),
        ],
        ids=["empty_string", "none_value"],
    )
    def test_validation_errors(self, invalid_input, match_pattern):
        """Test that ValidationError is raised for invalid inputs."""
        with pytest.raises(ValidationError, match=match_pattern):
            EmailAddress(address=invalid_input)

    def test_email_address_required_field(self):
        """Test that address field is required."""
        with pytest.raises(ValidationError) as exc_info:
            EmailAddress()

        assert "address" in str(exc_info.value)

    def test_email_address_exceeds_max_length(self):
        """Test that EmailAddress exceeding 254 characters raises ValidationError."""
        # Create an email address longer than 254 characters
        long_email = "a" * 250 + "@test.com"  # 260 characters

        with pytest.raises(ValidationError) as exc_info:
            EmailAddress(address=long_email)

        assert "address" in str(exc_info.value)
