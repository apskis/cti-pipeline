"""The company brand: read for the console, and changed from the Branding tab.

The same company.json the document builders read (config/companies/<slug>/), so the
console and the reports cannot disagree. A save here changes the next report built.
core/tools/cti_brand.py checks the file again for the builders.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import struct
import threading
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, ValidationError

from .colours import Check, console_checks, dark_tokens, light_tokens, palette_checks

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

AssetKind = Literal["logo", "banner", "symbol"]
ASSET_KINDS: tuple[AssetKind, ...] = ("logo", "banner", "symbol")
MAX_IMAGE_BYTES = 2 * 1024 * 1024
MIN_SIDE, MAX_SIDE = 16, 4000
# Width over height each image may have. The builders size the banner and footer logo
# by width, so a very tall image would push the page body down or swamp the footer.
ASPECT_LIMITS: dict[AssetKind, tuple[float, float]] = {
    "logo": (1.5, 8.0),
    "banner": (4.0, 12.0),
    "symbol": (0.3, 3.0),
}

Hex = Annotated[str, StringConstraints(pattern=r"^[0-9A-Fa-f]{6}$")]
Text = Annotated[str, StringConstraints(min_length=1, max_length=200, strip_whitespace=True)]


class BrandError(Exception):
    """The brand file or an image is missing or wrong. `status` is the HTTP answer."""

    def __init__(self, message: str, status: int = 500) -> None:
        super().__init__(message)
        self.status = status


class Palette(BaseModel):
    """The seven document colours, six digit hex without #."""

    model_config = ConfigDict(extra="forbid")
    primary: Hex
    accent: Hex
    text: Hex
    muted: Hex
    rule: Hex
    tint: Hex
    zebra: Hex

    def upper(self) -> dict[str, str]:
        return {key: value.upper() for key, value in self.model_dump().items()}


class BrandIn(BaseModel):
    """What the Branding tab sends. The slug and images are not changed here."""

    model_config = ConfigDict(extra="forbid")
    name: Text
    legal_name: Text
    department: Text
    program: Text
    contact: Text
    palette: Palette


class _Assets(BaseModel):
    model_config = ConfigDict(extra="ignore")
    logo: str
    banner: str
    symbol: str


class _Console(BaseModel):
    model_config = ConfigDict(extra="forbid")
    light: dict[str, Hex] = Field(default_factory=dict)
    dark: dict[str, Hex] = Field(default_factory=dict)


class _CompanyFile(BaseModel):
    model_config = ConfigDict(extra="ignore")
    slug: Annotated[str, StringConstraints(pattern=SLUG_PATTERN)]
    name: Text
    legal_name: Text
    department: Text
    program: Text
    contact: Text
    palette: Palette
    assets: _Assets
    console: _Console = Field(default_factory=_Console)


class CheckOut(BaseModel):
    label: str
    foreground: str
    background: str
    ratio: float
    needed: float
    ok: bool


class Brand(BaseModel):
    """What /api/brand returns. Console colours as #rrggbb, ready for CSS."""

    slug: str
    name: str
    legal_name: str
    department: str
    program: str
    contact: str
    palette: dict[str, str]
    light: dict[str, str]
    dark: dict[str, str]
    # Changes whenever the file or an image changes, so the page can drop cached images.
    version: str


class Preview(BaseModel):
    light: dict[str, str]
    dark: dict[str, str]
    checks: list[CheckOut]
    ok: bool


def _tokens(raw: dict[str, str], theme: str) -> dict[str, str]:
    unknown = sorted(set(raw) - CONSOLE_TOKENS)
    if unknown:
        raise BrandError(f"console.{theme} has unknown tokens: {', '.join(unknown)}")
    return {name: f"#{value.lower()}" for name, value in sorted(raw.items())}


def _check_out(check: Check) -> CheckOut:
    return CheckOut(
        label=check.label,
        foreground=f"#{check.foreground.lower()}",
        background=f"#{check.background.lower()}",
        ratio=check.ratio,
        needed=check.needed,
        ok=check.ok,
    )


def png_size(data: bytes) -> tuple[int, int]:
    """Width and height from a PNG's header, or BrandError if it is not a PNG."""
    # The signature, then the IHDR chunk: length, type, width, height.
    if len(data) < 24 or not data.startswith(PNG_MAGIC) or data[12:16] != b"IHDR":
        raise BrandError("The image is not a PNG", 422)
    width, height = struct.unpack(">II", data[16:24])
    return width, height


