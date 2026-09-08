#!/usr/bin/env python3
"""Write a Claude Code MCP config for one component.

Reads ``enabled_servers`` from ``components/<name>/component.yaml`` and emits a
``.mcp.json`` that launches the matching threatpipe server over stdio. Servers
read their API keys from the environment the task was started with, so no
credential is written here. Names with no local server (``search`` in the POC)
are skipped with a note so the run output says which sources were unavailable.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

# component.yaml server name -> threatpipe entry script
SERVER_SCRIPTS: dict[str, str] = {
    "nvd": "nvd_server.py",
    "enrich": "enrich_server.py",
    "ics": "ics_server.py",
    "shodan": "shodan_server.py",
    "intel471": "intel471_server.py",
    "claroty": "claroty_server.py",
    "rapid7": "rapid7_server.py",
    "threatq": "threatq_server.py",
    "falcon": "falcon_launcher.py",
    "splunk": "splunk_launcher.py",
}


def build_config(enabled: list[str], threatpipe: Path) -> tuple[dict, list[str]]:
    """Return (mcp config, skipped names) for the requested servers."""
    servers: dict[str, dict] = {}
    skipped: list[str] = []
    for name in enabled:
        script = SERVER_SCRIPTS.get(name)
        if script is None or not (threatpipe / script).is_file():
            skipped.append(name)
            continue
        # the script's own dir lands on sys.path, so its bare ``_shared`` import works
        servers[name] = {"command": sys.executable, "args": [str(threatpipe / script)]}
    return {"mcpServers": servers}, skipped


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--component", required=True)
    ap.add_argument("--repo", default=Path.cwd(), type=Path)
    ap.add_argument("--out", default=Path.cwd() / ".mcp.json", type=Path)
    args = ap.parse_args()

    manifest = args.repo / "components" / args.component / "component.yaml"
    data = yaml.safe_load(manifest.read_text()) or {}
    enabled = list(data.get("enabled_servers") or [])
    config, skipped = build_config(enabled, args.repo / "core" / "threatpipe")

    args.out.write_text(json.dumps(config, indent=2) + "\n")
    print(f"[mcp] {args.component}: enabled={sorted(config['mcpServers'])} "
          f"skipped={skipped} -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
