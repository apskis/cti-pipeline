"""Every deliverable on disk, one entry per ID, with its quality check result.

Discovery follows scripts/update_state.py: every .docx outside a ``state`` folder, ID
taken from the filename, newest copy of an ID wins. The weekly and quarterly reports
are not in the pipeline's ID scheme, so they get console IDs of their own.
"""

from __future__ import annotations

import json
import logging
import os
import re
import threading
from dataclasses import asdict, dataclass, replace
from datetime import date, datetime
from pathlib import Path

from .pipeline import PipelineRules
from .reviews import Review
from .reviews import load as load_reviews

log = logging.getLogger(__name__)

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
    # The Reviewer's verdict, or None when no review exists for this document.
    review: Review | None = None

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
# a document is parsed again only after it changes. They are also saved to disk (see
# save_checks), so a restarted console does not parse all of them again.
_CHECKS: dict[tuple[str, int], str | None] = {}
# The startup warm and the first requests scan at once; this way each report is parsed by
# one of them, not by all of them competing for the same CPU.
_CHECKING = threading.Lock()


def _is_check_row(row: object) -> bool:
    return (
        isinstance(row, list)
        and len(row) == 3
        and isinstance(row[0], str)
        and isinstance(row[1], int)
        and (row[2] is None or isinstance(row[2], str))
    )


def load_checks(file: Path, rules: PipelineRules) -> int:
    """Take an earlier run's check results; returns how many. Other rules' results are
    ignored, so a check the pipeline tightened runs again on every document."""
    try:
        data = json.loads(file.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return 0
    if not isinstance(data, dict) or data.get("rules") != rules.version:
        return 0
    rows = [r for r in data.get("checks", []) if _is_check_row(r)]
    for path, mtime, problem in rows:
        _CHECKS.setdefault((path, mtime), problem)
    return len(rows)


def _still_current(path: str, mtime: int) -> bool:
    try:
        return Path(path).stat().st_mtime_ns == mtime
    except OSError:
        return False


def save_checks(file: Path, rules: PipelineRules) -> None:
    """Write the results for documents as they are now; older versions are left out."""
    rows = [[p, m, r] for (p, m), r in list(_CHECKS.items()) if _still_current(p, m)]
    file.parent.mkdir(parents=True, exist_ok=True)
    partial = file.with_suffix(".part")
    partial.write_text(json.dumps({"rules": rules.version, "checks": rows}), encoding="utf-8")
    os.replace(partial, file)  # a crash mid write never leaves a half file behind


def warm_checks(out_dir: Path, rules: PipelineRules, file: Path) -> None:
    """Check every document not checked yet, then save, so the first page load is quick."""
    try:
        scan(out_dir, rules)
        save_checks(file, rules)
    except Exception:  # runs on its own thread: a failure must be logged, not lost
        log.exception("Could not check the reports ahead of time")


def _status(found: _Found, rules: PipelineRules) -> tuple[str, str | None]:
    if found.kind not in rules.checked_kinds:
        return "unchecked", None
    key = (str(found.path), found.path.stat().st_mtime_ns)
    if key not in _CHECKS:
        with _CHECKING:
            if key not in _CHECKS:  # another thread may have checked it while this waited
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
    reviews = load_reviews(out_dir)
    items = [_build(found, out_dir, first_seen, rules, reviews) for found in chosen.values()]
    return sorted(items, key=lambda d: (d.first_seen, d.id), reverse=True)


def _review(found: _Found, reviews: dict[str, tuple[Review, float]]) -> Review | None:
    if found.ident not in reviews:
        return None
    review, reviewed = reviews[found.ident]
    return replace(review, stale=found.path.stat().st_mtime > reviewed)


def _build(
    found: _Found,
    out_dir: Path,
    first_seen: dict[str, str],
    rules: PipelineRules,
    reviews: dict[str, tuple[Review, float]],
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
        review=_review(found, reviews),
    )


def counts_by_kind(items: list[Deliverable]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        counts[item.kind] = counts.get(item.kind, 0) + 1
    return counts


def first_seen_on(items: list[Deliverable], day: date) -> list[Deliverable]:
    return [d for d in items if d.first_seen == day.isoformat()]
