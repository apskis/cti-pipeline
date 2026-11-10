"""Read the CVE register workbook. Opened read only; never written."""

from __future__ import annotations

import logging
from pathlib import Path

from openpyxl import load_workbook

log = logging.getLogger(__name__)

SHEET = "CVE Register"
HEADER = "CVE / Advisory ID"


def latest_register(out_dir: Path) -> Path | None:
    found = sorted(
        out_dir.glob("*/registers/CVE_Register_*.xlsx"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return found[0] if found else None


def count_cves(path: Path) -> int | None:
    """Rows under the register's header row; None when the sheet or header is missing."""
    try:
        book = load_workbook(path, read_only=True, data_only=True)
    except (OSError, ValueError, KeyError) as exc:
        log.warning("cannot open %s: %s", path.name, exc)
        return None
    try:
        if SHEET not in book.sheetnames:
            return None
        rows = book[SHEET].iter_rows(min_col=1, max_col=1, values_only=True)
        for (value,) in rows:
            if str(value or "").strip() == HEADER:
                # the real workbook repeats its header row further down; it is not a CVE
                return sum(1 for (cell,) in rows if str(cell or "").strip() not in ("", HEADER))
        return None
    finally:
        book.close()
