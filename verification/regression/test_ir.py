"""Regressions in `protean ir` and `protean ir diff`."""

from __future__ import annotations

import os

import pytest

REVIEWS_IR = os.path.join(os.path.dirname(__file__), "..", "..", ".protean", "reviews", "ir.json")


def _ir_diff(*args: str):
    import protean.cli
    from typer.testing import CliRunner

    return CliRunner().invoke(protean.cli.app, ["ir", "diff", *args])


def _plain(result) -> str:
    """Return the CLI output without ANSI styling.

    Rich colours the output on CI even under CliRunner, and it styles each dash-separated
    part of an option name separately, so a plain substring check fails there.
    """
    import click

    return click.unstyle(result.output)


def _reviews_ir_without_a_projection(tmp_path) -> str:
    """Write the reviews baseline with one projection removed, and return its path.

    Diffing it against the baseline gives a real change in either direction: an added
    projection is safe, and a removed one is breaking.
    """
    import json

    with open(REVIEWS_IR) as fh:
        ir = json.load(fh)
    if not ir["projections"]:
        pytest.fail("precondition: the reviews baseline has a projection to remove")
    del ir["projections"][next(iter(ir["projections"]))]
    path = tmp_path / "reviews-ir.json"
    path.write_text(json.dumps(ir))
    return str(path)


@pytest.mark.protean_bug(
    issue=1912,
    state="open",
    bug=(
        '`protean ir diff` exits 2 for "non-breaking changes only", the same code Click uses for a usage error such as'
        " an unknown option. A gate that reads exit 2 as a safe change passes when its own command line is broken. "
        "`scripts/ir-gate.sh` accepts exit 2 only with a JSON report whose summary has changes and no breaking change."
        " The test compares the two codes, so it flips whichever one Protean moves."
    ),
)
@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="ir diff exits 2 for non-breaking changes, the code Click uses for a usage error",
)
def test_ir_diff_usage_error_does_not_share_the_non_breaking_exit_code(tmp_path):
    """proteanhq/protean#1912: `ir diff` gives two outcomes one exit code.

    `protean ir diff` documents exit 2 as "non-breaking changes only". Click exits 2
    for a usage error, such as an unknown option. A CI gate that reads exit 2 as a safe
    change therefore passes when its own command line is broken: the old `make ir-gate`
    recipe would report a non-breaking change for a misspelled `--dir=`, though no diff
    ran. `scripts/ir-gate.sh` works around it by accepting exit 2 only with a JSON
    report whose summary says there are changes and none is breaking.

    The test compares the two codes rather than pinning either one, so it flips
    whichever of them Protean moves.
    """
    import json

    safe = _ir_diff(
        "--left",
        _reviews_ir_without_a_projection(tmp_path),
        "--right",
        REVIEWS_IR,
        "--dir",
        str(tmp_path),
        "--format",
        "json",
    )
    usage = _ir_diff("--no-such-flag")

    summary = json.loads(safe.stdout)["summary"]
    if safe.exit_code == 0 or not summary["has_changes"] or summary["has_breaking_changes"]:
        pytest.fail(f"precondition: an added projection is a non-breaking change\n{safe.output}")
    if usage.exit_code == 0 or "No such option: --no-such-flag" not in _plain(usage):
        pytest.fail(f"precondition: ir diff rejected the unknown option\n{usage.output}")
    assert usage.exit_code != safe.exit_code


@pytest.mark.protean_bug(
    issue=1912,
    state="open",
    bug=(
        "`protean ir diff` exits 1 for a breaking change and also for an error before any diff runs, such as a missing"
        " baseline file (`typer.Abort()`). The CLI exit-code rule keeps exit 2 for an environment error. "
        "`scripts/ir-gate.sh` reruns the diff in text format on exit 1, so the reason is printed either way."
    ),
)
@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="ir diff exits 1 both for a breaking change and for a baseline it cannot load",
)
def test_ir_diff_load_error_does_not_share_the_breaking_exit_code(tmp_path):
    """proteanhq/protean#1912: `ir diff` exits 1 for two outcomes too.

    It exits 1 for a breaking change, and also for an error before any diff runs, such
    as a missing baseline file. Protean's CLI convention keeps exit 2 for an environment error. `ir diff` raises
    `typer.Abort()` for these errors, which exits 1. A gate cannot tell from the code
    alone whether it found a breaking change or never compared anything.
    `scripts/ir-gate.sh` reruns the diff in text format on exit 1 so the reason is
    printed either way.
    """
    breaking = _ir_diff(
        "--left", REVIEWS_IR, "--right", _reviews_ir_without_a_projection(tmp_path), "--dir", str(tmp_path)
    )
    missing = str(tmp_path / "missing.json")
    load_error = _ir_diff("--left", missing, "--right", REVIEWS_IR, "--dir", str(tmp_path))

    if breaking.exit_code == 0 or "Breaking Changes" not in _plain(breaking):
        pytest.fail(f"precondition: a removed projection is a breaking change\n{breaking.output}")
    if load_error.exit_code == 0 or "file not found" not in _plain(load_error):
        pytest.fail(f"precondition: ir diff reported the missing baseline\n{load_error.output}")
    assert load_error.exit_code != breaking.exit_code


