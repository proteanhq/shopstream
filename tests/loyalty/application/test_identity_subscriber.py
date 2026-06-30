"""Application tests for the loyalty CustomerRegisteredSubscriber (auto-enrolment ACL)."""

from protean import current_domain

from loyalty.reward.identity_subscriber import CustomerRegisteredSubscriber
from loyalty.reward.reward_account import RewardAccount


def _message(event_type, data):
    return {"metadata": {"headers": {"type": event_type}}, "data": data}


def _accounts_for(customer_id):
    return current_domain.repository_for(RewardAccount)._dao.query.filter(customer_id=customer_id).all().items


class TestCustomerRegisteredSubscriber:
    def test_customer_registered_enrolls_a_reward_account(self):
        CustomerRegisteredSubscriber()(
            _message(
                "Identity.CustomerRegistered.v1",
                {"customer_id": "cust-1", "first_name": "Maya"},
            )
        )

        accounts = _accounts_for("cust-1")
        assert len(accounts) == 1
        assert accounts[0].status == "Active"
        assert accounts[0].tier == "bronze"

    def test_redelivery_is_idempotent(self):
        msg = _message("Identity.CustomerRegistered.v1", {"customer_id": "cust-1"})
        CustomerRegisteredSubscriber()(msg)
        CustomerRegisteredSubscriber()(msg)  # at-least-once redelivery

        assert len(_accounts_for("cust-1")) == 1

    def test_other_event_types_are_ignored(self):
        CustomerRegisteredSubscriber()(_message("Identity.ProfileUpdated.v1", {"customer_id": "cust-1"}))
        assert _accounts_for("cust-1") == []

    def test_missing_customer_id_is_a_noop(self):
        CustomerRegisteredSubscriber()(_message("Identity.CustomerRegistered.v1", {"first_name": "Maya"}))
        # no crash, nothing enrolled
        assert _accounts_for("") == []
