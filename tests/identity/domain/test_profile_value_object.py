import datetime

import pytest
from identity.customer.customer import Profile
from identity.shared.phone import PhoneNumber
from protean.exceptions import ValidationError
from protean.utils import DomainObjects


def test_profile_element_type():
    assert Profile.element_type == DomainObjects.VALUE_OBJECT


def test_profile_requires_first_name_and_last_name():
    with pytest.raises(ValidationError):
        Profile()


def test_profile_requires_first_name():
    with pytest.raises(ValidationError):
        Profile(last_name="Doe")


def test_profile_requires_last_name():
    with pytest.raises(ValidationError):
        Profile(first_name="John")


class TestProfileConstruction:
    def test_minimal_profile(self):
        profile = Profile(first_name="John", last_name="Doe")
        assert profile.first_name == "John"
        assert profile.last_name == "Doe"
        assert profile.phone is None
        assert profile.date_of_birth is None

    def test_profile_with_phone(self):
        profile = Profile(
            first_name="Jane",
            last_name="Smith",
            phone=PhoneNumber(number="+1-555-123-4567"),
        )
        assert profile.first_name == "Jane"
        assert profile.last_name == "Smith"
        assert profile.phone.number == "+1-555-123-4567"

    def test_profile_with_date_of_birth(self):
        dob = datetime.date(1990, 5, 15)
        profile = Profile(
            first_name="John",
            last_name="Doe",
            date_of_birth=dob,
        )
        assert profile.date_of_birth == dob

    def test_profile_with_all_fields(self):
        dob = datetime.date(1985, 12, 25)
        profile = Profile(
            first_name="Alice",
            last_name="Wonderland",
            phone=PhoneNumber(number="(555) 987-6543"),
            date_of_birth=dob,
        )
        assert profile.first_name == "Alice"
        assert profile.last_name == "Wonderland"
        assert profile.phone.number == "(555) 987-6543"
        assert profile.date_of_birth == dob


class TestProfileMaxLength:
    def test_first_name_max_length(self):
        with pytest.raises(ValidationError):
            Profile(first_name="A" * 101, last_name="Doe")

    def test_last_name_max_length(self):
        with pytest.raises(ValidationError):
            Profile(first_name="John", last_name="D" * 101)

    def test_first_name_at_max_length(self):
        profile = Profile(first_name="A" * 100, last_name="Doe")
        assert len(profile.first_name) == 100

    def test_last_name_at_max_length(self):
        profile = Profile(first_name="John", last_name="D" * 100)
        assert len(profile.last_name) == 100
