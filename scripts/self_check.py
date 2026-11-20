#!/usr/bin/env python3
"""Drive the pipeline's self check loop, so a human only reads the outcome.

April, 2026-11-19: the AI must check itself over and over without a human deciding; a
human should spend seconds on a review. So the entrypoint runs, per document:

    review (fresh session) -> this script: lint + record -> fix pass -> review again ...

until every document passes or SELF_CHECK_ROUNDS is spent. This script is the
deterministic part. It never judges prose; it runs the analytic linter, reads the
reviewer's verdict, keeps a per document record in ``state/guardrails/<ID>.json`` and
decides what goes back for fixing.

A record's ``status`` is the one word the console shows:

    verified        passed review and lint on the first round
    self-corrected  failed at least once, the AI fixed it, and it then passed
    fixing          failed this round and is queued for another attempt
    needs-human     still failing after the last round; ``open_issues`` says why

Commands
    record   --round N --max M   after a review round: lint each reviewed document,
                                 record the round, write state/_work/fix.json.
                                 Exit 0 when something needs fixing, 3 when nothing does.
    finalize                     mark anything still "fixing" as "needs-human" (its fix
                                 pass failed or never rebuilt it) and print a summary.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "core" / "tools"))

import analytic_lint  # noqa: E402

OUT = Path(os.environ.get("OUTPUT_DIR", "out")).resolve()

# The gates a guardrail record reports, in the order the console lists them. Each maps to a
# reviewer check in task-review.md, except "wording", which the linter decides in code.
GATES = ("sources", "cve_facts", "house_rules", "consistency", "reasoning", "wording")


def guardrails_dir() -> Path:
    return OUT / "state" / "guardrails"


def now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def read_json(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def lint_document(path: Path) -> list[dict[str, Any]]:
    """Linter findings for one document, as plain dicts for the record."""
    blocks = analytic_lint.read_blocks(path)
    return [
        {"level": f.level, "rule": f.rule, "message": f.message, "excerpt": f.excerpt}
        for f in analytic_lint.lint_text(blocks)
    ]


def gate_results(review: dict[str, Any] | None, lint: list[dict[str, Any]]) -> dict[str, str]:
    """pass / flag / unchecked per gate. A missing reviewer check is "unchecked", never pass."""
    checks = (review or {}).get("checks") or {}
    gates = {g: checks.get(g, "unchecked") for g in GATES if g != "wording"}
    gates = {g: v if v in ("pass", "flag") else "unchecked" for g, v in gates.items()}
    gates["wording"] = "flag" if any(f["level"] == "ERROR" for f in lint) else "pass"
    return gates


def open_issues(review: dict[str, Any] | None, lint: list[dict[str, Any]]) -> list[str]:
    """One line per thing still wrong, written for a human who has seconds."""
    issues = [
        f"{f.get('problem', '').strip()} ({f.get('claim', '').strip()[:80]})"
        for f in (review or {}).get("findings", [])
        if f.get("problem")
    ]
    issues += [f"Wording: {f['rule']}: {f['excerpt']}" for f in lint if f["level"] == "ERROR"]
    if review is None:
        issues.append("The reviewer wrote no review for this document.")
    return issues


def next_status(
    previous: list[dict[str, Any]], failed: bool, round_no: int, max_rounds: int
) -> str:
    if not failed:
        return "self-corrected" if any(r["failed"] for r in previous) else "verified"
    return "fixing" if round_no < max_rounds else "needs-human"


def record_item(item: dict[str, str], round_no: int, max_rounds: int) -> dict[str, Any]:
    """Lint one reviewed document, append this round to its record, return the record."""
    ident = item["id"]
    review = read_json(OUT / "state" / "reviews" / f"{ident}.json")
    doc = OUT / item["path"]
    lint = lint_document(doc) if doc.exists() else []
    gates = gate_results(review, lint)
    issues = open_issues(review, lint)
    # A gate the reviewer flagged fails the document even if its overall verdict says pass.
    failed = (
        bool(issues) or (review or {}).get("verdict") != "pass" or "flag" in gates.values()
    )

    path = guardrails_dir() / f"{ident}.json"
    record = read_json(path) or {"id": ident, "kind": item.get("kind", "")}
    if round_no == 1 or "rounds" not in record:
        # Round 1 is a new run: an old failure must not turn today's clean pass into
        # "self-corrected".
        record["rounds"] = []
    record["path"] = item["path"]
    record["rounds"].append({
        "round": round_no,
        "checked_at": now(),
        "failed": failed,
        "review_verdict": (review or {}).get("verdict", "missing"),
        "review_findings": len((review or {}).get("findings", [])),
        "lint_errors": sum(f["level"] == "ERROR" for f in lint),
        "lint_warnings": sum(f["level"] == "WARN" for f in lint),
    })
    record.update({
        "status": next_status(record["rounds"][:-1], failed, round_no, max_rounds),
        "gates": gates,
        "open_issues": issues,
        "summary": (review or {}).get("summary", ""),
        "lint": lint,
        "updated_at": now(),
    })
    write_json(path, record)
    return record


def cmd_record(review_list: Path, round_no: int, max_rounds: int, fix_out: Path) -> int:
    batch = (read_json(review_list) or {}).get("batch", [])
    to_fix = []
    for item in batch:
        record = record_item(item, round_no, max_rounds)
        print(f"[self-check] round {round_no}: {record['id']} {record['status']}")
        if record["status"] == "fixing":
            to_fix.append({**item, "round": round_no, "open_issues": record["open_issues"],
                           "lint": [f for f in record["lint"] if f["level"] == "ERROR"]})
    if not to_fix:
        fix_out.unlink(missing_ok=True)
        return 3
    write_json(fix_out, {"round": round_no, "batch": to_fix})
    print(f"[self-check] {len(to_fix)} sent back for fixing -> {fix_out}")
    return 0


def cmd_finalize() -> int:
    counts: dict[str, int] = {}
    for path in sorted(guardrails_dir().glob("*.json")):
        record = read_json(path)
        if record is None:
            continue
        if record.get("status") == "fixing":
            # The fix pass did not rebuild it, so no later round judged it. When it left a
            # note saying why (it refused to force a dishonest fix), that is the reason.
            note = OUT / "state" / "_work" / "fixes" / f"{record['id']}.md"
            reason = note.read_text(encoding="utf-8").strip() if note.exists() else ""
            record["status"] = "needs-human"
            record["fix_note"] = reason
            record["open_issues"] = record.get("open_issues", []) + [
                reason or "The automatic fix pass did not produce a new version."]
            record["updated_at"] = now()
            write_json(path, record)
        counts[record["status"]] = counts.get(record["status"], 0) + 1
    summary = ", ".join(f"{n} {s}" for s, n in sorted(counts.items())) or "no documents"
    print(f"[self-check] final: {summary}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    rec = sub.add_parser("record")
    rec.add_argument("--round", type=int, required=True)
    rec.add_argument("--max", type=int, required=True)
    rec.add_argument("--list", type=Path, default=OUT / "state" / "_work" / "review.json")
    rec.add_argument("--out", type=Path, default=OUT / "state" / "_work" / "fix.json")
    sub.add_parser("finalize")
    args = ap.parse_args()
    if args.cmd == "record":
        return cmd_record(args.list, args.round, args.max, args.out)
    return cmd_finalize()


if __name__ == "__main__":
    raise SystemExit(main())