class BrandStore:
    """One company's folder. One writer at a time; every write is whole and atomic."""

    def __init__(self, folder: Path) -> None:
        self.folder = folder.resolve()
        self.source = self.folder / "company.json"
        self._lock = threading.Lock()

    # ------------------------------------------------------------------ reading
    def _raw(self) -> dict[str, object]:
        try:
            raw = json.loads(self.source.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise BrandError(f"No brand file at {self.source}") from exc
        except json.JSONDecodeError as exc:
            raise BrandError(f"{self.source} is not a valid brand file: {exc}") from exc
        if not isinstance(raw, dict):
            raise BrandError(f"{self.source} is not a valid brand file: not an object")
        return raw

    def _parsed(self) -> _CompanyFile:
        try:
            return _CompanyFile.model_validate(self._raw())
        except ValidationError as exc:
            raise BrandError(f"{self.source} is not a valid brand file: {exc}") from exc

    def _asset_path(self, kind: AssetKind) -> Path:
        path = (self.folder / getattr(self._parsed().assets, kind)).resolve()
        if not path.is_relative_to(self.folder):
            raise BrandError(f"assets.{kind} must stay inside the company folder")
        return path

    def asset(self, kind: AssetKind) -> Path:
        """An image's path, which must be a PNG inside the company folder."""
        path = self._asset_path(kind)
        try:
            with path.open("rb") as image:
                head = image.read(24)
        except OSError as exc:
            raise BrandError(f"assets.{kind} {path} cannot be read") from exc
        if not head.startswith(PNG_MAGIC):
            raise BrandError(f"assets.{kind}: {path.name} is not a PNG")
        return path

    def _version(self) -> str:
        digest = hashlib.sha256(self.source.read_bytes())
        for kind in ASSET_KINDS:
            stat = self.asset(kind).stat()
            digest.update(f"{kind}:{stat.st_mtime_ns}:{stat.st_size}".encode())
        return digest.hexdigest()[:12]

    def load(self) -> Brand:
        raw = self._parsed()
        return Brand(
            slug=raw.slug,
            name=raw.name,
            legal_name=raw.legal_name,
            department=raw.department,
            program=raw.program,
            contact=raw.contact,
            palette=raw.palette.upper(),
            light=_tokens(raw.console.light, "light"),
            dark=_tokens(raw.console.dark, "dark"),
            version=self._version(),
        )

    # ------------------------------------------------------------------ changing
    @staticmethod
    def preview(item: BrandIn) -> Preview:
        """The console colours a palette gives, and every contrast check, without saving."""
        palette = item.palette.upper()
        light, dark = light_tokens(palette), dark_tokens(palette)
        checks = [*palette_checks(palette), *console_checks(light, dark)]
        return Preview(
            light={k: f"#{v.lower()}" for k, v in light.items()},
            dark={k: f"#{v.lower()}" for k, v in dark.items()},
            checks=[_check_out(c) for c in checks],
            ok=all(c.ok for c in checks),
        )

    def save(self, item: BrandIn) -> Brand:
        """Write the names, the palette and the console colours derived from it."""
        preview = self.preview(item)
        failed = [c for c in preview.checks if not c.ok]
        if failed:
            first = failed[0]
            raise BrandError(
                f"Not saved: {first.label} is {first.ratio}:1 and needs {first.needed}:1. "
                "Pick a darker or lighter colour.",
                422,
            )
        with self._lock:
            raw = self._raw()
            raw.update(item.model_dump(exclude={"palette"}))
            raw["palette"] = item.palette.upper()
            raw["console"] = {
                theme: {k: v.lstrip("#").upper() for k, v in tokens.items()}
                for theme, tokens in (("light", preview.light), ("dark", preview.dark))
            }
            self._replace(self.source, (json.dumps(raw, indent=2) + "\n").encode("utf-8"))
        return self.load()

    def save_asset(self, kind: AssetKind, data: bytes) -> Brand:
        """Replace one image, after checking it is a PNG of a sensible size and shape."""
        if len(data) > MAX_IMAGE_BYTES:
            raise BrandError(f"The image is over {MAX_IMAGE_BYTES // (1024 * 1024)} MB", 413)
        width, height = png_size(data)
        if not (MIN_SIDE <= width <= MAX_SIDE and MIN_SIDE <= height <= MAX_SIDE):
            raise BrandError(
                f"The image is {width} by {height} pixels; each side must be "
                f"{MIN_SIDE} to {MAX_SIDE}",
                422,
            )
        low, high = ASPECT_LIMITS[kind]
        aspect = width / height
        if not low <= aspect <= high:
            raise BrandError(
                f"The {kind} is {aspect:.1f} times as wide as it is tall; "
                f"it must be {low:g} to {high:g} times",
                422,
            )
        with self._lock:
            # The path only: a broken image on disk must still be replaceable.
            self._replace(self._asset_path(kind), data)
        return self.load()

    @staticmethod
    def _replace(path: Path, data: bytes) -> None:
        """Write beside the file, keep the old one as .bak, then swap in one step."""
        partial = path.with_name(path.name + ".part")
        partial.write_bytes(data)
        if path.exists():
            shutil.copy2(path, path.with_name(path.name + ".bak"))
        os.replace(partial, path)
