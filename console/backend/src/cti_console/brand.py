"""The company brand the console shows: its name, colours and symbol.

The same company.json the document builders read (config/companies/<slug>/), so the
console and the reports cannot disagree. Only the parts the console uses are checked
here; core/tools/cti_brand.py checks the rest for the builders.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, ValidationError

SLUG_PATTERN = r"^[a-z0-9][a-z0-9-]{0,39}$"
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
# The colour tokens a brand may set. Status colours (ok, warn, fail) carry meaning,
# not brand, so they stay in index.css for every company.
CONSOLE_TOKENS = frozenset(
    {
        "page", "surface", "raised", "line", "ink", "muted", "faint", "brand", "accent",
        "accent-hover", "on-accent", "accent-soft", "accent-soft-ink", "rung", "symbol-tile",
        "series-scan", "series-build", "series-report", "series-other",
    }
)  # fmt: skip

Hex = Annotated[str, StringConstraints(pattern=r"^[0-9A-Fa-f]{6}$")]
Text = Annotated[str, StringConstraints(min_length=1, max_length=200, strip_whitespace=True)]


class BrandError(Exception):
    """The company's brand file is missing or wrong. The console cannot draw without it."""


class _Assets(BaseModel):
    model_config = ConfigDict(extra="ignore")
    symbol: str


class _Console(BaseModel):
    model_config = ConfigDict(extra="forbid")
    light: dict[str, Hex] = Field(default_factory=dict)
    dark: dict[str, Hex] = Field(default_factory=dict)


class _CompanyFile(BaseModel):
    # The builders' fields (palette, contact, ...) are theirs to check.
    model_config = ConfigDict(extra="ignore")
    slug: Annotated[str, StringConstraints(pattern=SLUG_PATTERN)]
    name: Text
    legal_name: Text
    program: Text
    assets: _Assets
    console: _Console = Field(default_factory=_Console)


class Brand(BaseModel):
    """What /api/brand returns. Colours as #rrggbb, ready for CSS."""

    slug: str
    name: str
    legal_name: str
    program: str
    light: dict[str, str]
    dark: dict[str, str]


def _tokens(raw: dict[str, str], theme: str) -> dict[str, str]:
    unknown = sorted(set(raw) - CONSOLE_TOKENS)
    if unknown:
        raise BrandError(f"console.{theme} has unknown tokens: {', '.join(unknown)}")
    return {name: f"#{value.lower()}" for name, value in sorted(raw.items())}


def _symbol(folder: Path, relative: str) -> Path:
    """The symbol image, which must be a PNG inside the company folder."""
    path = (folder / relative).resolve()
    if not path.is_relative_to(folder):
        raise BrandError("assets.symbol must stay inside the company folder")
    try:
        with path.open("rb") as image:
            if image.read(len(PNG_MAGIC)) != PNG_MAGIC:
                raise BrandError(f"{path.name} is not a PNG")
    except OSError as exc:
        raise BrandError(f"assets.symbol {path} cannot be read") from exc
    return path


def load_brand(folder: Path) -> tuple[Brand, Path]:
    """The company's brand and the path of its symbol image."""
    folder = folder.resolve()
    source = folder / "company.json"
    try:
        raw = _CompanyFile.model_validate(json.loads(source.read_text(encoding="utf-8")))
    except FileNotFoundError as exc:
        raise BrandError(f"No brand file at {source}") from exc
    except (json.JSONDecodeError, ValidationError) as exc:
        raise BrandError(f"{source} is not a valid brand file: {exc}") from exc
    brand = Brand(
        slug=raw.slug,
        name=raw.name,
        legal_name=raw.legal_name,
        program=raw.program,
        light=_tokens(raw.console.light, "light"),
        dark=_tokens(raw.console.dark, "dark"),
    )
    return brand, _symbol(folder, raw.assets.symbol)
