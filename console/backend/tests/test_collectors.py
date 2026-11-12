from __future__ import annotations

import os
from dataclasses import replace
from datetime import date
from pathlib import Path

import pytest

from cti_console.config import Settings
from cti_console.deliverables import _CHECKS, load_checks, save_checks, scan
from cti_console.pipeline import PipelineRules, load_rules
from cti_console.runs import group_runs, load_sessions
from cti_console.stages import assigned_ids, search_count
from cti_console.summary import build_summary


def test_runs_split_on_scan_and_on_long_gaps(settings: Settings) -> None:
    runs = group_runs(load_sessions(settings.out_dir))
    shape = [(r.component, r.kind, len(r.sessions)) for r in runs]
    assert shape == [
        ("bulletin-scan", "scan", 1),
        ("bulletin-scan", "scan", 3),
        ("reporting", "scan", 1),
        ("bulletin-scan", "build only", 1),
    ]


def test_bad_cost_log_line_is_skipped(settings: Settings) -> None:
    log = settings.out_dir / "bulletin-scan/state/cost-log.jsonl"
    log.write_text(log.read_text(encoding="utf-8") + "not json\n", encoding="utf-8")
    assert len(load_sessions(settings.out_dir)) == 6


def test_deliverables_one_per_id_with_status(settings: Settings) -> None:
    items = {d.id: d for d in scan(settings.out_dir, load_rules(settings.scripts_dir))}
    assert set(items) == {"CTI26-01", "CTI26-02", "TH26-01", "WK-2026-46", "CVE-VM-2026-10-10"}
    assert items["CVE-VM-2026-10-10"].status == "unchecked"
    assert items["CTI26-01"].status == "ok"
    assert items["CTI26-02"].status == "broken"
    assert "single character" in (items["CTI26-02"].problem or "")
    assert items["WK-2026-46"].status == "unchecked"
    assert items["CTI26-01"].title == "Good Bulletin"
    assert items["CTI26-01"].first_seen == "2026-10-10"


def test_paths_are_relative_and_skip_state(settings: Settings) -> None:
    items = scan(settings.out_dir, load_rules(settings.scripts_dir))
    assert all(not d.path.startswith(("/", "\\")) and ":" not in d.path for d in items)
    assert not any("state/" in d.path for d in items)


def test_search_count_phrasings() -> None:
    assert search_count("Web searches run: 7") == 7
    assert search_count("I ran 9 searches this run") == 9
    assert search_count("WebSearch was available and unused by choice") == 0
    assert search_count("nothing about searching") is None


def test_assigned_ids_only_for_that_day(settings: Settings) -> None:
    text = (settings.out_dir / "bulletin-scan/state/dedup-log.md").read_text(encoding="utf-8")
    assert assigned_ids(text, date(2026, 11, 10)) == {"CTI26-02", "TH26-01"}


def test_summary_tiles_and_stages(settings: Settings) -> None:
    s = build_summary(settings)
    assert s["counts"] == {"bulletin": 2, "hunt": 1, "weekly": 1, "cve_brief": 1}
    assert s["cves_tracked"] == 2
    assert s["total_cost_usd"] == 20.7
    stages = {st["key"]: st for st in s["stages"]}  # type: ignore[union-attr]
    assert stages["feeds"]["status"] == "warn"
    assert stages["feeds"]["note"] == "Failed: HHS HC3 Alerts (HTTP 404)"
    assert stages["feeds"]["value"] == "189 items, 9 of 10 up"
    assert stages["scan"]["value"] == "19 min, 7 searches"
    assert stages["triage"]["value"] == "2 new IDs"
    assert stages["build"]["value"] == "3 passes"
    assert stages["check"]["status"] == "fail"
    assert stages["deliver"]["value"] == "2 new"


def test_missing_sources_read_as_unknown(settings: Settings) -> None:
    (settings.out_dir / "bulletin-scan/reports/scan-2026-11-10.md").unlink()
    for log in settings.logs_dir.iterdir():
        log.unlink()
    stages = {st["key"]: st for st in build_summary(settings)["stages"]}  # type: ignore[union-attr]
    assert stages["feeds"]["status"] == "unknown"
    assert stages["scan"]["status"] == "unknown"


def test_promote_headings_only_whole_bold_paragraphs() -> None:
    from cti_console.reader import promote_headings

    html = (
        "<p><strong>Why This Matters</strong></p>"
        "<p><strong>Lead: </strong>body text</p>"
        "<p><strong>x</strong></p>"
        "<table><tr><td><p><strong>Threat Actor</strong></p></td></tr></table>"
        "<p><strong>Sources</strong></p>"
    )
    assert promote_headings(html) == (
        "<h3>Why This Matters</h3><p><strong>Lead: </strong>body text</p><p><strong>x</strong></p>"
        "<table><tr><td><p><strong>Threat Actor</strong></p></td></tr></table>"
        "<h3>Sources</h3>"
    )


@pytest.fixture(autouse=True)
def _fresh_checks() -> None:
    """Check results are module level; each test starts as a newly started console."""
    _CHECKS.clear()


def _counting(rules: PipelineRules) -> tuple[PipelineRules, list[str]]:
    """The same rules, with a shell check that records each document it parses."""
    parsed: list[str] = []

    def check(path: Path, ident: str, kind: str) -> str | None:
        parsed.append(ident)
        return rules.shell_reason(path, ident, kind)

    return replace(rules, shell_reason=check), parsed


def test_saved_checks_spare_a_restart_the_parsing(settings: Settings) -> None:
    rules = load_rules(settings.scripts_dir)
    file = settings.cache_dir / "checks.json"
    before = {d.id: d.status for d in scan(settings.out_dir, rules)}
    save_checks(file, rules)
    _CHECKS.clear()  # as after a restart

    assert load_checks(file, rules) == 3
    counted, parsed = _counting(rules)
    after = {d.id: d.status for d in scan(settings.out_dir, counted)}
    assert parsed == []
    assert after == before


def test_saved_checks_are_dropped_when_the_rules_change(settings: Settings) -> None:
    rules = load_rules(settings.scripts_dir)
    file = settings.cache_dir / "checks.json"
    scan(settings.out_dir, rules)
    save_checks(file, rules)
    _CHECKS.clear()

    assert load_checks(file, replace(rules, version="tightened")) == 0


def test_a_changed_report_is_checked_again(settings: Settings) -> None:
    rules = load_rules(settings.scripts_dir)
    file = settings.cache_dir / "checks.json"
    scan(settings.out_dir, rules)
    save_checks(file, rules)
    _CHECKS.clear()
    load_checks(file, rules)
    changed = settings.out_dir / "bulletin-scan/bulletins/2026/CTI26-01-Good_Bulletin.docx"
    os.utime(changed, (1_800_000_000, 1_800_000_000))

    counted, parsed = _counting(rules)
    scan(settings.out_dir, counted)
    assert parsed == ["CTI26-01"]


def test_unreadable_saved_checks_are_ignored(settings: Settings) -> None:
    file = settings.cache_dir / "checks.json"
    file.parent.mkdir(parents=True)
    file.write_text("{not json", encoding="utf-8")
    assert load_checks(file, load_rules(settings.scripts_dir)) == 0
