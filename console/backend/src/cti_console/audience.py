"""Who each report is for, read from the build specs the pipeline leaves behind.

A bulletin spec names its teams in two places: the audience line ("DRAFT for April's
review: Product Security, IT Security") and the team on each question for the reader
(``[["SOC", "Is ...?"], ...]``). Team names drift from report to report ("SOC",
"Security Operations", "Security team"), so a stakeholder matches on their team name
or on any of the other names they are known by.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from .stakeholders import Stakeholder

ID_KEYS = ("report_id", "hunt_id", "id")
MAX_SPEC_BYTES = 2_000_000
# "DRAFT for April's review: A, B" or "... review — A, B": the teams follow the break.
AUDIENCE_BREAK = re.compile(r"\s(?:—|–|-|:)\s|:\s")
NOT_A_TEAM = re.compile(r"\b(draft|review)\b", re.IGNORECASE)


@dataclass
class TeamAsk:
    name: str
    questions: list[str] = field(default_factory=list)


@dataclass
class ReportAudience:
    spec: str  # relative to out/
    teams: list[TeamAsk]


def normalise(name: str) -> str:
    """Lower case, '&' as 'and', punctuation and a trailing 'team(s)' dropped."""
    text = name.lower().replace("&", " and ")
    text = re.sub(r"[^a-z0-9/ ]+", " ", text)
    text = " ".join(text.split())
    return re.sub(r"\s+teams?$", "", text).strip()


def name_keys(name: str) -> set[str]:
    """The whole name and, for 'DevOps / Platform Engineering', each part."""
    whole = normalise(name)
    parts = {p.strip() for p in whole.split("/") if p.strip()}
    return {whole.replace(" / ", "/"), *parts} - {""}


def stakeholder_keys(person: Stakeholder) -> set[str]:
    keys: set[str] = set()
    for name in [person.team, *person.also_known_as]:
        keys |= name_keys(name)
    return keys


def _audience_teams(line: object) -> list[str]:
    if not isinstance(line, str):
        return []
    pieces = AUDIENCE_BREAK.split(line, maxsplit=1)
    if len(pieces) < 2:
        return []
    names = [n.strip(" .") for n in pieces[1].split(",")]
    return [n for n in names if n and len(n) <= 80 and not NOT_A_TEAM.search(n)]


def _question_teams(questions: object) -> list[TeamAsk]:
    """Both spec shapes: [[team, question], ...] and [{"audience", "items"}, ...]."""
    asks: dict[str, TeamAsk] = {}
    if not isinstance(questions, list):
        return []
    for item in questions:
        team, texts = None, []
        if isinstance(item, list) and len(item) >= 2 and isinstance(item[0], str):
            team, texts = item[0], [str(item[1])]
        elif isinstance(item, dict) and isinstance(item.get("audience"), str):
            team = item["audience"]
            texts = [str(t) for t in item.get("items", []) if isinstance(t, str | int | float)]
        if team and team.strip() and len(team) <= 80:
            ask = asks.setdefault(team.strip(), TeamAsk(team.strip()))
            ask.questions.extend(t for t in texts if t)
    return list(asks.values())


def _teams(spec: dict[str, object]) -> list[TeamAsk]:
    teams = _question_teams(spec.get("questions"))
    known = {normalise(t.name) for t in teams}
    for name in _audience_teams(spec.get("audience")):
        if normalise(name) not in known:
            known.add(normalise(name))
            teams.append(TeamAsk(name))
    return teams


_PARSED: dict[Path, tuple[int, str | None, list[TeamAsk]]] = {}


def _read_spec(path: Path) -> tuple[str | None, list[TeamAsk]]:
    """The spec's report ID and teams, cached until the file changes."""
    mtime = path.stat().st_mtime_ns
    cached = _PARSED.get(path)
    if cached and cached[0] == mtime:
        return cached[1], cached[2]
    ident: str | None = None
    teams: list[TeamAsk] = []
    try:
        if path.stat().st_size <= MAX_SPEC_BYTES:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                ident = next((data[k] for k in ID_KEYS if isinstance(data.get(k), str)), None)
                teams = _teams(data) if ident else []
    except (OSError, ValueError):
        pass
    _PARSED[path] = (mtime, ident, teams)
    return ident, teams


def report_audiences(out_dir: Path) -> dict[str, ReportAudience]:
    """Teams per report ID, from the newest spec that names that ID."""
    specs = [p for p in out_dir.rglob("*.json") if "_backup" not in p.relative_to(out_dir).parts]
    specs.sort(key=lambda p: p.stat().st_mtime)  # oldest first, so newer ones win
    found: dict[str, ReportAudience] = {}
    for path in specs:
        ident, teams = _read_spec(path)
        if ident and teams:
            found[ident] = ReportAudience(path.relative_to(out_dir).as_posix(), teams)
    return found


def audience_view(out_dir: Path, people: list[Stakeholder]) -> dict[str, object]:
    """Each report's teams with the stakeholders who match, and teams nobody covers."""
    keys = {p.id: stakeholder_keys(p) for p in people}
    reports: dict[str, object] = {}
    unmatched: dict[str, dict[str, object]] = {}
    for ident, audience in sorted(report_audiences(out_dir).items()):
        teams = []
        for team in audience.teams:
            wanted = name_keys(team.name)
            matched = [pid for pid, k in keys.items() if wanted & k]
            teams.append({"name": team.name, "questions": team.questions, "stakeholders": matched})
            if not matched:
                entry = unmatched.setdefault(
                    normalise(team.name), {"team": team.name, "reports": []}
                )
                entry["reports"].append(ident)  # type: ignore[union-attr]
        reports[ident] = {"spec": audience.spec, "teams": teams}
    gaps = sorted(unmatched.values(), key=lambda e: -len(e["reports"]))  # type: ignore[arg-type]
    return {"reports": reports, "unmatched": gaps}
