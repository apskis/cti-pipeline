#!/usr/bin/env python3
"""Write a Claude Code MCP config for one component.

Reads ``enabled_servers`` from ``components/<name>/component.yaml`` and emits a
``.mcp.json`` that launches the matching server over stdio. A name resolves to a
threatpipe script first, then to an entry in ``core/.mcp.json`` (third party servers
such as ``aws-api``, pinned there so local runs and the pipeline launch the same
version). Servers read their keys from the environment the task was started with,
so no credential is written here. Names with no server (``search`` in the POC) are
skipped with a note so the run output says which sources were unavailable.
"""
from __future__ import annotations

import argparse
import json
import os
import re
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


_ENV_REF = re.compile(r"\$\{(\w+)(?::-([^}]*))?\}")


def _expand(value: str) -> str:
    """Resolve ``${VAR}`` and ``${VAR:-default}`` the way Claude Code does for .mcp.json.

    Done here so the generated file is concrete and does not depend on how the CLI
    treats references in a ``--mcp-config`` file.
    """
    return _ENV_REF.sub(lambda m: os.environ.get(m.group(1)) or (m.group(2) or ""), value)


def load_external(core_mcp: Path) -> dict[str, dict]:
    """Return the third party server entries declared in ``core/.mcp.json``."""
    if not core_mcp.is_file():
        return {}
    return json.loads(core_mcp.read_text()).get("mcpServers", {})


def build_config(
    enabled: list[str], threatpipe: Path, external: dict[str, dict] | None = None
) -> tuple[dict, list[str]]:
    """Return (mcp config, skipped names) for the requested servers."""
    external = external or {}
    servers: dict[str, dict] = {}
    skipped: list[str] = []
    for name in enabled:
        script = SERVER_SCRIPTS.get(name)
        if script is not None and (threatpipe / script).is_file():
            # the script's own dir lands on sys.path, so its bare ``_shared`` import works
            servers[name] = {"command": sys.executable, "args": [str(threatpipe / script)]}
        elif name in external:
            entry = dict(external[name])
            entry["env"] = {k: _expand(v) for k, v in entry.get("env", {}).items()}
            servers[name] = entry
        else:
            skipped.append(name)
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
    core = args.repo / "core"
    config, skipped = build_config(
        enabled, core / "threatpipe", load_external(core / ".mcp.json")
    )

    args.out.write_text(json.dumps(config, indent=2) + "\n")
    print(f"[mcp] {args.component}: enabled={sorted(config['mcpServers'])} "
          f"skipped={skipped} -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
