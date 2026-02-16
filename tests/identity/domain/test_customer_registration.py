"""Tests for Customer.register() factory method."""

from identity.customer.customer import Customer, CustomerStatus, CustomerTier
from identity.customer.events import CustomerRegistered


class TestCustomerRegister:
    def test_register_creates_customer(self):
        customer = Customer.register(
            external_id="EXT-001",
            email="john@example.com",
            first_name="John",
            last_name="Doe",
        )
        assert customer.external_id == "EXT-001"
        assert customer.email.address == "john@example.com"
        assert customer.profile.first_name == "John"
        assert customer.profile.last_name == "Doe"
        assert customer.status == CustomerStatus.ACTIVE.value
        assert customer.tier == CustomerTier.STANDARD.value
        assert customer.registered_at is not None

    def test_register_with_phone(self):
        customer = Customer.register(
            external_id="EXT-002",
            email="jane@example.com",
            first_name="Jane",
            last_name="Smith",
            phone="+1-555-123-4567",
        )
        assert customer.profile.phone.number == "+1-555-123-4567"

    def test_register_with_date_of_birth(self):
        from datetime import date

        customer = Customer.register(
            external_id="EXT-003",
            email="bob@example.com",
            first_name="Bob",
            last_name="Jones",
            date_of_birth=date(1990, 5, 15),
        )
        assert customer.profile.date_of_birth == date(1990, 5, 15)

    def test_register_raises_customer_registered_event(self):
        customer = Customer.register(
            external_id="EXT-004",
            email="alice@example.com",
            first_name="Alice",
            last_name="Brown",
        )
        assert len(customer._events) == 1
        event = customer._events[0]
        assert isinstance(event, CustomerRegistered)
        assert event.customer_id == str(customer.id)
        assert event.external_id == "EXT-004"
        assert event.email == "alice@example.com"
        assert event.first_name == "Alice"
        assert event.last_name == "Brown"
        assert event.registered_at is not None

    def test_register_profile_has_no_phone_by_default(self):
        customer = Customer.register(
            external_id="EXT-005",
            email="carol@example.com",
            first_name="Carol",
            last_name="White",
        )
        assert customer.profile.phone is None

    def test_register_profile_has_no_dob_by_default(self):
        customer = Customer.register(
            external_id="EXT-006",
            email="dave@example.com",
            first_name="Dave",
            last_name="Green",
        )
        assert customer.profile.date_of_birth is None
