#!/usr/bin/env python3
"""Resolve every key in config/paths.json and make sure it can be written to.

Prints ``key = absolute path`` for each entry and exits non zero if any folder
cannot be created, so a bad layout fails at the start of a run rather than when
a finished document is saved. Values may reference ``${OUTPUT_DIR}`` and
``${REPO_ROOT}``; anything else in ``${...}`` is read from the environment.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG = REPO_ROOT / "config" / "paths.json"
# keys that name a file: create the parent and, for the logs, an empty header
FILE_KEYS = {"gap_register", "cve_register", "peer_register",
             "awareness_ledger", "awareness_pipeline", "dedup_log"}
SEED_MARKDOWN = {"dedup_log", "awareness_ledger", "awareness_pipeline", "gap_register"}


def expand(value: str) -> Path:
    """Substitute ``${VAR}`` tokens from the environment, with repo defaults."""
    env = dict(os.environ)
    env.setdefault("OUTPUT_DIR", str(REPO_ROOT / "out"))
    env.setdefault("REPO_ROOT", str(REPO_ROOT))
    for key, val in env.items():
        value = value.replace("${" + key + "}", val)
    return Path(value).resolve()


def main() -> int:
    paths = json.loads(CONFIG.read_text())
    failures = 0
    for key, raw in paths.items():
        if key.startswith("_"):
            continue
        target = expand(raw)
        try:
            if key in FILE_KEYS:
                target.parent.mkdir(parents=True, exist_ok=True)
                if key in SEED_MARKDOWN and not target.exists():
                    target.write_text(f"# {key.replace('_', ' ')}\n\n")
            else:
                target.mkdir(parents=True, exist_ok=True)
            status = "ok"
        except OSError as exc:
            status = f"FAIL {exc}"
            failures += 1
        print(f"{key:22s} = {target}  [{status}]")
    if failures:
        print(f"{failures} path(s) could not be created", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
