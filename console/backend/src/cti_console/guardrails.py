"""The self check loop's outcome, one JSON file per document under <component>/state/guardrails.

scripts/self_check.py writes these after every review round: which guardrail gates passed,
how many rounds the AI took, and what (if anything) it could not fix. The console shows
the outcome so a human can read it in seconds. The files carry text a model wrote, so
anything not in the agreed shape is skipped and every string is length capped.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path

log = logging.getLogger(__name__)

# verified: passed first time. self-corrected: failed, fixed itself, passed.
# fixing: a run stopped mid loop. needs-human: still failing after the last round.
STATUSES = ("verified", "self-corrected", "fixing", "needs-human")
# In the order the panel lists them; the labels live in the frontend.
GATES = ("sources", "cve_facts", "house_rules", "consistency", "reasoning", "wording")
GATE_RESULTS = ("pass", "flag", "unchecked")
MAX_ISSUES = 10
MAX_TEXT = 500


@dataclass(frozen=True)
class Guardrail:
    status: str
    gates: dict[str, str]
    rounds: int
    # Rounds that failed before the last one: how many times the AI caught itself.
    corrections: int
    open_issues: list[str]
    lint_warnings: int
    updated_at: str
    # True when the document changed after this record, so it may be out of date.
    stale: bool = False


def _text(value: object) -> str:
    return value[:MAX_TEXT] if isinstance(value, str) else ""


def _gates(raw: object) -> dict[str, str]:
    given = raw if isinstance(raw, dict) else {}
    return {g: v if (v := given.get(g)) in GATE_RESULTS else "unchecked" for g in GATES}


def _rounds(raw: object) -> list[dict[str, object]]:
    return [r for r in raw if isinstance(r, dict)] if isinstance(raw, list) else []


def parse(data: object) -> Guardrail | None:
    """A Guardrail from self_check.py's JSON, or None when it is not the agreed shape."""
    if not isinstance(data, dict) or data.get("status") not in STATUSES:
        return None
    rounds = _rounds(data.get("rounds"))
    issues = data.get("open_issues")
    lint = data.get("lint")
    return Guardrail(
        status=data["status"],
        gates=_gates(data.get("gates")),
        rounds=len(rounds),
        corrections=sum(1 for r in rounds[:-1] if r.get("failed") is True),
        open_issues=[t for i in (issues if isinstance(issues, list) else []) if (t := _text(i))][
            :MAX_ISSUES
        ],
        lint_warnings=sum(
            1 for f in (lint if isinstance(lint, list) else [])
            if isinstance(f, dict) and f.get("level") == "WARN"
        ),
        updated_at=_text(data.get("updated_at")),
    )


def load(out_dir: Path) -> dict[str, tuple[Guardrail, float]]:
    """Every readable record by document ID, with the record file's modification time."""
    found: dict[str, tuple[Guardrail, float]] = {}
    for file in out_dir.glob("*/state/guardrails/*.json"):
        try:
            record = parse(json.loads(file.read_text(encoding="utf-8")))
        except (OSError, ValueError):
            record = None
        if record is None:
            log.warning("Skipping a guardrail file that is not in the agreed shape: %s", file.name)
            continue
        mtime = file.stat().st_mtime
        if file.stem not in found or mtime > found[file.stem][1]:
            found[file.stem] = (record, mtime)
    return found


def counts_by_status(records: list[Guardrail | None]) -> dict[str, int]:
    """How many documents ended in each state, for the overview tile."""
    counts = dict.fromkeys(STATUSES, 0)
    for record in records:
        if record is not None:
            counts[record.status] += 1
    return counts