@pytest.mark.protean_bug(
    issue=None,
    state="open",
    bug=(
        "`protean ir diff --format json` reports `summary.has_breaking_changes: false` for a field type change that it"
        " lists under `compatibility.breaking_changes` and exits 1 for. Changing a projection field from `Float` to "
        "`Decimal` shows it. A tool that reads only the summary takes the change as safe. `scripts/ir-gate.sh` is not "
        "affected, because it trusts the summary only on exit 2."
    ),
)
@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="ir diff --format json reports has_breaking_changes false for a breaking field type change",
)
def test_ir_diff_summary_counts_a_breaking_field_type_change(tmp_path):
    """Protean finding (not yet filed upstream): the JSON summary misses a breaking change.

    Changing a projection field's type is listed under `compatibility.breaking_changes`
    and makes `ir diff` exit 1, but `summary.has_breaking_changes` stays false. A tool
    that reads the summary takes the change as safe. `scripts/ir-gate.sh` is not fooled,
    because it accepts a summary only on exit 2.
    """
    import json

    with open(REVIEWS_IR) as fh:
        ir = json.load(fh)
    if not ir["projections"]:
        pytest.fail("precondition: the reviews baseline has a projection")
    fields = ir["projections"][next(iter(ir["projections"]))]["projection"]["fields"]
    name, field = next((n, f) for n, f in fields.items() if f.get("type") == "Integer")
    field["type"] = "Float"
    changed = tmp_path / "reviews-ir.json"
    changed.write_text(json.dumps(ir))

    result = _ir_diff("--left", REVIEWS_IR, "--right", str(changed), "--dir", str(tmp_path), "--format", "json")

    report = json.loads(result.stdout)
    breaking = report["compatibility"]["breaking_changes"]
    if result.exit_code != 1 or [c["field_name"] for c in breaking] != [name]:
        pytest.fail(f"precondition: the type change is reported as breaking\n{result.output}")
    assert report["summary"]["has_breaking_changes"] is True


CATALOGUE_IR = os.path.join(os.path.dirname(__file__), "..", "..", ".protean", "catalogue", "ir.json")
PRICE_FQN = "catalogue.product.product.Price"


def _price_fields(ir: dict) -> dict:
    return ir["clusters"]["catalogue.product.product.Product"]["value_objects"][PRICE_FQN]["fields"]


@pytest.mark.protean_bug(
    issue=1926,
    state="open",
    bug=(
        "`protean ir diff` does not classify a change to a `Dict` field's value type. Typing catalogue's "
        "`Price.tier_prices` as `Dict(value_type=ValueObject(TierPrice))` shows as `tier_prices.content_type: None → "
        "TierPrice` and exits 2 (non-breaking), with only the added `TierPrice` listed as a safe change. Stored rows "
        "whose tier values are bare numbers no longer load."
    ),
)
@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="ir diff does not classify a Dict value type change, so it passes as non-breaking",
)
def test_1926_ir_diff_classifies_a_dict_value_type_change_as_breaking(tmp_path):
    """proteanhq/protean#1926: a Dict value type change passes as safe.

    The left side is the catalogue baseline with `Price.tier_prices` untyped, as it was
    before it became a map of `TierPrice`. Values stored under the old shape can't be
    loaded under the new one, so the change is breaking.
    """
    import json

    with open(CATALOGUE_IR) as fh:
        ir = json.load(fh)
    field = _price_fields(ir)["tier_prices"]
    if field.get("content_type") != "TierPrice":
        pytest.fail("precondition: the catalogue baseline types Price.tier_prices as a map of TierPrice")
    field["content_type"] = None
    untyped = tmp_path / "catalogue-ir.json"
    untyped.write_text(json.dumps(ir))

    result = _ir_diff("--left", str(untyped), "--right", CATALOGUE_IR, "--dir", str(tmp_path), "--format", "json")

    if result.exit_code not in (1, 2):
        pytest.fail(f"precondition: ir diff reports the change\n{result.output}")
    breaking = json.loads(result.stdout)["compatibility"]["breaking_changes"]
    assert result.exit_code == 1
    assert "tier_prices" in [c["field_name"] for c in breaking]


