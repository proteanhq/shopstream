"""Application tests for profile management via domain.process()."""

from identity.customer.customer import Customer
from identity.customer.profile import UpdateProfile
from identity.customer.registration import RegisterCustomer
from protean import current_domain


class TestUpdateProfileFlow:
    def _register_customer(self):
        command = RegisterCustomer(
            external_id="EXT-001",
            email="test@example.com",
            first_name="John",
            last_name="Doe",
        )
        return current_domain.process(command, asynchronous=False)

    def test_update_profile_happy_path(self):
        customer_id = self._register_customer()

        command = UpdateProfile(
            customer_id=customer_id,
            first_name="Jane",
            last_name="Smith",
        )
        current_domain.process(command, asynchronous=False)

        customer = current_domain.repository_for(Customer).get(customer_id)
        assert customer.profile.first_name == "Jane"
        assert customer.profile.last_name == "Smith"

    def test_update_profile_with_date_of_birth(self):
        """Cover profile.py line 19: date_of_birth parsing."""
        customer_id = self._register_customer()

        command = UpdateProfile(
            customer_id=customer_id,
            first_name="John",
            last_name="Doe",
            date_of_birth="1990-05-15",
        )
        current_domain.process(command, asynchronous=False)

        customer = current_domain.repository_for(Customer).get(customer_id)
        assert str(customer.profile.date_of_birth) == "1990-05-15"

    def test_update_profile_with_phone(self):
        customer_id = self._register_customer()

        command = UpdateProfile(
            customer_id=customer_id,
            first_name="John",
            last_name="Doe",
            phone="+1-555-999-8888",
        )
        current_domain.process(command, asynchronous=False)

        customer = current_domain.repository_for(Customer).get(customer_id)
        assert customer.profile.phone.number == "+1-555-999-8888"
