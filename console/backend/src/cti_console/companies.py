"""The companies the console can show, and which one it shows now.

Each company is a folder, data/companies/<slug>/, holding its brand (company.json and
assets/), its stakeholder list, and its own out/ and logs/. The console reads only the
active company's folders, so one company's reports and people never show under another.

The pipeline company (GeneLabs) is the exception until the pipeline runs per company:
its reports, logs and stakeholders stay at the repo root where the pipeline writes them.
Its brand still lives here, so a save from the Branding tab no longer changes the repo.

Committed folders under config/companies/ are only first copies: each is copied into
data/ once, and _starter/ is what a new, blank company begins from.
"""

from __future__ import annotations

import json
import os
import shutil
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints

from .config import COMPANY_SLUG, PIPELINE_COMPANY, Settings

STARTER = "_starter"
MAX_COMPANIES = 100
STATE_FILE = "console.json"
# What a new company copies from its source: the brand only, never people or reports.
BRAND_PARTS = ("company.json", "assets")

Slug = Annotated[str, StringConstraints(pattern=COMPANY_SLUG.pattern)]
Name = Annotated[str, StringConstraints(min_length=1, max_length=200, strip_whitespace=True)]


class CompanyError(Exception):
    """A company that cannot be found, made or picked. `status` is the HTTP answer."""

    def __init__(self, message: str, status: int = 400) -> None:
        super().__init__(message)
        self.status = status


class CompanyIn(BaseModel):
    """A new company. `source` is a company to copy the brand from; none means blank."""

    model_config = ConfigDict(extra="forbid")
    name: Name
    slug: Slug
    source: Slug | None = None


class Pick(BaseModel):
    model_config = ConfigDict(extra="forbid")
    slug: Slug


class CompanyOut(BaseModel):
    slug: str
    name: str
    program: str
    # True for the one company the pipeline writes reports for today.
    pipeline: bool


class CompanyList(BaseModel):
    active: str
    companies: list[CompanyOut]


@dataclass(frozen=True)
class Workspace:
    """Every folder one company's console reads and writes."""

    slug: str
    folder: Path  # company.json and assets/
    out_dir: Path
    logs_dir: Path
    stakeholders_file: Path
    stakeholders_example: Path


