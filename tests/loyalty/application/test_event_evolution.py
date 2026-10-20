"""Evolution of RewardAccount events: a renamed field and a superseded event.

``PointsEarned`` and ``PointsRedeemed`` renamed their ``amount`` field to ``points`` with
``renamed_from="amount"``, so a stored payload written under the old name still loads.
``MembershipCardIssued`` is deprecated and superseded by ``MembershipCardIssuedV2``, which
carries ``issued_on`` as a date: ``issue_card()`` raises only the new event, and raising the
old one emits a ``ProteanDeprecationWarning`` that names the replacement.
"""

import warnings
from datetime import date

import pytest
from protean import current_domain
from protean.exceptions import ProteanDeprecationWarning

from loyalty.reward.events import (
    MembershipCardIssued,
    MembershipCardIssuedV2,
    PointsEarned,
    PointsRedeemed,
)
from loyalty.reward.reward_account import RewardAccount


def _stored_event(account_id, event_name, data):
    """Write a raw RewardAccount event payload to the event store, then read it back."""
    store = current_domain.event_store.store
    stream = f"loyalty::reward_account-{account_id}"
    type_string = f"Loyalty.{event_name}.v1"
    store._write(
        stream,
        type_string,
        data,
        {
            "headers": {
                "id": f"evt-{event_name}-{account_id}",
                "type": type_string,
                "time": "2025-01-01T00:00:00+00:00",
                "stream": stream,
            },
            "envelope": {"specversion": "1.0"},
            "domain": {
                "fqn": f"loyalty.reward.events.{event_name}",
                "kind": "EVENT",
                "origin_stream": None,
                "stream_category": "loyalty::reward_account",
                "version": 1,
                "sequence_id": "0",
                "asynchronous": True,
            },
        },
        -1,
    )
    messages = store.read(stream)
    assert len(messages) == 1, "Expected the raw event to be stored"
    return messages[0].to_domain_object()


def _points_payload(account_id, **count):
    return {
        "account_id": account_id,
        "customer_id": "cust-evo",
        "balance_after": 100,
        "reason": "order",
        "occurred_at": "2025-01-01T00:00:00+00:00",
        **count,
    }


class TestPointsFieldRename:
    def test_old_amount_payload_loads_into_points(self):
        event = _stored_event("acc-evo-1", "PointsEarned", _points_payload("acc-evo-1", amount=42))

        assert isinstance(event, PointsEarned)
        assert event.points == 42

    def test_current_points_payload_loads(self):
        event = _stored_event("acc-evo-2", "PointsEarned", _points_payload("acc-evo-2", points=17))

        assert event.points == 17

    def test_points_wins_when_both_names_are_present(self):
        event = _stored_event("acc-evo-3", "PointsEarned", _points_payload("acc-evo-3", amount=1, points=9))

        assert event.points == 9

    def test_old_amount_payload_loads_into_points_on_redeemed(self):
        event = _stored_event("acc-evo-4", "PointsRedeemed", _points_payload("acc-evo-4", amount=30))

        assert isinstance(event, PointsRedeemed)
        assert event.points == 30

    def test_aggregate_raises_points(self):
        account = RewardAccount.enroll(customer_id="cust-evo")
        account.earn_points(50)
        account.redeem_points(20)
        account.claw_back_points(10)

        counts = [(type(e).__name__, e.points) for e in account._events if isinstance(e, PointsEarned | PointsRedeemed)]
        assert counts == [("PointsEarned", 50), ("PointsRedeemed", 20), ("PointsRedeemed", 10)]


class TestMembershipCardSupersession:
    def test_raising_the_old_event_warns_once_naming_v2(self):
        account = RewardAccount.enroll(customer_id="cust-evo")
        # The warning fires once per event type per domain, so clear what an earlier test recorded.
        current_domain._deprecated_events_warned.discard(MembershipCardIssued)
        event = MembershipCardIssued(account_id=account.id, card_number="LOY-OLD", issued_on="2025-01-01")

        with pytest.warns(ProteanDeprecationWarning, match="MembershipCardIssuedV2") as records:
            account.raise_(event)
            account.raise_(event)

        assert len([r for r in records if issubclass(r.category, ProteanDeprecationWarning)]) == 1

    def test_issue_card_raises_only_v2_with_a_date(self):
        account = RewardAccount.enroll(customer_id="cust-evo")
        current_domain._deprecated_events_warned.discard(MembershipCardIssued)

        with warnings.catch_warnings(record=True) as records:
            warnings.simplefilter("always")
            account.issue_card(card_number="LOY-NEW")

        assert [r for r in records if issubclass(r.category, ProteanDeprecationWarning)] == []
        cards = [e for e in account._events if isinstance(e, MembershipCardIssued | MembershipCardIssuedV2)]
        assert len(cards) == 1
        assert isinstance(cards[0], MembershipCardIssuedV2)
        assert cards[0].card_number == "LOY-NEW"
        assert isinstance(cards[0].issued_on, date)
        assert cards[0].issued_on == account.card.issued_on
