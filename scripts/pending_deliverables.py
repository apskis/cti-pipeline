#!/usr/bin/env python3
"""List deliverables the dedup log promises that do not yet exist on disk.

The scan pass assigns IDs (``bulletin:CTI26-07``, ``hunt:TH26-03``, an AWR id for
today) in ``state/dedup-log.md``. This driver turns those promises into a work
batch for the builder pass: for each pending ID it emits the log entry that
carries the evidence, so the builder never has to research from scratch.

Exit 0 and write the batch when something is pending; exit 3 when nothing is.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
from pathlib import Path

OUT = Path(os.environ.get("OUTPUT_DIR", "out")).resolve()
DEDUP = OUT / "state" / "dedup-log.md"
BULLETIN = re.compile(r"bulletin:\s*(CTI\d{2}-\d{2})")
HUNT = re.compile(r"hunt:\s*(TH\d{2}-\d{2})")
AWR = re.compile(r"\b(AWR-\d{4}-\d{2}-\d{2})\b")


def on_disk(pattern: str, roots: list[str]) -> set[str]:
    ids: set[str] = set()
    rx = re.compile(pattern)
    for root in roots:
        for f in (OUT / root).rglob("*.docx") if (OUT / root).exists() else []:
            m = rx.search(f.name)
            if m:
                ids.add(m.group(0))
    return ids


def entries(text: str) -> list[str]:
    """Split the log into entry blocks: a dated header line plus its indented lines."""
    blocks: list[str] = []
    current: list[str] = []
    for line in text.splitlines():
        if re.match(r"^\d{4}-\d{2}-\d{2} \| ", line):
            if current:
                blocks.append("\n".join(current))
            current = [line]
        elif current and (line.startswith("  ") or not line.strip()):
            current.append(line)
        elif current:
            blocks.append("\n".join(current)); current = []
    if current:
        blocks.append("\n".join(current))
    return blocks


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--batch", type=int, default=4, help="max items per builder pass")
    ap.add_argument("--out", type=Path, default=OUT / "state" / "_work" / "pending.json")
    ap.add_argument("--today", default=dt.date.today().isoformat())
    args = ap.parse_args()
    if not DEDUP.exists():
        print("[pending] no dedup log; nothing to build"); return 3

    text = DEDUP.read_text()
    have_b = on_disk(r"CTI\d{2}-\d{2}", ["bulletins"])
    have_h = on_disk(r"TH\d{2}-\d{2}", ["hunts/packages", "hunts/archive"])
    have_a = on_disk(r"AWR-\d{4}-\d{2}-\d{2}", ["employee-posts"])

    items: list[dict] = []
    seen: set[str] = set()
    for block in entries(text):
        for rx, kind, have in ((BULLETIN, "bulletin", have_b), (HUNT, "hunt", have_h)):
            for ident in rx.findall(block):
                if ident not in have and ident not in seen:
                    seen.add(ident)
                    items.append({"id": ident, "kind": kind, "evidence": block.strip()})
    awr = f"AWR-{args.today}"
    if awr in text and awr not in have_a:
        items.append({"id": awr, "kind": "awareness", "evidence": "topic chosen in today's scan report and dedup log"})
    brief = f"CVE-VM-{args.today}"
    if not (OUT / "registers" / f"{brief}.docx").exists() and (OUT / "registers" / "CVE_Register_2026.xlsx").exists():
        items.append({"id": brief, "kind": "cve_brief", "evidence": "build from registers/CVE_Register_2026.xlsx, Latest Run tab"})

    remaining = len(items)
    # bulletins and hunts carry the most work; brief and awareness are cheap, keep them in the first batch
    order = {"cve_brief": 0, "awareness": 1, "bulletin": 2, "hunt": 3}
    items.sort(key=lambda i: order[i["kind"]])
    batch = items[: args.batch]
    summary = ", ".join(f"{i['kind']}={sum(1 for x in items if x['kind']==i['kind'])}" for i in {x["kind"]: x for x in items}.values())
    if not batch:
        print("[pending] nothing pending: every ID in the dedup log has a file on disk"); return 3
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps({"today": args.today, "remaining": remaining, "batch": batch}, indent=2))
    print(f"[pending] {remaining} pending ({summary}); this batch: {[i['id'] for i in batch]} -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
