"""One run in full: its sessions, its stages, what it wrote and the report it left."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

from markdown_it import MarkdownIt

from .config import Settings
from .deliverables import Deliverable, scan
from .pipeline import load_rules
from .runs import Run
from .stages import pipeline_stages
from .summary import collect_runs

# Where each component leaves its run report, by run day. Components not listed write none.
REPORTS = {
    "bulletin-scan": "reports/scan-{day}.md",
    "perimeter-scan": "{day}-perimeter-scan-run-report.md",
    "documentation-sync": "doc-sync-runs/{day}-doc-sync.md",
}
# A document saved just after the last session ended still belongs to the run.
WRITE_GRACE = timedelta(minutes=5)

# Raw HTML in a report is shown as text, never passed through: the reports quote web
# pages. Tables are on because the scan reports use them.
_MARKDOWN = MarkdownIt("commonmark", {"html": False}).enable("table")
_RENDERED: dict[tuple[str, int], str] = {}


def find_run(settings: Settings, ident: str) -> tuple[Run, list[Run]] | None:
    runs = collect_runs(settings)
    match = next((r for r in runs if r.id == ident), None)
    return (match, runs) if match else None


def report_path(out_dir: Path, run: Run) -> Path | None:
    pattern = REPORTS.get(run.component)
    if pattern is None or run.kind != "scan":
        return None
    path = (out_dir / run.component / pattern.format(day=run.started.date().isoformat())).resolve()
    return path if path.is_relative_to(out_dir.resolve()) and path.is_file() else None


def render_markdown(path: Path) -> str:
    key = (str(path), path.stat().st_mtime_ns)
    if key not in _RENDERED:
        _RENDERED[key] = _MARKDOWN.render(path.read_text(encoding="utf-8", errors="replace"))
    return _RENDERED[key]


def written_during(items: list[Deliverable], run: Run) -> list[Deliverable]:
    """Documents of this component last saved while the run was going.

    A later rebuild saves the file again, so an older run can show fewer documents than
    it once wrote. That is said on the page rather than guessed around.
    """
    start, end = run.started, run.ended + WRITE_GRACE
    prefix = f"{run.component}/"
    return [
        d
        for d in items
        if d.path.startswith(prefix)
        # modified is local time without a zone; astimezone() reads it as local
        and start <= datetime.fromisoformat(d.modified).astimezone() <= end
    ]


def run_detail(settings: Settings, run: Run, runs: list[Run]) -> dict[str, object]:
    items = scan(settings.out_dir, load_rules(settings.scripts_dir))
    day = run.started.date()
    has_stages = run.component == "bulletin-scan" and run.kind == "scan"
    # the check stage covers the documents this run's day produced, not the whole archive
    that_day = [d for d in items if d.first_seen == day.isoformat()]
    report = report_path(settings.out_dir, run)
    return {
        **run.to_dict(),
        "stages": [
            s.to_dict()
            for s in pipeline_stages(settings.out_dir, settings.logs_dir, runs, run, that_day)
        ]
        if has_stages
        else [],
        "written": [d.to_dict() for d in written_during(items, run)],
        "report": {
            "name": report.name,
            "html": render_markdown(report),
        }
        if report
        else None,
    }
