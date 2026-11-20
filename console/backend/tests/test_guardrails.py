"""The self check loop's outcome reaches each deliverable, the summary and the stage."""

from __future__ import annotations

import json
import os
from pathlib import Path

from conftest import DAY, _session

from cti_console.config import Settings
from cti_console.deliverables import scan
from cti_console.guardrails import parse
from cti_console.pipeline import load_rules
from cti_console.runs import group_runs, load_sessions
from cti_console.summary import build_summary

ROUND_FAIL = {"round": 1, "failed": True}
ROUND_PASS = {"round": 2, "failed": False}
FIXED = {
    "id": "CTI26-01",
    "status": "self-corrected",
    "gates": {"sources": "pass", "wording": "pass", "reasoning": "maybe"},
    "rounds": [ROUND_FAIL, ROUND_PASS],
    "open_issues": [],
    "lint": [{"level": "WARN", "rule": "absolute-certainty"}, {"level": "ERROR"}],
    "updated_at": f"{DAY}T20:30:00Z",
}


def _write(settings: Settings, ident: str, body: object, mtime: float | None = None) -> Path:
    path = settings.out_dir / "bulletin-scan/state/guardrails" / f"{ident}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body if isinstance(body, str) else json.dumps(body), encoding="utf-8")
    if mtime is not None:
        os.utime(path, (mtime, mtime))
    return path


def _items(settings: Settings) -> dict[str, object]:
    return {d.id: d for d in scan(settings.out_dir, load_rules(settings.scripts_dir))}


def test_record_reaches_the_deliverable(settings: Settings) -> None:
    _write(settings, "CTI26-01", FIXED)
    g = _items(settings)["CTI26-01"].guardrail  # type: ignore[attr-defined]
    assert g is not None and g.status == "self-corrected"
    assert (g.rounds, g.corrections, g.lint_warnings) == (2, 1, 1)
    # An unknown gate value never shows as a pass, and a missing gate is unchecked.
    assert g.gates["reasoning"] == "unchecked"
    assert g.gates["cve_facts"] == "unchecked"
    assert g.gates["sources"] == "pass"


def test_bad_records_are_skipped(settings: Settings) -> None:
    _write(settings, "CTI26-01", "{not json")
    _write(settings, "TH26-01", {**FIXED, "status": "approved"})
    items = _items(settings)
    assert items["CTI26-01"].guardrail is None  # type: ignore[attr-defined]
    assert items["TH26-01"].guardrail is None  # type: ignore[attr-defined]


def test_record_older_than_document_is_stale(settings: Settings) -> None:
    doc = settings.out_dir / "bulletin-scan/bulletins/2026/CTI26-01-Good_Bulletin.docx"
    _write(settings, "CTI26-01", FIXED, mtime=doc.stat().st_mtime - 60)
    g = _items(settings)["CTI26-01"].guardrail  # type: ignore[attr-defined]
    assert g is not None and g.stale is True


def test_parse_caps_issues() -> None:
    g = parse({**FIXED, "status": "needs-human", "open_issues": ["x" * 900] * 30})
    assert g is not None and len(g.open_issues) == 10 and len(g.open_issues[0]) == 500


def test_summary_counts_each_state(settings: Settings) -> None:
    _write(settings, "CTI26-01", FIXED)
    _write(settings, "TH26-01", {**FIXED, "status": "needs-human", "open_issues": ["No source"]})
    counts = build_summary(settings)["guardrails"]
    assert counts == {"verified": 0, "self-corrected": 1, "fixing": 0, "needs-human": 1}


def _loop_sessions(settings: Settings) -> None:
    log = settings.out_dir / "bulletin-scan/state/cost-log.jsonl"
    with log.open("a", encoding="utf-8") as f:
        for minute, label in ((10, "review-1"), (14, "fix-1"), (18, "review-2")):
            f.write(json.dumps(_session(f"{DAY}T20:{minute}:00+00:00", label, 1.0, 3)) + "\n")


def test_loop_sessions_stay_in_their_run(settings: Settings) -> None:
    _loop_sessions(settings)
    runs = group_runs(load_sessions(settings.out_dir))
    labels = [[s.label for s in r.sessions] for r in runs if r.component == "bulletin-scan"]
    assert ["scan", "build-1", "build-2", "review-1", "fix-1", "review-2"] in labels


def test_stage_reports_what_needs_a_human(settings: Settings) -> None:
    _loop_sessions(settings)
    review_dir = settings.out_dir / "bulletin-scan/state/reviews"
    review_dir.mkdir(parents=True, exist_ok=True)
    for ident in ("CTI26-01", "TH26-01"):
        body = {"verdict": "pass", "checked_at": f"{DAY}T20:18:00Z", "findings": []}
        (review_dir / f"{ident}.json").write_text(json.dumps(body), encoding="utf-8")
    _write(settings, "CTI26-01", FIXED)
    _write(settings, "TH26-01", {**FIXED, "status": "needs-human"})
    stages = {st["key"]: st for st in build_summary(settings)["stages"]}  # type: ignore[union-attr]
    assert stages["review"]["label"] == "Self check"
    assert stages["review"]["value"] == "2 docs, 1 need you"
    assert stages["review"]["note"] == "Needs you: TH26-01"
