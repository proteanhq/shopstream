"""Contract for the event model render that `make docs-event-model` and `make docs-check` run.

`protean docs generate --type=event-model` draws one slice per aggregate, and merges
human notes from an annotations TOML file keyed by element FQN. These tests drive the
CLI the way the Makefile does (subprocess, memory mode, `--domain`), with a temp
annotations file and a temp output path, and check where each note lands.

They also pin `protean ir diff --format=event-model`, which `make ir-diff-model` runs:
it must name a dropped event and exit with the same code as `--format=text`, so the
slice view can't hide a breaking change that the text view reports.
"""

import copy
import json
import os
import re
import shutil
import subprocess
import tomllib
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
PROTEAN = shutil.which("protean")
CATALOGUE_IR = REPO / ".protean" / "catalogue" / "ir.json"
LOYALTY_IR = REPO / ".protean" / "loyalty" / "ir.json"
REVIEWS_IR = REPO / ".protean" / "reviews" / "ir.json"

pytestmark = pytest.mark.skipif(PROTEAN is None, reason="protean CLI not on PATH")


def _run(*args: str) -> subprocess.CompletedProcess:
    # Run from the repo root so .protean/config.toml (strictness) applies, as in `make`.
    env = {**os.environ, "PYTHONPATH": str(REPO / "src"), "PROTEAN_ENV": "memory"}
    return subprocess.run([PROTEAN, "--log-level", "ERROR", *args], cwd=REPO, env=env, capture_output=True, text=True)


def _render(domain: str, annotations: Path, output: Path) -> subprocess.CompletedProcess:
    return _run(
        "docs",
        "generate",
        f"--domain={domain}.domain",
        "--type=event-model",
        f"--annotations={annotations}",
        f"--output={output}",
    )


def _write_notes(path: Path, notes: dict[str, str]) -> Path:
    path.write_text("".join(f'[annotations."{fqn}"]\nnote = "{text}"\n\n' for fqn, text in notes.items()))
    return path


def _rendered(result: subprocess.CompletedProcess, output: Path) -> str:
    assert result.returncode == 0, result.stdout + result.stderr
    assert output.exists(), "render reported success but wrote no file"
    return output.read_text()


def _slices(markdown: str) -> dict[str, str]:
    """Split a render into its slices, keyed by aggregate name."""
    parts = re.split(r"^## Event Model: (\w+)$", markdown, flags=re.M)
    return dict(zip(parts[1::2], parts[2::2], strict=True))


def _fqn(ir_path: Path, section: str, short_name: str) -> str:
    """Find an element's FQN in a committed IR, so a rename fails here instead of passing vacuously."""
    ir = json.loads(ir_path.read_text())
    if section == "clusters":
        names = ir["clusters"]
    else:
        names = {fqn for group in ir["projections"].values() for fqn in group.get("projectors", {})}
    matches = [fqn for fqn in names if fqn.rsplit(".", 1)[-1] == short_name]
    assert len(matches) == 1, f"{short_name} in {ir_path}: {matches}"
    return matches[0]


def test_an_aggregate_note_lands_in_its_own_slice_after_the_given_when_then(tmp_path):
    category = _fqn(CATALOGUE_IR, "clusters", "Category")
    notes = _write_notes(tmp_path / "notes.toml", {category: "NOTE-ON-CATEGORY"})
    output = tmp_path / "model.md"

    markdown = _rendered(_render("catalogue", notes, output), output)

    slices = _slices(markdown)
    assert list(slices) == ["Category", "Product"]
    category_slice = slices["Category"]
    then_line = category_slice.index("> **Then**")
    note = category_slice.index("> **Note:** NOTE-ON-CATEGORY")
    diagram = category_slice.index("```mermaid")
    assert then_line < note < diagram
    assert "NOTE-ON-CATEGORY" not in slices["Product"]
    assert "Unmatched annotations" not in markdown


def test_a_note_on_a_consumer_drawn_in_two_slices_shows_in_both(tmp_path):
    projector = _fqn(CATALOGUE_IR, "projectors", "CategoryProductsProjector")
    notes = _write_notes(tmp_path / "notes.toml", {projector: "NOTE-ON-PROJECTOR"})
    output = tmp_path / "model.md"

    markdown = _rendered(_render("catalogue", notes, output), output)

    slices = _slices(markdown)
    assert len(slices) == 2
    for name, body in slices.items():
        assert "(CategoryProductsProjector → CategoryProducts)" in body, f"projector not drawn in {name}"
        assert body.count("> **Note:** NOTE-ON-PROJECTOR") == 1, name
    assert "Unmatched annotations" not in markdown


