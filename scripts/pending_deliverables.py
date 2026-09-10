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


# A file whose name carries the ID is not enough: a builder fed a spec with the wrong
# keys emits a hollow document with placeholder text, and that must be rebuilt.
MIN_PARAS = {"bulletin": 15, "hunt": 30, "awareness": 8}
PLACEHOLDERS = ("TH-26-XX", "TH-26-NN", "CTIYY-NN")
# Sections April removed from the package format on 2026-08-24. Their presence means a
# reverted builder or a spec still carrying the old keys, so the document is rebuilt.
REMOVED_SECTIONS = {"hunt": ("Findings Classification Key", "Coverage & Gaps", "Execution Log",
                             "Outcome & Classification", "Overall Finding", "Pending Review")}


def shell_reason(path: Path, ident: str, kind: str) -> str | None:
    """Return why the document is a shell, or None when it looks complete."""
    try:
        import docx  # python-docx, present in the image
        d = docx.Document(str(path))
        paras = [p.text for p in d.paragraphs if p.text.strip()]
        text = "\n".join(paras) + "\n".join(c.text for t in d.tables for r in t.rows for c in r.cells)
        # the awareness post carries its ID in the footer only
        text += "\n".join(p.text for sec in d.sections for part in (sec.header, sec.footer) for p in part.paragraphs)
    except Exception as exc:  # unreadable file counts as missing
        return f"unreadable ({exc.__class__.__name__})"
    if ident not in text:
        return f"ID {ident} not in document text"
    if len(paras) < MIN_PARAS.get(kind, 8):
        return f"only {len(paras)} paragraphs"
    hit = next((ph for ph in PLACEHOLDERS if ph in text), None)
    if hit:
        return f"placeholder text {hit!r}"
    gone = next((sec for sec in REMOVED_SECTIONS.get(kind, ()) if sec in text), None)
    return f"carries removed section {gone!r} (reverted builder or stale spec)" if gone else None


def on_disk(pattern: str, roots: list[str], kind: str) -> tuple[set[str], dict[str, str]]:
    """IDs with a complete document, plus IDs whose document is a shell (with the reason)."""
    ids: set[str] = set(); shells: dict[str, str] = {}
    rx = re.compile(pattern)
    for root in roots:
        for f in (OUT / root).rglob("*.docx") if (OUT / root).exists() else []:
            m = rx.search(f.name)
            if not m:
                continue
            why = shell_reason(f, m.group(0), kind)
            if why:
                shells[m.group(0)] = f"{f.relative_to(OUT)}: {why}"
            else:
                ids.add(m.group(0))
    return ids, shells


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
    have_b, shell_b = on_disk(r"CTI\d{2}-\d{2}", ["bulletins"], "bulletin")
    have_h, shell_h = on_disk(r"TH\d{2}-\d{2}", ["hunts/packages", "hunts/archive"], "hunt")
    have_a, shell_a = on_disk(r"AWR-\d{4}-\d{2}-\d{2}", ["employee-posts"], "awareness")
    shells = {**shell_b, **shell_h, **shell_a}

    items: list[dict] = []
    seen: set[str] = set()
    for block in entries(text):
        for rx, kind, have in ((BULLETIN, "bulletin", have_b), (HUNT, "hunt", have_h)):
            for ident in rx.findall(block):
                if ident not in have and ident not in seen:
                    seen.add(ident)
                    item = {"id": ident, "kind": kind, "evidence": block.strip()}
                    if ident in shells:
                        item["rebuild"] = f"existing file is a shell, overwrite it: {shells[ident]}"
                    items.append(item)
    awr = f"AWR-{args.today}"
    if awr in text and awr not in have_a:
        item = {"id": awr, "kind": "awareness", "evidence": "topic chosen in today's scan report and dedup log"}
        if awr in shells:
            item["rebuild"] = f"existing file is a shell, overwrite it: {shells[awr]}"
        items.append(item)
    brief = f"CVE-VM-{args.today}"
    if not (OUT / "registers" / f"{brief}.docx").exists() and (OUT / "registers" / "CVE_Register_2026.xlsx").exists():
        items.append({"id": brief, "kind": "cve_brief", "evidence": "build from registers/CVE_Register_2026.xlsx, Latest Run tab"})

    remaining = len(items)
    # bulletins and hunts carry the most work; brief and awareness are cheap, keep them in the first batch
    order = {"cve_brief": 0, "awareness": 1, "bulletin": 2, "hunt": 3}
    items.sort(key=lambda i: order[i["kind"]])
    # a hunt package is roughly two bulletins' worth of work: weight it so a batch
    # never asks one context for more than two of them
    batch: list[dict] = []; weight = 0
    for item in items:
        w = 2 if item["kind"] == "hunt" else 1
        if batch and weight + w > args.batch:
            break
        batch.append(item); weight += w
    summary = ", ".join(f"{i['kind']}={sum(1 for x in items if x['kind']==i['kind'])}" for i in {x["kind"]: x for x in items}.values())
    if not batch:
        print("[pending] nothing pending: every ID in the dedup log has a file on disk"); return 3
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps({"today": args.today, "remaining": remaining, "batch": batch}, indent=2))
    rebuilds = [i["id"] for i in items if i.get("rebuild")]
    print(f"[pending] {remaining} pending ({summary}); shells to rebuild: {rebuilds or 'none'}; "
          f"this batch: {[i['id'] for i in batch]} -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
