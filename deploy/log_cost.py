#!/usr/bin/env python3
"""Print one headless Claude session's reply and record what it cost.

``claude --print --output-format json`` returns the reply wrapped in a result object
that also carries the cost, turn count and token usage. The entrypoint used to print
plain text, so this keeps the reply in the job log exactly as before, then adds one
``[cost]`` line (searchable in CloudWatch / Log Analytics) and appends the same record
to a JSONL file that ships with the run's state, giving a cost history per component.

Context comes from the environment the entrypoint sets: COMPONENT, MODE, LABEL
(scan, build-1, ...) and RC (the claude exit code).
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def load_result(raw: str) -> dict[str, Any] | None:
    """Return the result object, or None when the CLI printed something else."""
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def cost_record(result: dict[str, Any]) -> dict[str, Any]:
    """The fields worth keeping from one session, plus where it ran."""
    usage = result.get("usage") or {}
    return {
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "component": os.environ.get("COMPONENT", ""),
        "mode": os.environ.get("MODE", ""),
        "label": os.environ.get("LABEL", ""),
        "exit_code": int(os.environ.get("RC", "0") or 0),
        "is_error": bool(result.get("is_error")),
        "cost_usd": result.get("total_cost_usd"),
        "turns": result.get("num_turns"),
        "duration_ms": result.get("duration_ms"),
        "input_tokens": usage.get("input_tokens"),
        "cache_read_tokens": usage.get("cache_read_input_tokens"),
        "cache_write_tokens": usage.get("cache_creation_input_tokens"),
        "output_tokens": usage.get("output_tokens"),
    }


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: log_cost.py <claude-json-output> <cost-log.jsonl>", file=sys.stderr)
        return 2
    raw = Path(sys.argv[1]).read_text(errors="replace")
    result = load_result(raw)
    if result is None:
        # Not JSON (an early CLI error, say): show it untouched so nothing is hidden.
        print(raw)
        print("[cost] unavailable: claude did not return a JSON result")
        return 0

    print(result.get("result") or "")
    record = cost_record(result)
    print("[cost] " + " ".join(f"{k}={v}" for k, v in record.items() if k != "ts"))

    log = Path(sys.argv[2])
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
