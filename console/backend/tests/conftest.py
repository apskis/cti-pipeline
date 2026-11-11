"""A small out/ and logs/ tree shaped like the real pipeline output."""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

import docx
import pytest
from openpyxl import Workbook

from cti_console.config import REPO_ROOT, Settings

DAY = "2026-11-10"


def _docx(path: Path, paragraphs: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    document = docx.Document()
    for text in paragraphs:
        document.add_paragraph(text)
    document.save(str(path))


def _session(
    ts: str,
    label: str,
    cost: float,
    minutes: float,
    component: str = "bulletin-scan",
    exit_code: int = 0,
) -> dict[str, object]:
    return {
        "ts": ts,
        "component": component,
        "mode": "weekly",
        "label": label,
        "exit_code": exit_code,
        "is_error": False,
        "cost_usd": cost,
        "duration_ms": int(minutes * 60_000),
        "turns": 10,
    }


def _write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")


def _cost_logs(out: Path) -> None:
    _write_jsonl(
        out / "bulletin-scan/state/cost-log.jsonl",
        [
            _session("2026-10-10T20:00:00+00:00", "scan", 7.5, 15),
            _session(f"{DAY}T20:00:00+00:00", "scan", 8.5, 19),
            _session(f"{DAY}T20:03:00+00:00", "build-1", 0.25, 2),
            _session(f"{DAY}T20:06:00+00:00", "build-2", 0.25, 2),
            # a manual rebuild hours later is its own run
            _session(f"{DAY}T23:00:00+00:00", "build-1", 0.2, 2),
        ],
    )
    _write_jsonl(
        out / "reporting/state/cost-log.jsonl",
        [_session(f"{DAY}T21:00:00+00:00", "scan", 4.0, 10, component="reporting")],
    )


def _documents(out: Path) -> None:
    body = [f"CTI26-01 paragraph {i} of a complete bulletin." for i in range(20)]
    _docx(out / "bulletin-scan/bulletins/2026/CTI26-01-Good_Bulletin.docx", body)
    broken = [f"CTI26-02 paragraph {i}." for i in range(20)] + ["D:", "o", "r"]
    _docx(out / "bulletin-scan/bulletins/2026/CTI26-02-Broken_Bulletin.docx", broken)
    hunt = [f"TH26-01 hunt paragraph {i}." for i in range(35)]
    _docx(out / "bulletin-scan/hunts/packages/TH26-01-Sample_Hunt.docx", hunt)
    _docx(out / "bulletin-scan/state/_work/CTI26-99-Scratch.docx", ["scratch"])
    # A CVE brief is one table: few paragraphs is normal, not broken.
    brief = out / "bulletin-scan/registers/CVE-VM-2026-10-10.docx"
    weekly = out / "reporting/CTI_Weekly_Report_2026_Week46.docx"
    _docx(brief, ["CVE-VM-2026-10-10", "Priority brief"])
    _docx(weekly, ["Weekly report"])
    # Not in any index, so their dates come from the file time; pin them off the run day.
    stamp = datetime(2026, 11, 9, 12, 0).timestamp()
    for path in (brief, weekly):
        os.utime(path, (stamp, stamp))


def _state_files(out: Path) -> None:
    state = out / "bulletin-scan/state"
    (state / "deliverables-index.md").write_text(
        "# Deliverables index\n\n| ID | Kind | File | First seen |\n|---|---|---|---|\n"
        "| CTI26-01 | bulletin | bulletins/2026/CTI26-01-Good_Bulletin.docx | 2026-10-10 |\n"
        f"| CTI26-02 | bulletin | bulletins/2026/CTI26-02-Broken_Bulletin.docx | {DAY} |\n"
        f"| TH26-01 | hunt | hunts/packages/TH26-01-Sample_Hunt.docx | {DAY} |\n",
        encoding="utf-8",
    )
    (state / "dedup-log.md").write_text(
        "2026-10-10 | old-item | Old | tier:VULN\n  bulletin:CTI26-01 | hunt:none\n"
        f"{DAY} | new-item | New | tier:VULN\n  bulletin:CTI26-02 | hunt:TH26-01\n"
        # an UPDATE repeats the ID the item already had; it is not a new assignment
        f"{DAY} | old-item | UPDATE: Old | tier:VULN\n  bulletin:CTI26-01 | hunt:none\n",
        encoding="utf-8",
    )
    reports = out / "bulletin-scan/reports"
    reports.mkdir(parents=True)
    (reports / f"scan-{DAY}.md").write_text(
        "- Scan mode: SEARCH MODE. Web searches run: 7\n", encoding="utf-8"
    )


def _register(out: Path) -> None:
    book = Workbook()
    sheet = book.active
    sheet.title = "CVE Register"
    sheet.append(["CVE Register 2026"])
    sheet.append(["CVE / Advisory ID", "Vendor"])
    sheet.append(["CVE-2026-0001", "Acme"])
    sheet.append(["CVE / Advisory ID", "Vendor"])  # the real register repeats its header
    sheet.append(["CVE-2026-0002", "Acme"])
    path = out / "bulletin-scan/registers/CVE_Register_2026.xlsx"
    path.parent.mkdir(parents=True, exist_ok=True)
    book.save(path)


@pytest.fixture()
def settings(tmp_path: Path) -> Settings:
    out, logs = tmp_path / "out", tmp_path / "logs"
    _cost_logs(out)
    _documents(out)
    _state_files(out)
    _register(out)
    logs.mkdir()
    (logs / f"bulletin-scan-{DAY}.log").write_text(
        f"[feeds] window 2026-10-09..{DAY}; 189 items from 9/10 feeds; "
        "failed: ['HHS HC3 Alerts (HTTP 404)'] -> /app/out/state/_work/feed-digest.md\n",
        encoding="utf-8",
    )
    return Settings(repo_root=REPO_ROOT, out_dir=out, logs_dir=logs)
