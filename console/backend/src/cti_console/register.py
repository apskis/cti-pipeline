"""Read the CVE register workbook. Opened read only; never written."""

from __future__ import annotations

import logging
import re
from collections.abc import Iterator
from dataclasses import asdict, dataclass
from pathlib import Path

from openpyxl import load_workbook

log = logging.getLogger(__name__)

SHEET = "CVE Register"
HEADER = "CVE / Advisory ID"

# Register header -> API field. The SPL and CQL columns are left out: they are long
# queries for the analyst's own tools, not something the console shows.
COLUMNS = {
    "CVE / Advisory ID": "id",
    "Vendor": "vendor",
    "Product": "product",
    "Vulnerability Type": "vuln_type",
    "CVSS": "cvss",
    "KEV Added": "kev_added",
    "KEV Due": "kev_due",
    "Exploitation Status": "exploitation",
    "GeneLabs Relevance": "relevance",
    "Hunt ID": "hunt_id",
    "Bulletin ID": "bulletin_id",
    "Date Added": "date_added",
    "Remediation Status": "remediation",
    "Observed In Our Logs": "observed",
}
# Exploitation Status is free text ("ITW (CISA KEV)", "Active ITW", "No known ITW").
EXPLOITED = re.compile(r"\bITW\b|exploit|ransomware", re.IGNORECASE)
NOT_EXPLOITED = re.compile(r"^\s*(?:no|none)\b", re.IGNORECASE)
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}")
PIPELINE_ID = re.compile(r"\b(?:CTI|TH)\d{2}-\d{1,4}\b")
SCORE = re.compile(r"^\s*(\d{1,2}(?:\.\d)?)")


@dataclass(frozen=True)
class Cve:
    id: str
    vendor: str
    product: str
    vuln_type: str
    cvss: str
    cvss_score: float | None
    kev_added: str | None
    kev_due: str | None
    exploitation: str
    exploited: bool
    relevance: str
    hunt_id: str | None
    bulletin_id: str | None
    date_added: str | None
    remediation: str
    observed: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def latest_register(out_dir: Path) -> Path | None:
    found = sorted(
        out_dir.glob("*/registers/CVE_Register_*.xlsx"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return found[0] if found else None


def _text(value: object) -> str:
    return "" if value is None else str(value).strip()


def _date(value: str) -> str | None:
    m = DATE.match(value)
    return m[0] if m else None


def _ref(value: str) -> str | None:
    """The first bulletin or hunt ID in the cell, or None.

    Most cells hold one ID or "n/a". A few older rows are shifted a column and hold
    other text here, so anything that is not an ID is dropped rather than linked.
    """
    m = PIPELINE_ID.search(value)
    return m[0] if m else None


def _score(cvss: str) -> float | None:
    m = SCORE.match(cvss)
    return float(m[1]) if m and float(m[1]) <= 10 else None


def _cve(row: dict[str, str]) -> Cve:
    status = row.get("exploitation", "")
    cvss = row.get("cvss", "")
    return Cve(
        id=row["id"],
        vendor=row.get("vendor", ""),
        product=row.get("product", ""),
        vuln_type=row.get("vuln_type", ""),
        cvss=cvss,
        cvss_score=_score(cvss),
        kev_added=_date(row.get("kev_added", "")),
        kev_due=_date(row.get("kev_due", "")),
        exploitation=status,
        exploited=bool(EXPLOITED.search(status)) and not NOT_EXPLOITED.match(status),
        relevance=row.get("relevance", ""),
        hunt_id=_ref(row.get("hunt_id", "")),
        bulletin_id=_ref(row.get("bulletin_id", "")),
        date_added=_date(row.get("date_added", "")),
        remediation=row.get("remediation", ""),
        observed=row.get("observed", ""),
    )


def _rows(path: Path) -> Iterator[tuple[object, ...]] | None:
    try:
        book = load_workbook(path, read_only=True, data_only=True)
    except (OSError, ValueError, KeyError) as exc:
        log.warning("cannot open %s: %s", path.name, exc)
        return None
    if SHEET not in book.sheetnames:
        book.close()
        return None
    rows = list(book[SHEET].iter_rows(values_only=True))
    book.close()
    return iter(rows)


def _read(path: Path) -> list[Cve] | None:
    """Every CVE row under the header; None when the sheet or header is missing."""
    rows = _rows(path)
    if rows is None:
        return None
    for row in rows:
        if _text(row[0] if row else None) == HEADER:
            fields = [COLUMNS.get(_text(cell)) for cell in row]
            break
    else:
        return None
    found: list[Cve] = []
    for row in rows:
        first = _text(row[0] if row else None)
        # the real workbook repeats its header row further down; it is not a CVE
        if first in ("", HEADER):
            continue
        values = {f: _text(v) for f, v in zip(fields, row, strict=False) if f}
        found.append(_cve(values))
    return found


# Reading the workbook takes about a second; keep it per file and modification time.
_CACHE: dict[tuple[str, int], list[Cve] | None] = {}


def read_register(path: Path) -> list[Cve] | None:
    key = (str(path), path.stat().st_mtime_ns)
    if key not in _CACHE:
        _CACHE[key] = _read(path)
    return _CACHE[key]


def count_cves(path: Path) -> int | None:
    cves = read_register(path)
    return None if cves is None else len(cves)
