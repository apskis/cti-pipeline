"""Every deliverable on disk, one entry per ID, with its quality check result.

Discovery follows scripts/update_state.py: every .docx outside a ``state`` folder, ID
taken from the filename, newest copy of an ID wins. The weekly and quarterly reports
are not in the pipeline's ID scheme, so they get console IDs of their own.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from datetime import date, datetime
from pathlib import Path

from .pipeline import PipelineRules

# Not in the pipeline's ID scheme; titled by week or quarter instead.
REPORT_KINDS = {
    "weekly": re.compile(r"CTI_Weekly_Report_(\d{4})_Week(\d+)"),
    "quarterly": re.compile(r"CTI_Quarterly_Strategic_Brief_Q(\d)_(\d{4})"),
}
INDEX_ROW = re.compile(r"^\|\s*(\S+)\s*\|\s*\w+\s*\|\s*(\S+)\s*\|\s*(\d{4}-\d{2}-\d{2})\s*\|")


@dataclass(frozen=True)
class Deliverable:
    id: str
    kind: str
    title: str
    path: str  # relative to the out folder, never absolute
    first_seen: str
    modified: str
    status: str  # ok | broken | unchecked
    problem: str | None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class _Found:
    ident: str
    kind: str
    path: Path


def _report_id(kind: str, match: re.Match[str]) -> str:
    if kind == "weekly":
        return f"WK-{match.group(1)}-{int(match.group(2)):02d}"
    return f"QB-{match.group(2)}-Q{match.group(1)}"


def _identify(path: Path, rules: PipelineRules) -> _Found | None:
    for kind, pattern in rules.kinds.items():
        if m := pattern.search(path.name):
            return _Found(m.group(0), kind, path)
    for kind, pattern in REPORT_KINDS.items():
        if m := pattern.search(path.name):
            return _Found(_report_id(kind, m), kind, path)
    return None


def _docx_files(out_dir: Path) -> list[Path]:
    """Every .docx under out, skipping state folders, newest first."""
    files = [
        f
        for f in out_dir.rglob("*.docx")
        if "state" not in f.relative_to(out_dir).parts and not f.name.startswith("~$")
    ]
    return sorted(files, key=lambda f: f.stat().st_mtime, reverse=True)


def _first_seen_dates(out_dir: Path) -> dict[str, str]:
    """Earliest 'first seen' date per ID from every component's deliverables index."""
    seen: dict[str, str] = {}
    for index in out_dir.glob("*/state/deliverables-index.md"):
        for line in index.read_text(encoding="utf-8").splitlines():
            if m := INDEX_ROW.match(line):
                ident, day = m.group(1), m.group(3)
                if ident not in seen or day < seen[ident]:
                    seen[ident] = day
    return seen


def _title(found: _Found) -> str:
    """Readable title from the filename, e.g. CTI26-137-IBM_Aspera_Faspex_RCE -> IBM Aspera..."""
    stem = found.path.stem.replace(found.ident, "")
    return re.sub(r"[_\s]+", " ", stem).strip(" -") or found.ident


# Parsing every .docx takes seconds, so results are kept per file and modification time:
# a document is parsed again only after it changes.
_CHECKS: dict[tuple[str, int], str | None] = {}


def _status(found: _Found, rules: PipelineRules) -> tuple[str, str | None]:
    if found.kind not in rules.checked_kinds:
        return "unchecked", None
    key = (str(found.path), found.path.stat().st_mtime_ns)
    if key not in _CHECKS:
        _CHECKS[key] = rules.shell_reason(found.path, found.ident, found.kind)
    problem = _CHECKS[key]
    return ("broken", problem) if problem else ("ok", None)


def scan(out_dir: Path, rules: PipelineRules) -> list[Deliverable]:
    """All deliverables, newest first by first seen date."""
    first_seen = _first_seen_dates(out_dir)
    chosen: dict[str, _Found] = {}
    for path in _docx_files(out_dir):
        found = _identify(path, rules)
        if found and found.ident not in chosen:
            chosen[found.ident] = found
    items = [_build(found, out_dir, first_seen, rules) for found in chosen.values()]
    return sorted(items, key=lambda d: (d.first_seen, d.id), reverse=True)


def _build(
    found: _Found, out_dir: Path, first_seen: dict[str, str], rules: PipelineRules
) -> Deliverable:
    modified = datetime.fromtimestamp(found.path.stat().st_mtime)
    status, problem = _status(found, rules)
    return Deliverable(
        id=found.ident,
        kind=found.kind,
        title=_title(found),
        path=found.path.relative_to(out_dir).as_posix(),
        first_seen=first_seen.get(found.ident, modified.date().isoformat()),
        modified=modified.isoformat(timespec="seconds"),
        status=status,
        problem=problem,
    )


def counts_by_kind(items: list[Deliverable]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        counts[item.kind] = counts.get(item.kind, 0) + 1
    return counts


def first_seen_on(items: list[Deliverable], day: date) -> list[Deliverable]:
    return [d for d in items if d.first_seen == day.isoformat()]
