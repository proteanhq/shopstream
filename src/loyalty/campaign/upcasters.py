"""Upcasters for CampaignLaunched — a multi-step schema-evolution chain (v1 -> v2 -> v3).

The aggregate raises the current (v3) event; these upcasters transparently transform older
stored events to v3 during replay/handling. Protean builds the chain at domain.init() and
applies as many steps as needed (e.g. a v1 event runs through both upcasters).

This is the only multi-step upcaster chain in ShopStream (ordering has a single v1->v2 step).
"""

from protean.core.upcaster import BaseUpcaster

from loyalty.campaign.events import CampaignLaunched
from loyalty.domain import loyalty


@loyalty.upcaster(event_type=CampaignLaunched, from_version=1, to_version=2)
class UpcastCampaignLaunchedV1ToV2(BaseUpcaster):
    """v1 stored a single ``discount_pct``; v2 renames it to ``discount_value`` and adds an
    explicit ``discount_type`` (every v1 campaign was a percentage discount)."""

    def upcast(self, data: dict) -> dict:
        data["discount_value"] = data.pop("discount_pct", 0)
        data.setdefault("discount_type", "percentage")
        return data


@loyalty.upcaster(event_type=CampaignLaunched, from_version=2, to_version=3)
class UpcastCampaignLaunchedV2ToV3(BaseUpcaster):
    """v3 introduces optional scheduling fields (``starts_on`` / ``ends_on``)."""

    def upcast(self, data: dict) -> dict:
        data.setdefault("starts_on", None)
        data.setdefault("ends_on", None)
        return data