class Companies:
    """The company folders and the active choice. One change at a time."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.root = settings.data_dir / "companies"
        self.state = settings.data_dir / STATE_FILE
        self._lock = threading.Lock()
        self._seed()
        self._active = self._first_active()

    # ------------------------------------------------------------------ setup
    def _seed(self) -> None:
        """Copy each committed company in once. An existing folder is never touched."""
        self.root.mkdir(parents=True, exist_ok=True)
        templates = self.settings.templates_dir
        if not templates.is_dir():
            return
        for source in sorted(templates.iterdir()):
            target = self.root / source.name
            committed = COMPANY_SLUG.match(source.name) and (source / "company.json").is_file()
            if committed and not target.exists():
                self._copy_brand(source, target)

    def _first_active(self) -> str:
        """The company picked last time, else the one the console was started with."""
        try:
            saved = json.loads(self.state.read_text(encoding="utf-8")).get("active")
        except (OSError, ValueError, AttributeError):
            saved = None
        for slug in (saved, self.settings.company, PIPELINE_COMPANY):
            if isinstance(slug, str) and self._exists(slug):
                return slug
        found = self._slugs()
        if not found:
            raise CompanyError(f"No companies in {self.root}", 500)
        return found[0]

    # ------------------------------------------------------------------ reading
    def _exists(self, slug: str) -> bool:
        return bool(COMPANY_SLUG.match(slug)) and (self.root / slug / "company.json").is_file()

    def _slugs(self) -> list[str]:
        return sorted(p.name for p in self.root.iterdir() if self._exists(p.name))

    def _describe(self, slug: str) -> CompanyOut:
        """Name and program from the brand file; a broken file still lists, by slug."""
        try:
            raw = json.loads((self.root / slug / "company.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            raw = {}
        if not isinstance(raw, dict):
            raw = {}
        name, program = raw.get("name"), raw.get("program")
        return CompanyOut(
            slug=slug,
            name=name if isinstance(name, str) and name.strip() else slug,
            program=program if isinstance(program, str) else "",
            pipeline=slug == PIPELINE_COMPANY,
        )

    def listing(self) -> CompanyList:
        return CompanyList(
            active=self.active_slug(), companies=[self._describe(s) for s in self._slugs()]
        )

    def active_slug(self) -> str:
        with self._lock:
            return self._active

    def workspace(self, slug: str) -> Workspace:
        if not self._exists(slug):
            raise CompanyError(f"No company {slug}", 404)
        folder = (self.root / slug).resolve()
        if slug == PIPELINE_COMPANY:
            return Workspace(
                slug=slug,
                folder=folder,
                out_dir=self.settings.out_dir,
                logs_dir=self.settings.logs_dir,
                stakeholders_file=self.settings.stakeholders_file,
                stakeholders_example=self.settings.stakeholders_example,
            )
        return Workspace(
            slug=slug,
            folder=folder,
            out_dir=folder / "out",
            logs_dir=folder / "logs",
            stakeholders_file=folder / "stakeholders.json",
            # The committed example names GeneLabs teams, so no other company offers it.
            stakeholders_example=folder / "stakeholders.example.json",
        )

    # ------------------------------------------------------------------ changing
    def pick(self, slug: str) -> CompanyList:
        """Make `slug` the active company, and remember it for the next start."""
        if not self._exists(slug):
            raise CompanyError(f"No company {slug}", 404)
        with self._lock:
            self._active = slug
            self._write_state()
        return self.listing()

    def create(self, item: CompanyIn) -> CompanyList:
        """A new company folder: a copy of `source`'s brand, or the blank starter."""
        with self._lock:
            target = self.root / item.slug
            if target.exists():
                raise CompanyError(f"There is already a company called {item.slug}", 409)
            if len(self._slugs()) >= MAX_COMPANIES:
                raise CompanyError(f"The console holds at most {MAX_COMPANIES} companies", 409)
            if item.source is None:
                source = self.settings.templates_dir / STARTER
            elif self._exists(item.source):
                source = self.root / item.source
            else:
                raise CompanyError(f"No company {item.source} to copy", 404)
            # Built beside the real folder and renamed in one step, so a failure part way
            # never leaves a half company in the list.
            partial = self.root / f".{item.slug}.part"
            shutil.rmtree(partial, ignore_errors=True)
            try:
                self._copy_brand(source, partial)
                raw = json.loads((partial / "company.json").read_text(encoding="utf-8"))
                raw["slug"] = item.slug
                raw["name"] = item.name
                if item.source is None:
                    raw["legal_name"] = item.name
                (partial / "company.json").write_text(
                    json.dumps(raw, indent=2) + "\n", encoding="utf-8"
                )
                for empty in ("out", "logs"):
                    (partial / empty).mkdir()
                os.replace(partial, target)
            finally:
                shutil.rmtree(partial, ignore_errors=True)
        return self.listing()

    @staticmethod
    def _copy_brand(source: Path, target: Path) -> None:
        target.mkdir(parents=True)
        for part in BRAND_PARTS:
            path = source / part
            if path.is_dir():
                # Earlier versions of a picture (.bak) and writes in progress stay behind.
                skip = shutil.ignore_patterns("*.bak", "*.part")
                shutil.copytree(path, target / part, ignore=skip)
            elif path.is_file():
                shutil.copy2(path, target / part)

    def _write_state(self) -> None:
        partial = self.state.with_suffix(".part")
        partial.write_text(json.dumps({"active": self._active}) + "\n", encoding="utf-8")
        os.replace(partial, self.state)
