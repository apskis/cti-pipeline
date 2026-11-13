"""The Reviewer's verdicts, one JSON file per document under <component>/state/reviews.

The Reviewer is a model session, so its files are treated as untrusted input: anything
that does not have the expected shape is skipped, and every string is length capped.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path

log = logging.getLogger(__name__)

VERDICTS = ("pass", "flag")
MAX_FINDINGS = 20
MAX_TEXT = 1000


@dataclass(frozen=True)
class Finding:
    claim: str
    problem: str
    source: str


@dataclass(frozen=True)
class Review:
    verdict: str  # pass | flag
    summary: str
    checked_at: str
    findings: list[Finding]
    # True when the document changed after it was reviewed, so the verdict may be out of date.
    stale: bool = False


def _text(value: object) -> str:
    return value[:MAX_TEXT] if isinstance(value, str) else ""


def _finding(row: object) -> Finding | None:
    if not isinstance(row, dict):
        return None
    claim, problem = _text(row.get("claim")), _text(row.get("problem"))
    if not problem:
        return None
    return Finding(claim=claim, problem=problem, source=_text(row.get("source")))


def parse(data: object) -> Review | None:
    """A Review from the Reviewer's JSON, or None when it is not the agreed shape."""
    if not isinstance(data, dict) or data.get("verdict") not in VERDICTS:
        return None
    rows = data.get("findings")
    findings = [f for r in (rows if isinstance(rows, list) else []) if (f := _finding(r))]
    # A flag with no readable finding still tells the reader to look, so it stays a flag.
    return Review(
        verdict=data["verdict"],
        summary=_text(data.get("summary")),
        checked_at=_text(data.get("checked_at")),
        findings=findings[:MAX_FINDINGS],
    )


def load(out_dir: Path) -> dict[str, tuple[Review, float]]:
    """Every readable review by document ID, with the review file's modification time."""
    found: dict[str, tuple[Review, float]] = {}
    for file in out_dir.glob("*/state/reviews/*.json"):
        try:
            review = parse(json.loads(file.read_text(encoding="utf-8")))
        except (OSError, ValueError):
            review = None
        if review is None:
            log.warning("Skipping a review file that is not in the agreed shape: %s", file.name)
            continue
        mtime = file.stat().st_mtime
        if file.stem not in found or mtime > found[file.stem][1]:
            found[file.stem] = (review, mtime)
    return found
