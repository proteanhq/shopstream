"""Integration tests for loyalty's second persistence provider.

`CampaignCatalog` is bound to a **separate** database provider (`provider="reporting"`) from the
rest of the domain. Under Postgres that provider is SQLite (a genuinely different database engine
running alongside Postgres in the same domain); under the memory env both providers are in-memory
but remain distinct named providers. These tests assert the routing and that the projection still
round-trips through the reporting store.
"""

from protean import current_domain

from loyalty.campaign.management import LaunchCampaign
from loyalty.projections.campaign_catalog import CampaignCatalog
from loyalty.projections.reward_account_view import RewardAccountView


class TestSecondProvider:
    def test_campaign_catalog_is_bound_to_the_reporting_provider(self):
        catalog_provider = current_domain.repository_for(CampaignCatalog)._provider
        default_provider = current_domain.repository_for(RewardAccountView)._provider

        # CampaignCatalog is served by the dedicated 'reporting' provider, not 'default'.
        assert catalog_provider.name == "reporting"
        assert default_provider.name == "default"
        assert catalog_provider is not default_provider

    def test_reporting_and_default_are_different_engines_under_postgres(self):
        catalog_provider = current_domain.repository_for(CampaignCatalog)._provider
        if catalog_provider.__class__.__database__ != "sqlite":
            import pytest

            pytest.skip("distinct database engines are only observable under the Postgres env")

        # Two real, different database engines active in one domain.
        default_provider = current_domain.repository_for(RewardAccountView)._provider
        assert catalog_provider.__class__.__database__ == "sqlite"
        assert default_provider.__class__.__database__ == "postgresql"

    def test_campaign_round_trips_through_the_reporting_store(self):
        campaign_id = current_domain.process(
            LaunchCampaign(
                campaign_code="REPORT5",
                name="Reporting Store Sale",
                discount_type="percentage",
                discount_value=5,
            ),
            asynchronous=False,
        )

        # The projector wrote into the reporting store; read it straight back from there.
        entry = current_domain.repository_for(CampaignCatalog).get(campaign_id)
        assert entry.campaign_code == "REPORT5"
        assert entry.status == "draft"
