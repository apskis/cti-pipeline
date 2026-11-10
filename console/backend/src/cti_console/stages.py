"""Status of each pipeline stage for one scan run, read from the files that run left.

Every value says where it came from. When the source is missing or does not say, the
stage is "unknown" rather than a guess: a quiet console must never read as a clean run.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path

from .deliverables import Deliverable, first_seen_on
from .runs import Run

FEEDS_LINE = re.compile(
    r"\[feeds\] window (\S+)\.\.(\S+); (\d+) items from (\d+)/(\d+) feeds; failed: \[(.*?)\]"
)
# The checklist line PR #10 added, then older phrasings seen in real reports.
SEARCH_COUNT = (
    re.compile(r"web searches run\D{0,40}?(\d+)", re.IGNORECASE),
    re.compile(r"\bran (\d+) (?:web )?searches", re.IGNORECASE),
)
NO_SEARCHES = re.compile(
    r"WebSearch was available and unused|did not run the .{0,20}web searches", re.IGNORECASE
)
ENTRY_DATE = re.compile(r"^(\d{4}-\d{2}-\d{2}) \| ")
ASSIGNED_ID = re.compile(r"\b(?:bulletin|hunt):\s*((?:CTI|TH)\d{2}-\d{2,})")


@dataclass(frozen=True)
class Stage:
    key: str
    label: str
    value: str
    status: str  # ok | warn | fail | unknown
    note: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


def _read(path: Path) -> str | None:
    return path.read_text(encoding="utf-8", errors="replace") if path.is_file() else None


def feeds_stage(logs_dir: Path, day: date) -> Stage:
    for log in sorted(logs_dir.glob(f"bulletin-scan*{day.isoformat()}*.log")):
        if m := FEEDS_LINE.search(_read(log) or ""):
            items, ok, total = int(m[3]), int(m[4]), int(m[5])
            # the log prints a Python list repr: ['A (HTTP 404)', 'B']
            failed = m[6].replace("'", "").replace('"', "").strip()
            status = "ok" if ok == total else "warn"
            note = f"Failed: {failed}" if failed else "Every feed answered"
            return Stage("feeds", "Feeds", f"{items} items, {ok} of {total} up", status, note)
    return Stage("feeds", "Feeds", "no log", "unknown", f"No scan log for {day} in logs/")


def search_count(report: str) -> int | None:
    for pattern in SEARCH_COUNT:
        if m := pattern.search(report):
            return int(m[1])
    return 0 if NO_SEARCHES.search(report) else None


def scan_stage(out_dir: Path, run: Run) -> Stage:
    minutes = round(sum(s.duration_s for s in run.sessions if not s.is_build) / 60)
    day = run.started.date().isoformat()
    report = _read(out_dir / "bulletin-scan" / "reports" / f"scan-{day}.md")
    if report is None:
        return Stage("scan", "Scan", f"{minutes} min", "unknown", f"No scan-{day}.md report")
    count = search_count(report)
    if count is None:
        return Stage(
            "scan",
            "Scan",
            f"{minutes} min",
            "unknown",
            "The scan report does not give a web search count",
        )
    status = "ok" if count > 0 else "warn"
    return Stage(
        "scan",
        "Scan",
        f"{minutes} min, {count} searches",
        status,
        "Web searches run, from the scan report",
    )


def assigned_ids(dedup_log: str, day: date) -> set[str]:
    """IDs first written into the dedup log on ``day``.

    An UPDATE entry repeats the ID its item already had, so an ID that appears on an
    earlier date was not assigned that day.
    """
    on_day: set[str] = set()
    earlier: set[str] = set()
    current = ""
    for line in dedup_log.splitlines():
        if m := ENTRY_DATE.match(line):
            current = m[1]
        found = ASSIGNED_ID.findall(line)
        if current == day.isoformat():
            on_day.update(found)
        elif current < day.isoformat():
            earlier.update(found)
    return on_day - earlier


def triage_stage(out_dir: Path, day: date) -> Stage:
    text = _read(out_dir / "bulletin-scan" / "state" / "dedup-log.md")
    if text is None:
        return Stage("triage", "Triage", "no log", "unknown", "No dedup log")
    ids = assigned_ids(text, day)
    bulletins = sum(1 for i in ids if i.startswith("CTI"))
    note = f"{bulletins} bulletins and {len(ids) - bulletins} hunts assigned"
    return Stage("triage", "Triage", f"{len(ids)} new IDs", "ok", note)


def build_stage(runs: list[Run], day: date) -> Stage:
    passes = [
        s
        for r in runs
        if r.component == "bulletin-scan"
        for s in r.sessions
        if s.is_build and s.started.date() == day
    ]
    failed = sum(1 for s in passes if not s.ok)
    status = "fail" if failed else ("ok" if passes else "unknown")
    note = f"{failed} passes failed" if failed else "Builder passes on this day"
    return Stage("build", "Build", f"{len(passes)} passes", status, note)


def check_stage(items: list[Deliverable]) -> Stage:
    checked = [d for d in items if d.status != "unchecked"]
    broken = [d for d in checked if d.status == "broken"]
    status = "fail" if broken else "ok"
    note = f"Broken: {', '.join(d.id for d in broken[:5])}" if broken else "No broken documents"
    return Stage("check", "Check", f"{len(checked)} docs, {len(broken)} broken", status, note)


def deliver_stage(items: list[Deliverable], day: date) -> Stage:
    new = first_seen_on(items, day)
    return Stage(
        "deliver",
        "Deliver",
        f"{len(new)} new",
        "ok" if new else "unknown",
        f"Documents first seen on {day}",
    )


def pipeline_stages(
    out_dir: Path, logs_dir: Path, runs: list[Run], run: Run, items: list[Deliverable]
) -> list[Stage]:
    day = run.started.date()
    return [
        feeds_stage(logs_dir, day),
        scan_stage(out_dir, run),
        triage_stage(out_dir, day),
        build_stage(runs, day),
        check_stage(items),
        deliver_stage(items, day),
    ]
