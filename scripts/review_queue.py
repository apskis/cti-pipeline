#!/usr/bin/env python3
"""List the documents the Reviewer should check this run.

The Writer builds documents; the Reviewer, a fresh session with no shared context, checks
each one against its sources and writes ``state/reviews/<ID>.json``. A document needs a
review when it has none, or when it changed after its review was written (a rebuild).

``--since`` limits the queue to documents saved after that time, which the entrypoint sets
to the start of the run so a normal run reviews only what it built. A document changed
after its review is queued whatever its date: someone fixed it, so the verdict is out of
date. Without ``--since`` every unreviewed document is eligible, which is how an older
backlog can be reviewed on demand.

Exit 0 and write the batch when something needs review; exit 3 when nothing does.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pending_deliverables import shell_reason  # noqa: E402

OUT = Path(os.environ.get("OUTPUT_DIR", "out")).resolve()
REVIEWS = OUT / "state" / "reviews"

# Written documents only. The CVE brief is a table rendered by code straight from the
# register, so there is no prose for a reviewer to check.
KINDS = {
    "bulletin": re.compile(r"CTI\d{2}-\d{2,}"),
    "hunt": re.compile(r"TH\d{2}-\d{2,}"),
    "awareness": re.compile(r"AWR-\d{4}-\d{2}-\d{2}"),
}


def identify(path: Path) -> tuple[str, str] | None:
    """(id, kind) from a filename, or None when it is not a reviewable document."""
    for kind, pattern in KINDS.items():
        if m := pattern.search(path.name):
            return m.group(0), kind
    return None


def review_path(ident: str) -> Path:
    return REVIEWS / f"{ident}.json"


def is_reviewed(ident: str, doc: Path) -> bool:
    """A review counts only if it is newer than the document it judged."""
    review = review_path(ident)
    return review.exists() and review.stat().st_mtime >= doc.stat().st_mtime


def candidates(since: float | None) -> list[dict[str, str]]:
    """Unreviewed, complete documents, newest copy of each ID, newest first."""
    files = sorted(
        (f for f in OUT.rglob("*.docx") if f.relative_to(OUT).parts[0] != "state"),
        key=lambda f: f.stat().st_mtime,
        reverse=True,
    )
    seen: set[str] = set()
    items: list[dict[str, str]] = []
    for doc in files:
        found = identify(doc)
        if found is None or found[0] in seen:
            continue
        ident, kind = found
        seen.add(ident)
        if is_reviewed(ident, doc):
            continue
        stale = review_path(ident).exists()  # reviewed once, changed since
        if since is not None and doc.stat().st_mtime < since and not stale:
            continue
        # A shell is the Writer's problem, already queued for a rebuild; reviewing it
        # would spend a model call to say what the code check already knows.
        if shell_reason(doc, ident, kind):
            continue
        items.append({"id": ident, "kind": kind, "path": doc.relative_to(OUT).as_posix()})
    return items


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--batch", type=int, default=6, help="max documents per review session")
    ap.add_argument("--since", type=float, default=None, help="only documents saved after this epoch time")
    ap.add_argument("--out", type=Path, default=OUT / "state" / "_work" / "review.json")
    args = ap.parse_args()

    items = candidates(args.since)
    if not items:
        print("[review] nothing to review: every document built this run already has a review")
        return 3
    batch = items[: args.batch]
    REVIEWS.mkdir(parents=True, exist_ok=True)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps({"remaining": len(items), "reviews_dir": "state/reviews", "batch": batch}, indent=2)
    )
    print(f"[review] {len(items)} to review; this batch: {[i['id'] for i in batch]} -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