@pytest.mark.protean_bug(
    issue=1927,
    state="open",
    bug=(
        "`protean schema generate` ignores a `Dict` field's value type. For catalogue's `Price.tier_prices`, a "
        "`Dict(value_type=ValueObject(TierPrice))`, the JSON Schema has a bare `object`, Avro a map of `string` and "
        "Protobuf `map<string, string>`. None of them refers to `TierPrice`."
    ),
)
@pytest.mark.parametrize("fmt", ["json", "avsc", "proto"])
@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="schema generate writes a Dict of value objects as an untyped map",
)
def test_1927_schema_generate_types_a_dict_of_value_objects(tmp_path, fmt):
    """proteanhq/protean#1927: typed Dict values are dropped from schemas."""
    import protean.cli
    from typer.testing import CliRunner

    result = CliRunner().invoke(
        protean.cli.app,
        ["schema", "generate", "--ir", CATALOGUE_IR, "--format", "all", "--output", str(tmp_path)],
    )
    if result.exit_code != 0:
        pytest.fail(f"precondition: schema generate succeeds\n{result.output}")
    text = (tmp_path / "schemas" / "Product" / "value_objects" / f"Price.v1.{fmt}").read_text(encoding="utf-8")
    if fmt == "proto":
        tier_prices = next((line for line in text.splitlines() if " tier_prices = " in line), None)
    else:
        import json

        schema = json.loads(text)
        if fmt == "json":
            tier_prices = schema["properties"].get("tier_prices")
        else:
            tier_prices = next((f["type"] for f in schema["fields"] if f["name"] == "tier_prices"), None)
    if tier_prices is None:
        pytest.fail(f"precondition: the Price schema has tier_prices\n{text}")

    assert "TierPrice" in str(tier_prices)


@pytest.mark.protean_bug(
    issue=1930,
    state="tripwire",
    bug=(
        "`IRBuilder._extract_subscription` calls `.value` on an event handler's raw `subscription_type` option "
        "(and on `subscription_profile` the same way; ShopStream checks only the type). The "
        'options table documents it as a `str`, and `ConfigResolver` accepts `"event_store"`, but `protean ir` then '
        "aborts for the whole domain with `AttributeError`. Loyalty's `PoisonEventStoreHandler` passes "
        "`SubscriptionType.EVENT_STORE` instead. Fixed in proteanhq/protean#2096, after ShopStream's pin."
    ),
)
@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="proteanhq/protean#1930: IRBuilder calls .value on a string subscription_type; fixed upstream, not in the pin",
)
def test_ir_builds_for_a_handler_with_a_string_subscription_type():
    """proteanhq/protean#1930: `protean ir` crashes on `subscription_type="event_store"`.

    The event handler options table documents `subscription_type` as a `str`, and
    `ConfigResolver` turns the string into `SubscriptionType.EVENT_STORE`, so the
    engine runs the handler on the event store. `IRBuilder._extract_subscription`
    reads the raw option and calls `.value` on it, which raises `AttributeError`
    for a string, so `make ir` aborts for the whole domain. Loyalty's
    `PoisonEventStoreHandler` passes the enum to avoid it.
    """
    from protean import Domain, handle
    from protean.fields import String
    from protean.ir.builder import IRBuilder
    from protean.server.subscription.config_resolver import ConfigResolver
    from protean.server.subscription.profiles import SubscriptionType

    domain = Domain(name="StringSubscriptionTypeProbe")

    @domain.aggregate
    class Ticket:
        title = String()

    @domain.event(part_of=Ticket)
    class TicketOpened:
        title = String()

    @domain.event_handler(part_of=Ticket, subscription_type="event_store")
    class TicketAudit:
        @handle(TicketOpened)
        def record(self, event):  # noqa: ARG002
            pass

    domain.init(traverse=False)
    if ConfigResolver(domain).resolve(TicketAudit).subscription_type != SubscriptionType.EVENT_STORE:
        pytest.fail("precondition: the resolver accepts the string form")

    try:
        ir = IRBuilder(domain).build()
    except AttributeError as exc:
        # Only the `.value` call on a `str` is the pinned bug; any other AttributeError after a
        # pin move must fail the run instead of passing as the expected failure.
        if "'str' object has no attribute 'value'" not in str(exc):
            raise
        raise AssertionError(f"IRBuilder failed on a string subscription_type: {exc}") from exc

    handlers = [h for cluster in ir["clusters"].values() for h in cluster["event_handlers"].values()]
    assert [h["subscription"]["type"] for h in handlers] == ["event_store"]
