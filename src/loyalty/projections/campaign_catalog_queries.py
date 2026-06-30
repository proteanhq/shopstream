"""Queries for the CampaignCatalog projection."""

from protean import read
from protean.fields import Identifier, String
from protean.utils.globals import current_domain

from loyalty.domain import loyalty
from loyalty.projections.campaign_catalog import CampaignCatalog


@loyalty.query(part_of=CampaignCatalog)
class GetCampaign:
    campaign_id = Identifier(required=True)


@loyalty.query(part_of=CampaignCatalog)
class ListCampaigns:
    status = String()


@loyalty.query_handler(part_of=CampaignCatalog)
class CampaignCatalogQueryHandler:
    @read(GetCampaign)
    def get_campaign(self, query):
        return current_domain.view_for(CampaignCatalog).get(query.campaign_id)

    @read(ListCampaigns)
    def list_campaigns(self, query):
        qs = current_domain.view_for(CampaignCatalog).query
        if query.status:
            qs = qs.filter(status=query.status)
        return qs.order_by("-updated_at").all().items
