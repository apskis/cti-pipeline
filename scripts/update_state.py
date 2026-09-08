#!/usr/bin/env python3
"""Deterministic run state: next IDs and a deliverables index from files on disk.

The model keeps the dedup log, but a run must not depend on it remembering to
write. This script runs twice per run:

  snapshot   before the model starts: remember the dedup log's hash
  finalize   after it finishes: rebuild state/next-ids.md and
             state/deliverables-index.md from the deliverables actually present,
             and append a run manifest to the dedup log if the model left it
             untouched, so the next run still sees what this one produced.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import os
import re
import sys
from pathlib import Path

OUT = Path(os.environ.get("OUTPUT_DIR", "out")).resolve()
STATE = OUT / "state"
DEDUP = STATE / "dedup-log.md"
HASH_FILE = STATE / ".dedup-log.prehash"
INDEX = STATE / "deliverables-index.md"
NEXT_IDS = STATE / "next-ids.md"

# id pattern -> (label, glob roots)
KINDS = {
    "bulletin": (re.compile(r"\bCTI(\d{2})-(\d{2})\b"), ["bulletins"]),
    "hunt": (re.compile(r"\bTH(\d{2})-(\d{2})\b"), ["hunts/packages", "hunts/archive"]),
    "awareness": (re.compile(r"\bAWR-\d{4}-\d{2}-\d{2}\b"), ["employee-posts"]),
    "cve_brief": (re.compile(r"\bCVE-VM-\d{4}-\d{2}-\d{2}\b"), ["registers"]),
    "exposure": (re.compile(r"\bCTI-EXP-[A-Za-z0-9_]+"), ["exposure-advisories"]),
    "detection": (re.compile(r"\bCTI-DET-[A-Za-z0-9_]+"), ["detection-handoffs"]),
}


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else ""


def _docx_files(roots: list[str]) -> list[Path]:
    files: list[Path] = []
    for root in roots:
        files += sorted((OUT / root).rglob("*.docx")) if (OUT / root).exists() else []
    return files


def collect() -> dict[str, list[tuple[str, Path]]]:
    """Map kind -> [(id, file)] for every deliverable on disk."""
    found: dict[str, list[tuple[str, Path]]] = {}
    for kind, (pattern, roots) in KINDS.items():
        for f in _docx_files(roots):
            m = pattern.search(f.name)
            if m:
                found.setdefault(kind, []).append((m.group(0), f))
    return found


def next_sequential(found: list[tuple[str, Path]], prefix: str, year: str) -> str:
    nums = [int(i.split("-")[1]) for i, _ in found if i.startswith(f"{prefix}{year}-")]
    return f"{prefix}{year}-{(max(nums) + 1 if nums else 1):02d}"


def write_next_ids(found: dict, today: str) -> None:
    year = today[2:4]
    STATE.mkdir(parents=True, exist_ok=True)
    NEXT_IDS.write_text(
        "# Next available IDs (computed from files on disk; this file wins over the dedup log)\n\n"
        f"- Next Bulletin ID: {next_sequential(found.get('bulletin', []), 'CTI', year)}\n"
        f"- Next Hunt ID: {next_sequential(found.get('hunt', []), 'TH', year)}\n"
        f"- Computed: {today}\n")


def write_index(found: dict, today: str) -> list[str]:
    """Append deliverables not yet indexed; return the new IDs."""
    existing = INDEX.read_text() if INDEX.exists() else ""
    lines = [] if existing else ["# Deliverables index (one row per file, first seen)\n",
                                 "| ID | Kind | File | First seen |", "|---|---|---|---|"]
    new: list[str] = []
    for kind, items in sorted(found.items()):
        for ident, f in items:
            rel = f.relative_to(OUT).as_posix()
            if f"| {rel} |" in existing:
                continue
            lines.append(f"| {ident} | {kind} | {rel} | {today} |")
            new.append(ident)
    if lines:
        with INDEX.open("a") as fh:
            fh.write("\n".join(lines) + "\n")
    return new


def finalize() -> int:
    today = dt.date.today().isoformat()
    found = collect()
    write_next_ids(found, today)
    new = write_index(found, today)
    untouched = HASH_FILE.exists() and HASH_FILE.read_text().strip() == _hash(DEDUP)
    if untouched:
        print("WARNING: dedup log unchanged by this run; appending a run manifest", file=sys.stderr)
        with DEDUP.open("a") as fh:
            fh.write(f"\n## RUN MANIFEST {today} (auto, model did not update this log)\n")
            for ident in new:
                fh.write(f"- {today} | produced {ident} (see state/deliverables-index.md)\n")
    HASH_FILE.unlink(missing_ok=True)
    print(f"[state] deliverables on disk: " + ", ".join(f"{k}={len(v)}" for k, v in sorted(found.items())))
    print(f"[state] new this run: {new or 'none'}; next ids -> {NEXT_IDS}")
    return 0


def snapshot() -> int:
    STATE.mkdir(parents=True, exist_ok=True)
    HASH_FILE.write_text(_hash(DEDUP))
    return 0


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "finalize"
    raise SystemExit({"snapshot": snapshot, "finalize": finalize}[cmd]())
