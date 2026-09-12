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

# id pattern per kind. The whole output tree is searched apart from ``state`` (scratch and
# ledgers), the same rule pending_deliverables.py uses: a builder that saves outside the
# canonical folder must not make the deliverable invisible to the tally, which is how the
# index and the next IDs came to disagree with what was actually on disk.
KINDS = {
    "bulletin": re.compile(r"\bCTI(\d{2})-(\d{2})\b"),
    "hunt": re.compile(r"\bTH(\d{2})-(\d{2})\b"),
    "awareness": re.compile(r"\bAWR-\d{4}-\d{2}-\d{2}\b"),
    "cve_brief": re.compile(r"\bCVE-VM-\d{4}-\d{2}-\d{2}\b"),
    "exposure": re.compile(r"\bCTI-EXP-[A-Za-z0-9_]+"),
    "detection": re.compile(r"\bCTI-DET-[A-Za-z0-9_]+"),
}


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else ""


def _docx_files() -> list[Path]:
    """Every deliverable .docx, skipping state/ so scratch drafts never count as output."""
    return sorted(f for f in OUT.rglob("*.docx") if f.relative_to(OUT).parts[0] != "state")


def collect() -> dict[str, list[tuple[str, Path]]]:
    """Map kind -> [(id, file)] for every deliverable on disk, newest copy of an ID first.

    An ID can appear more than once when a builder saved to two folders. Ordering by
    modification time keeps the most recent copy first, so the index names the one the
    pipeline wrote last rather than whichever the filesystem happened to yield.
    """
    found: dict[str, list[tuple[str, Path]]] = {}
    files = sorted(_docx_files(), key=lambda f: f.stat().st_mtime, reverse=True)
    for kind, pattern in KINDS.items():
        for f in files:
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
            if ident not in new:  # a deliverable saved twice is one new deliverable
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
    # count distinct IDs, not files: one deliverable saved to two folders is still one
    print("[state] deliverables on disk: "
          + ", ".join(f"{k}={len({i for i, _ in v})}" for k, v in sorted(found.items())))
    for kind, items in sorted(found.items()):
        dupes = {i for i, _ in items if sum(1 for j, _ in items if j == i) > 1}
        for ident in sorted(dupes):
            where = [f.relative_to(OUT).as_posix() for i, f in items if i == ident]
            print(f"[state] {ident} ({kind}) has {len(where)} copies, newest first: {where}")
    print(f"[state] new this run: {new or 'none'}; next ids -> {NEXT_IDS}")
    return 0


def snapshot() -> int:
    STATE.mkdir(parents=True, exist_ok=True)
    HASH_FILE.write_text(_hash(DEDUP))
    return 0


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "finalize"
    raise SystemExit({"snapshot": snapshot, "finalize": finalize}[cmd]())
