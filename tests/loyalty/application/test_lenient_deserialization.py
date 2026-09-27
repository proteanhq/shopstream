"""Lenient and strict deserialization of stored PromoCampaign events.

``CampaignPaused`` opts into lenient loading (``lenient=True``): a stored payload carrying a
field the class no longer has loads anyway, and the dropped name is recorded under
``metadata.extensions["_dropped_fields"]``. Every other loyalty event keeps Protean's strict
default, so an unknown field still fails with ``DeserializationError``.
"""

import pytest
from protean import current_domain
from protean.exceptions import DeserializationError

from loyalty.campaign.campaign import PromoCampaign
from loyalty.campaign.events import CampaignActivated, CampaignPaused


def _write_raw_event(store, stream, event_name, data, position):
    """Write a stored event as an older writer would have, bypassing the current class."""
    type_string = f"Loyalty.{event_name}.v1"
    store._write(
        stream,
        type_string,
        data,
        {
            "headers": {
                "id": f"evt-{event_name}-{position}",
                "type": type_string,
                "time": "2025-01-01T00:00:00+00:00",
                "stream": stream,
            },
            "envelope": {"specversion": "1.0"},
            "domain": {
                "fqn": f"loyalty.campaign.events.{event_name}",
                "kind": "EVENT",
                "origin_stream": None,
                "stream_category": stream.rsplit("-", 1)[0],
                "version": 1,
                "sequence_id": str(position),
                "asynchronous": True,
            },
        },
        position - 1,
    )


def _stored_message(campaign_id, event_name, data):
    store = current_domain.event_store.store
    stream = f"loyalty::promo_campaign-{campaign_id}"
    _write_raw_event(store, stream, event_name, data, position=0)
    messages = store.read(stream)
    assert len(messages) == 1, "Expected the raw event to be stored"
    return messages[0]


class TestLenientCampaignPaused:
    def test_extra_field_is_dropped_and_recorded(self):
        message = _stored_message(
            "promo-lenient-001",
            "CampaignPaused",
            {
                "campaign_id": "promo-lenient-001",
                "reason": "budget",
                "paused_at": "2025-01-01T00:00:00+00:00",
                "paused_by": "ops-bot",
                "ticket": "OPS-42",
            },
        )

        event = message.to_domain_object()

        assert isinstance(event, CampaignPaused)
        assert event.campaign_id == "promo-lenient-001"
        assert event.reason == "budget"
        assert "paused_by" not in event.to_dict()
        assert "ticket" not in event.to_dict()
        assert event._metadata.extensions["_dropped_fields"] == ["paused_by", "ticket"]

    def test_missing_required_field_still_raises(self):
        message = _stored_message(
            "promo-lenient-003",
            "CampaignPaused",
            {"reason": "budget", "paused_at": "2025-01-01T00:00:00+00:00", "paused_by": "ops-bot"},
        )

        with pytest.raises(DeserializationError) as exc_info:
            message.to_domain_object()

        assert "campaign_id" in str(exc_info.value)

    def test_payload_without_extra_field_records_nothing(self):
        message = _stored_message(
            "promo-lenient-002",
            "CampaignPaused",
            {
                "campaign_id": "promo-lenient-002",
                "reason": "budget",
                "paused_at": "2025-01-01T00:00:00+00:00",
            },
        )

        event = message.to_domain_object()

        assert event.reason == "budget"
        assert "_dropped_fields" not in event._metadata.extensions

    def test_replay_tolerates_extra_field_on_paused_event(self):
        campaign = PromoCampaign.launch("LENIENT1", "Lenient Sale", "percentage", 10)
        campaign.activate()
        current_domain.repository_for(PromoCampaign).add(campaign)

        store = current_domain.event_store.store
        stream = f"loyalty::promo_campaign-{campaign.id}"
        stored = store.read(stream)
        assert len(stored) == 2, "Expected Launched and Activated in the stream"
        _write_raw_event(
            store,
            stream,
            "CampaignPaused",
            {
                "campaign_id": str(campaign.id),
                "reason": "budget",
                "paused_at": "2025-01-02T00:00:00+00:00",
                "paused_by": "ops-bot",
            },
            position=len(stored),
        )

        loaded = current_domain.repository_for(PromoCampaign).get(campaign.id)
        assert loaded.status == "paused"


class TestStrictByDefault:
    def test_domain_default_is_strict(self):
        assert current_domain.config.get("lenient_deserialization", False) is False

    def test_unknown_field_on_non_lenient_event_raises(self):
        message = _stored_message(
            "promo-strict-001",
            "CampaignActivated",
            {
                "campaign_id": "promo-strict-001",
                "activated_at": "2025-01-01T00:00:00+00:00",
                "activated_by": "ops-bot",
            },
        )

        with pytest.raises(DeserializationError) as exc_info:
            message.to_domain_object()

        assert "activated_by" in str(exc_info.value)

    def test_known_fields_on_non_lenient_event_load(self):
        message = _stored_message(
            "promo-strict-002",
            "CampaignActivated",
            {"campaign_id": "promo-strict-002", "activated_at": "2025-01-01T00:00:00+00:00"},
        )

        event = message.to_domain_object()

        assert isinstance(event, CampaignActivated)
        assert event.campaign_id == "promo-strict-002"