def test_a_note_on_a_fact_event_is_reported_unmatched(tmp_path):
    ir = json.loads(LOYALTY_IR.read_text())
    fact_events = [
        fqn
        for cluster in ir["clusters"].values()
        for fqn, evt in cluster.get("events", {}).items()
        if evt.get("is_fact_event")
    ]
    assert len(fact_events) == 1, fact_events
    fact_event = fact_events[0]
    notes = _write_notes(tmp_path / "notes.toml", {fact_event: "NOTE-ON-FACT-EVENT"})
    output = tmp_path / "model.md"

    markdown = _rendered(_render("loyalty", notes, output), output)

    assert "NOTE-ON-FACT-EVENT" not in markdown
    head, unmatched = markdown.split("## Unmatched annotations", 1)
    assert fact_event not in head
    assert f"`{fact_event}`" in unmatched


def test_an_unquoted_dotted_key_aborts_the_render(tmp_path):
    # TOML reads [annotations.loyalty.reward...] as nested tables, so the entry Protean
    # sees is keyed "loyalty" and has no note. The render aborts and names that key,
    # rather than listing the full name under "Unmatched annotations".
    notes = tmp_path / "notes.toml"
    notes.write_text('[annotations.loyalty.reward.reward_account.RewardAccount]\nnote = "NOTE"\n')
    output = tmp_path / "model.md"

    result = _render("loyalty", notes, output)

    assert result.returncode != 0
    assert not output.exists()
    assert "Annotation for 'loyalty'" in " ".join((result.stdout + result.stderr).split())


@pytest.mark.parametrize(
    "content",
    [
        pytest.param('[annotations."loyalty.reward.reward_account.RewardAccount"\nnote = "x"\n', id="invalid-toml"),
        pytest.param('[annotations."loyalty.reward.reward_account.RewardAccount"]\nnote = 3\n', id="note-not-a-string"),
    ],
)
def test_a_malformed_annotations_file_aborts_before_writing(tmp_path, content):
    notes = tmp_path / "notes.toml"
    notes.write_text(content)
    output = tmp_path / "model.md"

    result = _render("loyalty", notes, output)

    assert result.returncode != 0
    assert not output.exists()


def test_the_committed_loyalty_notes_all_render_and_all_match():
    notes = tomllib.loads((REPO / ".protean" / "loyalty" / "annotations.toml").read_text())["annotations"]
    markdown = (REPO / "docs" / "loyalty" / "event-model.md").read_text()

    assert len(notes) >= 3
    assert "Unmatched annotations" not in markdown
    quoted_text = " ".join(line.removeprefix(">").strip() for line in markdown.splitlines() if line.startswith(">"))
    for fqn, entry in notes.items():
        assert " ".join(entry["note"].split()) in quoted_text, fqn


def _drop_one_event(ir: dict) -> tuple[dict, str]:
    """Return a copy of *ir* with one cluster event removed, and that event's short name."""
    dropped = copy.deepcopy(ir)
    for cluster in dropped["clusters"].values():
        events = cluster.get("events", {})
        for fqn in sorted(events):
            if not events[fqn].get("is_fact_event"):
                del events[fqn]
                return dropped, fqn.rsplit(".", 1)[-1]
    pytest.fail("no non-fact event in the reviews baseline to drop")


@pytest.mark.parametrize("direction", ["removed", "added"])
def test_ir_diff_as_event_model_names_the_event_and_exits_like_text(tmp_path, direction):
    baseline = json.loads(REVIEWS_IR.read_text())
    changed, event = _drop_one_event(baseline)
    copy_path = tmp_path / "changed.json"
    copy_path.write_text(json.dumps(changed))
    left, right = (REVIEWS_IR, copy_path) if direction == "removed" else (copy_path, REVIEWS_IR)

    model = _run("ir", "diff", "--left", str(left), "--right", str(right), "--format=event-model")
    text = _run("ir", "diff", "--left", str(left), "--right", str(right), "--format=text")

    assert f"event {event} {direction}" in model.stdout, model.stdout + model.stderr
    assert model.returncode == text.returncode
    assert model.returncode != 0


def test_ir_diff_as_event_model_reports_no_change_on_identical_files():
    result = _run("ir", "diff", "--left", str(REVIEWS_IR), "--right", str(REVIEWS_IR), "--format=event-model")

    assert result.returncode == 0
    assert "No model changes." in result.stdout
