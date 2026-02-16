"""Tests for Customer.update_profile() behavior."""

from datetime import date

from identity.customer.customer import Customer
from identity.customer.events import ProfileUpdated
from identity.shared.email import EmailAddress


def _make_customer(**overrides):
    defaults = {
        "external_id": "EXT-001",
        "email": EmailAddress(address="test@example.com"),
    }
    defaults.update(overrides)
    return Customer(**defaults)


class TestUpdateProfile:
    def test_update_profile_changes_name(self):
        customer = Customer.register(
            external_id="EXT-001",
            email="test@example.com",
            first_name="John",
            last_name="Doe",
        )
        customer._events.clear()

        customer.update_profile(first_name="Jane", last_name="Smith")
        assert customer.profile.first_name == "Jane"
        assert customer.profile.last_name == "Smith"

    def test_update_profile_with_phone(self):
        customer = Customer.register(
            external_id="EXT-001",
            email="test@example.com",
            first_name="John",
            last_name="Doe",
        )
        customer._events.clear()

        customer.update_profile(
            first_name="John",
            last_name="Doe",
            phone="+1-555-999-8888",
        )
        assert customer.profile.phone.number == "+1-555-999-8888"

    def test_update_profile_with_date_of_birth(self):
        customer = Customer.register(
            external_id="EXT-001",
            email="test@example.com",
            first_name="John",
            last_name="Doe",
        )
        customer._events.clear()

        dob = date(1985, 3, 20)
        customer.update_profile(
            first_name="John",
            last_name="Doe",
            date_of_birth=dob,
        )
        assert customer.profile.date_of_birth == dob

    def test_update_profile_raises_event(self):
        customer = Customer.register(
            external_id="EXT-001",
            email="test@example.com",
            first_name="John",
            last_name="Doe",
        )
        customer._events.clear()

        customer.update_profile(
            first_name="Jane",
            last_name="Smith",
            phone="+1-555-123-4567",
        )
        assert len(customer._events) == 1
        event = customer._events[0]
        assert isinstance(event, ProfileUpdated)
        assert event.customer_id == str(customer.id)
        assert event.first_name == "Jane"
        assert event.last_name == "Smith"
        assert event.phone == "+1-555-123-4567"

    def test_update_profile_clears_optional_fields(self):
        customer = Customer.register(
            external_id="EXT-001",
            email="test@example.com",
            first_name="John",
            last_name="Doe",
            phone="+1-555-123-4567",
        )
        customer._events.clear()

        customer.update_profile(first_name="John", last_name="Doe")
        assert customer.profile.phone is None
        assert customer.profile.date_of_birth is None
