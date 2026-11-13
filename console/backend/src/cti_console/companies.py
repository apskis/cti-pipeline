"""The companies the console can show, and which one it shows now.

Each company is a folder, data/companies/<slug>/, holding its brand (company.json and
assets/), its facts for the pipeline (profile.json and reference/), its stakeholder list,
and its own out/ and logs/. The console reads only the active company's folders, so one
company's reports and people never show under another.

GeneLabs is the exception: its reports, logs and stakeholders stay at the repo root, where
the pipeline and scheduled runs wrote them before companies existed. Its brand and facts
still live here, so a save in the console no longer changes the repo.

Committed folders under config/companies/ are only first copies: each is copied into
data/ once, and _starter/ is what a new, blank company begins from.

Which company is shown is remembered per person: the local single user has one choice,
and with sign in on each signed in person has their own, so one person switching never
changes what another sees.
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

from .auth import Principal
from .config import COMPANY_SLUG, PIPELINE_COMPANY, Settings

STARTER = "_starter"
MAX_COMPANIES = 100
STATE_FILE = "console.json"
# What a new company copies from its source: the brand only, never people or reports.
BRAND_PARTS = ("company.json", "assets")
# What the pipeline knows about a company. A new company always starts these from the
# blank starter: a copied brand does not make another company's products or peers its own.
FACT_PARTS = ("profile.json", "reference")

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
    # Whether its out/ holds anything yet, so the page can say how to start a first run.
    has_runs: bool


class CompanyList(BaseModel):
    # Empty when the person may see no company at all.
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
        self._users = self._saved_users()

    # ------------------------------------------------------------------ setup
    def _seed(self) -> None:
        """Copy each committed company in once. Nothing already in data/ is overwritten.

        A copy made before companies had facts gets the committed profile.json and
        reference/ added beside its brand, so it can run without being made again.
        """
        self.root.mkdir(parents=True, exist_ok=True)
        templates = self.settings.templates_dir
        if not templates.is_dir():
            return
        for source in sorted(templates.iterdir()):
            target = self.root / source.name
            committed = COMPANY_SLUG.match(source.name) and (source / "company.json").is_file()
            if not committed:
                continue
            if not target.exists():
                self._copy_parts(source, target, BRAND_PARTS)
            self._copy_parts(source, target, FACT_PARTS)

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

    def _saved_users(self) -> dict[str, str]:
        """Each signed in person's last choice, by their provider subject."""
        try:
            saved = json.loads(self.state.read_text(encoding="utf-8")).get("users")
        except (OSError, ValueError, AttributeError):
            return {}
        if not isinstance(saved, dict):
            return {}
        return {k: v for k, v in saved.items() if isinstance(k, str) and isinstance(v, str)}

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
        out_dir = self.workspace(slug).out_dir
        return CompanyOut(
            slug=slug,
            name=name if isinstance(name, str) and name.strip() else slug,
            program=program if isinstance(program, str) else "",
            has_runs=out_dir.is_dir() and any(out_dir.iterdir()),
        )

    def listing(self, who: Principal) -> CompanyList:
        """The companies `who` may read, and the one shown to them."""
        visible = [s for s in self._slugs() if who.can_read(s)]
        return CompanyList(
            active=self.active_slug(who) or "",
            companies=[self._describe(s) for s in visible],
        )

    def active_slug(self, who: Principal) -> str | None:
        """The company shown to `who`: their last choice while they may still read it,
        else the console's own choice, else the first they may read, else none."""
        with self._lock:
            mine = self._active if who.subject is None else self._users.get(who.subject)
            fallback = self._active
        # A chosen company whose folder has gone stays chosen, so the page says what is
        # missing instead of quietly showing another company under the same header.
        if mine and who.can_read(mine):
            return mine
        if fallback and self._exists(fallback) and who.can_read(fallback):
            return fallback
        return next((s for s in self._slugs() if who.can_read(s)), None)

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
    def pick(self, slug: str, who: Principal) -> CompanyList:
        """Show `slug` to `who`, and remember it for their next visit."""
        # The same answer for a company that is missing and one they may not see, so the
        # reply does not tell them which other companies exist.
        if not self._exists(slug) or not who.can_read(slug):
            raise CompanyError(f"No company {slug}", 404)
        with self._lock:
            if who.subject is None:
                self._active = slug
            else:
                self._users[who.subject] = slug
            self._write_state()
        return self.listing(who)

    def create(self, item: CompanyIn, who: Principal) -> CompanyList:
        """A new company folder: a copy of `source`'s brand, or the blank starter.

        Its facts (profile.json, reference/) always come from the starter.
        """
        with self._lock:
            target = self.root / item.slug
            if target.exists():
                raise CompanyError(f"There is already a company called {item.slug}", 409)
            if len(self._slugs()) >= MAX_COMPANIES:
                raise CompanyError(f"The console holds at most {MAX_COMPANIES} companies", 409)
            if item.source is None:
                source = self.settings.templates_dir / STARTER
            elif self._exists(item.source) and who.can_read(item.source):
                source = self.root / item.source
            else:
                raise CompanyError(f"No company {item.source} to copy", 404)
            # Built beside the real folder and renamed in one step, so a failure part way
            # never leaves a half company in the list.
            partial = self.root / f".{item.slug}.part"
            shutil.rmtree(partial, ignore_errors=True)
            try:
                self._copy_parts(source, partial, BRAND_PARTS)
                self._copy_parts(self.settings.templates_dir / STARTER, partial, FACT_PARTS)
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
        return self.listing(who)

    @staticmethod
    def _copy_parts(source: Path, target: Path, parts: tuple[str, ...]) -> None:
        """Copy the named files and folders that `target` does not have yet."""
        target.mkdir(parents=True, exist_ok=True)
        for part in parts:
            path, dest = source / part, target / part
            if dest.exists():
                continue
            if path.is_dir():
                # Earlier versions of a picture (.bak) and writes in progress stay behind.
                skip = shutil.ignore_patterns("*.bak", "*.part")
                shutil.copytree(path, dest, ignore=skip)
            elif path.is_file():
                shutil.copy2(path, dest)

    def _write_state(self) -> None:
        partial = self.state.with_suffix(".part")
        state = {"active": self._active, "users": self._users}
        partial.write_text(json.dumps(state) + "\n", encoding="utf-8")
        os.replace(partial, self.state)
