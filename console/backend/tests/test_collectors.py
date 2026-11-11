from __future__ import annotations

from datetime import date

from cti_console.config import Settings
from cti_console.deliverables import scan
from cti_console.pipeline import load_rules
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
