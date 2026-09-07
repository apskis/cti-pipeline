#!/usr/bin/env python3
"""Deterministic report renderer for the CTI pipeline.

Claude Code (the agent) does the analysis that the Azure OpenAI layer used to
do and writes it as ``analysis_result.json``. This script is the deterministic
half: it loads that JSON and renders the branded GeneLabs .docx with the
vendored python-docx renderers. No model call happens here.

Usage:
    python render_report.py --mode weekly    --analysis out/analysis_result.json --out-dir out
    python render_report.py --mode quarterly --analysis out/analysis_result.json --out-dir out

Exit codes: 0 ok, 2 bad args / missing input, 3 render failure.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

# Vendored package root: this file's directory holds src/ (src.core, src.reports).
_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

# Importing the concrete modules registers the generators in REPORT_REGISTRY.
from src.reports import quarterly_report, weekly_report  # noqa: F401,E402
from src.reports.registry import get_report_generator, list_report_types  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="Render a CTI report from an analysis_result JSON.")
    ap.add_argument("--mode", default=os.environ.get("MODE", "weekly"),
                    help="report type to render (weekly|quarterly). Default: weekly or $MODE.")
    ap.add_argument("--analysis", required=True, help="path to analysis_result.json")
    ap.add_argument("--out-dir", default=os.environ.get("OUTPUT_DIR", "."),
                    help="directory to write the .docx into")
    ap.add_argument("--mock", action="store_true", help="tag the filename _MOCK")
    args = ap.parse_args()

    mode = args.mode.strip().lower()
    analysis_path = Path(args.analysis)
    out_dir = Path(args.out_dir)

    if not analysis_path.is_file():
        print(f"[render] analysis file not found: {analysis_path}", file=sys.stderr)
        return 2

    gen = get_report_generator(mode, use_mock_data=args.mock)
    if gen is None:
        print(f"[render] unknown mode '{mode}'. Available: {list_report_types()}", file=sys.stderr)
        return 2

    try:
        analysis_result = json.loads(analysis_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        print(f"[render] could not read analysis JSON: {e}", file=sys.stderr)
        return 2
    if not isinstance(analysis_result, dict):
        print("[render] analysis JSON must be a JSON object (dict).", file=sys.stderr)
        return 2

    try:
        doc = gen.generate(analysis_result)
    except Exception as e:  # noqa: BLE001 - surface any renderer failure with context
        print(f"[render] {mode} render failed: {type(e).__name__}: {e}", file=sys.stderr)
        return 3

    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / gen.get_filename()
    doc.save(str(out_path))
    print(f"[render] wrote {mode} report: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
