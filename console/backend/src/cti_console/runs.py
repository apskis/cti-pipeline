"""Runs, rebuilt from every component's state/cost-log.jsonl.

The cost log has one line per Claude session, written when the session ends. A run is
not recorded anywhere, so it is inferred: a component's sessions belong to one run until
a scan session starts a new one or the gap between sessions is long.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

log = logging.getLogger(__name__)

# Builder passes start seconds after the previous session ends. Half an hour apart is a
# separate run: a manual rebuild started later the same day.
RUN_GAP = timedelta(minutes=30)


@dataclass(frozen=True)
class Session:
    component: str
    mode: str
    label: str
    ended: datetime
    cost_usd: float
    duration_s: float
    turns: int
    ok: bool

    @property
    def started(self) -> datetime:
        return self.ended - timedelta(seconds=self.duration_s)

    @property
    def is_build(self) -> bool:
        return self.label.startswith("build")

    @property
    def is_follow_on(self) -> bool:
        """A builder or reviewer session: it continues the run its scan started."""
        return self.is_build or self.label == "review"


@dataclass
class Run:
    component: str
    mode: str
    sessions: list[Session] = field(default_factory=list)

    @property
    def id(self) -> str:
        return f"{self.component}-{self.started:%Y%m%dT%H%M%S}"

    @property
    def started(self) -> datetime:
        return self.sessions[0].started

    @property
    def ended(self) -> datetime:
        return self.sessions[-1].ended

    @property
    def kind(self) -> str:
        if any(not s.is_follow_on for s in self.sessions):
            return "scan"
        return "build only"

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "component": self.component,
            "mode": self.mode,
            "kind": self.kind,
            "started": self.started.isoformat(),
            "ended": self.ended.isoformat(),
            "duration_s": round(sum(s.duration_s for s in self.sessions)),
            "cost_usd": round(sum(s.cost_usd for s in self.sessions), 2),
            "ok": all(s.ok for s in self.sessions),
            "sessions": [_session_dict(s) for s in self.sessions],
        }


def _session_dict(s: Session) -> dict[str, object]:
    return {
        "label": s.label,
        "started": s.started.isoformat(),
        "ended": s.ended.isoformat(),
        "duration_s": round(s.duration_s),
        "cost_usd": round(s.cost_usd, 2),
        "turns": s.turns,
        "ok": s.ok,
    }


def _parse(line: str) -> Session:
    row = json.loads(line)
    return Session(
        component=row["component"],
        mode=row.get("mode", ""),
        label=row["label"],
        ended=datetime.fromisoformat(row["ts"]),
        cost_usd=float(row.get("cost_usd", 0.0)),
        duration_s=float(row.get("duration_ms", 0)) / 1000,
        turns=int(row.get("turns", 0)),
        ok=row.get("exit_code", 0) == 0 and not row.get("is_error", False),
    )


def load_sessions(out_dir: Path) -> list[Session]:
    """Every session in every component's cost log, oldest first. Bad lines are skipped."""
    sessions: list[Session] = []
    for path in sorted(out_dir.glob("*/state/cost-log.jsonl")):
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            try:
                sessions.append(_parse(line))
            except (ValueError, KeyError, TypeError) as exc:
                log.warning("skipping %s line %d: %s", path.name, number, exc)
    return sorted(sessions, key=lambda s: s.started)


def group_runs(sessions: list[Session]) -> list[Run]:
    """Group sessions into runs per component, oldest run first."""
    runs: list[Run] = []
    current: dict[str, Run] = {}
    for s in sessions:
        run = current.get(s.component)
        starts_new = run is None or not s.is_follow_on or s.started - run.ended > RUN_GAP
        if starts_new:
            run = Run(component=s.component, mode=s.mode)
            current[s.component] = run
            runs.append(run)
        run.sessions.append(s)
    return sorted(runs, key=lambda r: r.started)
