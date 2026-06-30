"""Active points-multiplier lookup — a cross-aggregate read.

The points-earning flow (RewardAccount aggregate) needs to know whether a PromoCampaign
of type ``points_multiplier`` is currently active. Rather than reach across aggregate
boundaries into PromoCampaign's event stream, the earn handler consults the CampaignCatalog
read model through this helper. When several multiplier campaigns are active, the most
generous one wins; when none are, the multiplier is 1 (points earned unchanged).
"""

from datetime import date

from protean.utils.globals import current_domain

from loyalty.projections.campaign_catalog import CampaignCatalog


def active_points_multiplier(on_date=None):
    """Return the highest active ``points_multiplier`` factor, or 1 if none apply.

    A campaign counts as active when its catalog status is ``active`` and ``on_date``
    (default: today) falls within its optional ``starts_on``/``ends_on`` window.
    """
    on_date = on_date or date.today()
    candidates = (
        current_domain.view_for(CampaignCatalog)
        .query.filter(status="active", discount_type="points_multiplier")
        .all()
        .items
    )

    best = 1
    for campaign in candidates:
        if campaign.starts_on and on_date < campaign.starts_on:
            continue
        if campaign.ends_on and on_date > campaign.ends_on:
            continue
        best = max(best, campaign.discount_value or 1)
    return best
