"""The Reviewer's verdicts reach each deliverable, and bad review files are ignored."""

from __future__ import annotations

import json
import os
from pathlib import Path

from conftest import DAY, _session

from cti_console.config import Settings
from cti_console.deliverables import scan
from cti_console.pipeline import load_rules
from cti_console.reviews import parse
from cti_console.runs import group_runs, load_sessions
from cti_console.summary import build_summary

FLAG = {
    "id": "CTI26-01",
    "verdict": "flag",
    "checked_at": "2026-11-12T14:05:00Z",
    "summary": "One date differs from its source.",
    "findings": [
        {"claim": "Exploited since 3 Nov", "problem": "Source says 5 Nov", "source": "https://x"},
        {"claim": "no problem given"},
        "not an object",
    ],
}


def _write(settings: Settings, ident: str, body: object, mtime: float | None = None) -> Path:
    path = settings.out_dir / "bulletin-scan/state/reviews" / f"{ident}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body if isinstance(body, str) else json.dumps(body), encoding="utf-8")
    if mtime is not None:
        os.utime(path, (mtime, mtime))
    return path


def _items(settings: Settings) -> dict[str, object]:
    return {d.id: d for d in scan(settings.out_dir, load_rules(settings.scripts_dir))}


def test_flag_keeps_only_readable_findings(settings: Settings) -> None:
    _write(settings, "CTI26-01", FLAG)
    review = _items(settings)["CTI26-01"].review  # type: ignore[attr-defined]
    assert review is not None and review.verdict == "flag"
    assert [f.problem for f in review.findings] == ["Source says 5 Nov"]
    assert review.stale is False


def test_unreviewed_document_has_no_review(settings: Settings) -> None:
    assert _items(settings)["TH26-01"].review is None  # type: ignore[attr-defined]


def test_review_older_than_document_is_stale(settings: Settings) -> None:
    doc = settings.out_dir / "bulletin-scan/bulletins/2026/CTI26-01-Good_Bulletin.docx"
    _write(settings, "CTI26-01", {**FLAG, "verdict": "pass"}, mtime=doc.stat().st_mtime - 60)
    review = _items(settings)["CTI26-01"].review  # type: ignore[attr-defined]
    assert review is not None and review.stale is True


def test_bad_files_are_skipped(settings: Settings) -> None:
    _write(settings, "CTI26-01", "{not json")
    _write(settings, "TH26-01", {"verdict": "maybe"})
    items = _items(settings)
    assert items["CTI26-01"].review is None  # type: ignore[attr-defined]
    assert items["TH26-01"].review is None  # type: ignore[attr-defined]


def test_review_serialises_with_the_deliverable(settings: Settings) -> None:
    _write(settings, "CTI26-01", FLAG)
    data = _items(settings)["CTI26-01"].to_dict()  # type: ignore[attr-defined]
    assert data["review"]["findings"][0]["source"] == "https://x"


def test_parse_caps_long_text() -> None:
    review = parse({"verdict": "pass", "summary": "x" * 5000, "findings": []})
    assert review is not None and len(review.summary) == 1000


def _reviewer_session(settings: Settings, ok: bool = True) -> None:
    """A reviewer pass right after the run day's two builder passes."""
    log = settings.out_dir / "bulletin-scan/state/cost-log.jsonl"
    row = _session(f"{DAY}T20:10:00+00:00", "review", 1.5, 3, exit_code=0 if ok else 1)
    with log.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row) + "\n")


def test_reviewer_session_stays_in_its_run(settings: Settings) -> None:
    _reviewer_session(settings)
    runs = group_runs(load_sessions(settings.out_dir))
    labels = [[s.label for s in r.sessions] for r in runs if r.component == "bulletin-scan"]
    assert ["scan", "build-1", "build-2", "review"] in labels


def test_review_stage_counts_flags_from_that_day(settings: Settings) -> None:
    _reviewer_session(settings)
    _write(settings, "CTI26-01", {**FLAG, "checked_at": f"{DAY}T20:12:00Z"})
    _write(settings, "TH26-01", {"verdict": "pass", "checked_at": f"{DAY}T20:12:00Z"})
    stages = {st["key"]: st for st in build_summary(settings)["stages"]}  # type: ignore[union-attr]
    assert stages["review"]["value"] == "2 docs, 1 flagged"
    assert stages["review"]["status"] == "warn"


def test_review_stage_without_a_reviewer_pass(settings: Settings) -> None:
    stages = {st["key"]: st for st in build_summary(settings)["stages"]}  # type: ignore[union-attr]
    assert stages["review"]["status"] == "unknown"
