"""Application tests for customer registration via domain.process()."""

from identity.customer.customer import Customer
from identity.customer.registration import RegisterCustomer
from protean import current_domain


class TestRegisterCustomerFlow:
    def test_register_customer_happy_path(self):
        command = RegisterCustomer(
            external_id="EXT-001",
            email="john@example.com",
            first_name="John",
            last_name="Doe",
        )
        customer_id = current_domain.process(command, asynchronous=False)
        assert customer_id is not None

        customer = current_domain.repository_for(Customer).get(customer_id)
        assert customer.external_id == "EXT-001"
        assert customer.email.address == "john@example.com"
        assert customer.profile.first_name == "John"
        assert customer.profile.last_name == "Doe"

    def test_register_customer_with_phone(self):
        command = RegisterCustomer(
            external_id="EXT-002",
            email="jane@example.com",
            first_name="Jane",
            last_name="Smith",
            phone="+1-555-123-4567",
        )
        customer_id = current_domain.process(command, asynchronous=False)
        customer = current_domain.repository_for(Customer).get(customer_id)
        assert customer.profile.phone.number == "+1-555-123-4567"

    def test_register_customer_with_date_of_birth(self):
        command = RegisterCustomer(
            external_id="EXT-003",
            email="bob@example.com",
            first_name="Bob",
            last_name="Jones",
            date_of_birth="1990-05-15",
        )
        customer_id = current_domain.process(command, asynchronous=False)
        customer = current_domain.repository_for(Customer).get(customer_id)
        assert str(customer.profile.date_of_birth) == "1990-05-15"

    def test_register_customer_stores_events(self):
        command = RegisterCustomer(
            external_id="EXT-004",
            email="alice@example.com",
            first_name="Alice",
            last_name="Brown",
        )
        current_domain.process(command, asynchronous=False)

        messages = current_domain.event_store.store.read("identity::customer")
        customer_registered_events = [
            m
            for m in messages
            if m.metadata and m.metadata.headers and m.metadata.headers.type == "Identity.CustomerRegistered.v1"
        ]
        assert len(customer_registered_events) >= 1
