"""What the pipeline knows about the company it runs for, beside its brand.

The brand (``company.json``, read by :mod:`cti_brand`) decides how documents look. The
profile (``profile.json`` in the same folder) decides what the scans watch and how the
prompts talk about the company: its industry, domains, own products, peers. Both come
from the one company folder, picked with ``CTI_COMPANY`` or ``CTI_COMPANY_DIR``.

An empty list is allowed and means "not set up yet": the prompts say so instead of
treating it as "nothing to watch".
"""

from __future__ import annotations

import json
from dataclasses import dataclass, fields
from functools import cache
from pathlib import Path

from cti_brand import COMPANIES_DIR, Brand, BrandError, company_dir, parse_brand

PROFILE_FILE = "profile.json"
REFERENCE_DIR = "reference"
TECH_PROFILE = "tech-profile.md"
PEER_WATCHLIST = "peer-watchlist.md"
MAX_TEXT = 2000
MAX_ITEMS = 200


class ProfileError(BrandError):
    """profile.json is missing or malformed."""


@dataclass(frozen=True)
class Profile:
    analyst: str
    industry: str
    domains: tuple[str, ...]
    security_contact: str
    osint_source_name: str
    products: str
    flagship_product: str
    own_products: tuple[str, ...]
    ics_products: tuple[str, ...]
    strategic_profile: tuple[str, ...]
    ir_feed_urls: tuple[str, ...]
    product_keywords: tuple[str, ...]
    peer_watch_orgs: tuple[str, ...]
    peer_competitor_orgs: tuple[str, ...]


@dataclass(frozen=True)
class Company:
    """One company as a run sees it: brand, profile and where its notes are."""

    brand: Brand
    profile: Profile
    folder: Path  # where profile.json and reference/ were found

    @property
    def tech_profile(self) -> Path:
        return self.folder / REFERENCE_DIR / TECH_PROFILE

    @property
    def peer_watchlist(self) -> Path:
        return self.folder / REFERENCE_DIR / PEER_WATCHLIST


def facts_dir(folder: Path, slug: str) -> Path:
    """Where a company's facts are: its own folder, or the committed copy for its slug.

    A console copy made before profiles existed holds only the brand, so the committed
    profile still applies to it, the same fallback the brand has.
    """
    if (folder / PROFILE_FILE).is_file():
        return folder
    committed = COMPANIES_DIR / slug
    return committed if (committed / PROFILE_FILE).is_file() else folder


def _text(raw: dict[str, object], key: str) -> str:
    value = raw.get(key, "")
    if not isinstance(value, str) or len(value) > MAX_TEXT:
        raise ProfileError(f"profile.json: {key!r} must be text of at most {MAX_TEXT} characters")
    return value.strip()


def _items(raw: dict[str, object], key: str) -> tuple[str, ...]:
    value = raw.get(key, [])
    ok = isinstance(value, list) and len(value) <= MAX_ITEMS
    if not ok or not all(isinstance(v, str) and 0 < len(v.strip()) <= MAX_TEXT for v in value):
        raise ProfileError(f"profile.json: {key!r} must be a list of up to {MAX_ITEMS} non empty texts")
    return tuple(v.strip() for v in value)


def parse_profile(folder: Path) -> Profile:
    """Read and check one company's profile.json."""
    source = folder / PROFILE_FILE
    try:
        raw = json.loads(source.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ProfileError(f"No profile at {source}. Copy config/companies/_starter/profile.json.") from exc
    except json.JSONDecodeError as exc:
        raise ProfileError(f"{source} is not valid JSON: {exc}") from exc
    if not isinstance(raw, dict):
        raise ProfileError(f"{source} must hold a JSON object")
    values: dict[str, object] = {}
    for field in fields(Profile):
        values[field.name] = _items(raw, field.name) if field.type.startswith("tuple") else _text(raw, field.name)
    return Profile(**values)  # type: ignore[arg-type]


@cache
def _cached(folder: Path) -> Company:
    brand = parse_brand(folder)
    facts = facts_dir(brand.folder, brand.slug)
    return Company(brand=brand, profile=parse_profile(facts), folder=facts)


def load_company() -> Company:
    """The company for this run. Read once per folder; a run is one company."""
    return _cached(company_dir())
