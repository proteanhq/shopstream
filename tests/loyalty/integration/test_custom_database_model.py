"""Integration tests for the custom ``@database_model`` on ``RewardAccountView``.

The custom model (`RewardAccountViewPostgresModel`) is registered with ``database="postgresql"``,
so Protean uses it only for the Postgres provider and falls back to its auto-generated model under
the in-memory provider. These tests assert both halves of that behaviour and that the projection
still round-trips through the custom model.
"""

from protean import current_domain

from loyalty.projections.reward_account_view import RewardAccountView
from loyalty.projections.reward_account_view_model import RewardAccountViewPostgresModel
from loyalty.reward.enrollment import EnrollRewardAccount


def _database_type() -> str:
    return current_domain.repository_for(RewardAccountView)._provider.__class__.__database__


class TestCustomDatabaseModel:
    def test_postgres_provider_resolves_the_custom_model(self):
        """Under Postgres the hand-written model is selected, with its column overrides."""
        if _database_type() != "postgresql":
            import pytest

            pytest.skip("custom column overrides only apply to the Postgres provider")

        model = current_domain.repository_for(RewardAccountView)._database_model
        # Protean re-bases our class onto SqlalchemyModel, so identity is by name/MRO.
        assert model.__name__ == "RewardAccountViewPostgresModel"
        assert issubclass(model, RewardAccountViewPostgresModel)

        # The column overrides took effect: Text (not the default bounded String) + an index.
        assert type(model.customer_id.type).__name__ == "Text"
        assert model.customer_id.index is True
        assert type(model.member_code.type).__name__ == "Text"

    def test_memory_provider_falls_back_to_the_auto_model(self):
        """Under the in-memory provider the postgresql-keyed model is NOT used."""
        if _database_type() != "memory":
            import pytest

            pytest.skip("fallback behaviour is only observable under the memory provider")

        model = current_domain.repository_for(RewardAccountView)._database_model
        assert not issubclass(model, RewardAccountViewPostgresModel)

    def test_projection_round_trips_through_the_resolved_model(self):
        """Regardless of provider, the projection is written and read back correctly."""
        account_id = current_domain.process(EnrollRewardAccount(customer_id="cust-dbmodel"), asynchronous=False)

        view = current_domain.repository_for(RewardAccountView).get(account_id)
        assert view.customer_id == "cust-dbmodel"
        assert view.member_code  # populated by the projector
        assert view.status == "Active"
        assert view.points_balance == 0
