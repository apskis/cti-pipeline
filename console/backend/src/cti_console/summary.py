"""The overview the front page shows: headline numbers, last scan run and its stages."""

from __future__ import annotations

from datetime import UTC, datetime

from .config import Settings
from .deliverables import counts_by_kind, scan
from .pipeline import load_rules
from .register import count_cves, latest_register
from .runs import Run, group_runs, load_sessions
from .stages import pipeline_stages


def collect_runs(settings: Settings) -> list[Run]:
    return group_runs(load_sessions(settings.out_dir))


def last_scan(runs: list[Run]) -> Run | None:
    scans = [r for r in runs if r.component == "bulletin-scan" and r.kind == "scan"]
    return scans[-1] if scans else None


def build_summary(settings: Settings) -> dict[str, object]:
    rules = load_rules(settings.scripts_dir)
    items = scan(settings.out_dir, rules)
    runs = collect_runs(settings)
    run = last_scan(runs)
    register = latest_register(settings.out_dir)
    return {
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "counts": counts_by_kind(items),
        "cves_tracked": count_cves(register) if register else None,
        "total_cost_usd": round(sum(s.cost_usd for r in runs for s in r.sessions), 2),
        "run_days": len({r.started.date() for r in runs}),
        "last_scan": run.to_dict() if run else None,
        "stages": [
            s.to_dict()
            for s in pipeline_stages(settings.out_dir, settings.logs_dir, runs, run, items)
        ]
        if run
        else [],
    }
