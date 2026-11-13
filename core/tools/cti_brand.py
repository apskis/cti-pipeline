"""The company brand every CTI document is built in.

Each company has one folder, config/companies/<slug>/, holding company.json and its
logo, banner and symbol. The document builders read the brand here instead of each
carrying its own palette, so changing how a company's documents look is one edit.

Standard library only: every builder imports this, including the ones copied out of
the repo and run on their own.

Which company:
    CTI_COMPANY_DIR   full path to a company folder (wins when set)
    CTI_COMPANY       slug under config/companies (default "genelabs")
"""

from __future__ import annotations

import json
import os
import re
import struct
from dataclasses import dataclass
from functools import cache
from pathlib import Path

DEFAULT_COMPANY = "genelabs"
COMPANY_ENV = "CTI_COMPANY"
COMPANY_DIR_ENV = "CTI_COMPANY_DIR"
# core/tools/cti_brand.py -> the repo root is two folders up from this file's folder.
REPO_ROOT = Path(__file__).resolve().parents[2]
COMPANIES_DIR = REPO_ROOT / "config" / "companies"

# A slug becomes a folder name, so it is held to a shape that cannot climb out.
SLUG_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]{0,39}$")
HEX_PATTERN = re.compile(r"^[0-9A-Fa-f]{6}$")
PALETTE_KEYS = ("primary", "accent", "text", "muted", "rule", "tint", "zebra")
ASSET_KEYS = ("logo", "banner", "symbol")
TEXT_KEYS = ("slug", "name", "legal_name", "department", "program", "contact")
MAX_TEXT = 200


class BrandError(ValueError):
    """company.json is missing, malformed, or points at files that are not there."""


@dataclass(frozen=True)
class Palette:
    """Document colours as six digit upper case hex, no #, as python-docx wants them."""

    primary: str  # headings, table header fill
    accent: str  # rules, bullets, links
    text: str  # body and headline text
    muted: str  # meta text and footer
    rule: str  # light rules and table borders
    tint: str  # label cells and callout fill
    zebra: str  # alternate table rows


@dataclass(frozen=True)
class Brand:
    slug: str
    name: str
    legal_name: str
    department: str
    program: str
    contact: str
    palette: Palette
    logo: Path
    banner: Path
    symbol: Path
    folder: Path

    @property
    def doc_comments(self) -> str:
        """The core properties comment every builder stamps on its .docx."""
        return f"{self.name} {self.department} | {self.program}"

    @property
    def banner_aspect(self) -> float:
        """Height over width of the banner, so the page body clears whatever is uploaded."""
        width, height = png_size(self.banner)
        return height / width


def png_size(path: Path) -> tuple[int, int]:
    """Width and height from a PNG's header."""
    head = path.read_bytes()[:24]
    if not head.startswith(b"\x89PNG\r\n\x1a\n") or head[12:16] != b"IHDR":
        raise BrandError(f"{path} is not a PNG")
    return struct.unpack(">II", head[16:24])


def company_dir() -> Path:
    """The folder of the company to build for, from the environment."""
    explicit = os.environ.get(COMPANY_DIR_ENV)
    if explicit:
        return Path(explicit).resolve()
    slug = os.environ.get(COMPANY_ENV, DEFAULT_COMPANY)
    if not SLUG_PATTERN.match(slug):
        raise BrandError(
            f"{COMPANY_ENV}={slug!r} is not a company slug (a to z, 0 to 9, -)"
        )
    return COMPANIES_DIR / slug


def _text(raw: dict[str, object], key: str) -> str:
    value = raw.get(key)
    if not isinstance(value, str) or not value.strip() or len(value) > MAX_TEXT:
        raise BrandError(
            f"company.json: {key!r} must be text of 1 to {MAX_TEXT} characters"
        )
    return value


def _palette(raw: object) -> Palette:
    if not isinstance(raw, dict):
        raise BrandError("company.json: 'palette' must be an object")
    colours: dict[str, str] = {}
    for key in PALETTE_KEYS:
        value = raw.get(key)
        if not isinstance(value, str) or not HEX_PATTERN.match(value):
            raise BrandError(
                f"company.json: palette.{key} must be six digit hex, such as 167D61"
            )
        colours[key] = value.upper()
    return Palette(**colours)


def _asset(folder: Path, assets: dict[str, object], key: str) -> Path:
    """An asset path inside the company folder. Anything pointing outside it is refused."""
    value = assets.get(key)
    if not isinstance(value, str):
        raise BrandError(f"company.json: assets.{key} must be a path")
    path = (folder / value).resolve()
    if not path.is_relative_to(folder):
        raise BrandError(f"company.json: assets.{key} must stay inside {folder}")
    if not path.is_file():
        raise BrandError(
            f"company.json: assets.{key} names {path}, which does not exist"
        )
    return path


def parse_brand(folder: Path) -> Brand:
    """Read and check one company folder."""
    folder = folder.resolve()
    source = folder / "company.json"
    try:
        raw = json.loads(source.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise BrandError(
            f"No brand file at {source}. Set {COMPANY_ENV} or {COMPANY_DIR_ENV}."
        ) from exc
    except json.JSONDecodeError as exc:
        raise BrandError(f"{source} is not valid JSON: {exc}") from exc
    if not isinstance(raw, dict):
        raise BrandError(f"{source} must hold a JSON object")
    assets = raw.get("assets")
    if not isinstance(assets, dict):
        raise BrandError("company.json: 'assets' must be an object")
    text = {key: _text(raw, key) for key in TEXT_KEYS}
    if not SLUG_PATTERN.match(text["slug"]):
        raise BrandError("company.json: 'slug' must be a to z, 0 to 9 and -")
    return Brand(
        **text,
        palette=_palette(raw.get("palette")),
        **{key: _asset(folder, assets, key) for key in ASSET_KEYS},
        folder=folder,
    )


@cache
def _cached(folder: Path) -> Brand:
    return parse_brand(folder)


def load_brand() -> Brand:
    """The brand for this run. Read once per folder; a builder run is one company."""
    return _cached(company_dir())
