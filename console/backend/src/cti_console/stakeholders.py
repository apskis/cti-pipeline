"""The stakeholder list: who the intelligence is for and what each person receives.

This is the one thing the console writes. The real list holds names and email addresses,
so it lives in a gitignored file (``config/stakeholders.json``); a made up example list is
committed beside it for demos. Writes are atomic and keep the previous version as a
``.bak`` file, so a bad save can always be undone by hand.
"""

from __future__ import annotations

import json
import os
import re
import secrets
import shutil
import threading
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

SCHEMA_VERSION = 1
MAX_STAKEHOLDERS = 500
KIND = r"^[a-z][a-z_]{0,29}$"
# Loose on purpose: enough to catch typos, not a full RFC 5322 parser.
EMAIL = re.compile(r"^[^@\s<>\"']{1,64}@[A-Za-z0-9.-]{1,190}\.[A-Za-z]{2,24}$")
Channel = Literal["email", "teams", "slack", "other"]


def _tidy_list(values: list[str], limit: int) -> list[str]:
    """Trimmed, non-empty, de-duplicated (ignoring case), first spelling kept."""
    seen: set[str] = set()
    tidy: list[str] = []
    for value in values:
        text = " ".join(value.split())
        if text and text.lower() not in seen:
            if len(text) > limit:
                raise ValueError(f"'{text[:20]}...' is longer than {limit} characters")
            seen.add(text.lower())
            tidy.append(text)
    return tidy


class StakeholderIn(BaseModel):
    """What the edit form sends. Unknown fields are refused, not ignored."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=100)
    role: str = Field("", max_length=100)
    team: str = Field(min_length=1, max_length=80)
    also_known_as: list[str] = Field(default_factory=list, max_length=20)
    email: str = Field("", max_length=254)
    channel: Channel = "email"
    receives: list[str] = Field(default_factory=list, max_length=20)
    interests: list[str] = Field(default_factory=list, max_length=20)
    notes: str = Field("", max_length=1000)

    @field_validator("email")
    @classmethod
    def _email(cls, value: str) -> str:
        if value and not EMAIL.match(value):
            raise ValueError("does not look like an email address")
        return value

    @field_validator("also_known_as")
    @classmethod
    def _aliases(cls, value: list[str]) -> list[str]:
        return _tidy_list(value, 80)

    @field_validator("interests")
    @classmethod
    def _interests(cls, value: list[str]) -> list[str]:
        return _tidy_list(value, 40)

    @field_validator("receives")
    @classmethod
    def _receives(cls, value: list[str]) -> list[str]:
        kinds = _tidy_list(value, 30)
        bad = [k for k in kinds if not re.match(KIND, k)]
        if bad:
            raise ValueError(f"unknown report kind {bad[0]!r}")
        return kinds


class Stakeholder(StakeholderIn):
    id: str = Field(pattern=r"^sh-[a-f0-9]{8}$")


class StakeholderFile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: int = SCHEMA_VERSION
    stakeholders: list[Stakeholder] = Field(default_factory=list, max_length=MAX_STAKEHOLDERS)


class StoreError(Exception):
    def __init__(self, message: str, status: int) -> None:
        super().__init__(message)
        self.status = status


class StakeholderStore:
    """Reads and writes the list. One writer at a time; every write is whole and atomic."""

    def __init__(self, path: Path, example: Path) -> None:
        self.path = path
        self.example = example
        self._lock = threading.Lock()

    def exists(self) -> bool:
        return self.path.is_file()

    def load(self) -> list[Stakeholder]:
        if not self.path.is_file():
            return []
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            return StakeholderFile.model_validate(raw).stakeholders
        except (OSError, ValueError) as exc:
            # Never overwrite a file we could not read; it may be hand edited.
            raise StoreError(f"{self.path.name} could not be read: {exc}", 500) from exc

    def add(self, item: StakeholderIn) -> Stakeholder:
        with self._lock:
            people = self.load()
            if len(people) >= MAX_STAKEHOLDERS:
                raise StoreError(f"The list is full ({MAX_STAKEHOLDERS} stakeholders)", 409)
            taken = {p.id for p in people}
            ident = _new_id(taken)
            created = Stakeholder(id=ident, **item.model_dump())
            self._save([*people, created])
            return created

    def update(self, ident: str, item: StakeholderIn) -> Stakeholder:
        with self._lock:
            people = self.load()
            index = _index_of(people, ident)
            changed = Stakeholder(id=ident, **item.model_dump())
            people[index] = changed
            self._save(people)
            return changed

    def remove(self, ident: str) -> None:
        with self._lock:
            people = self.load()
            del people[_index_of(people, ident)]
            self._save(people)

    def start_from_example(self) -> list[Stakeholder]:
        """Copy the committed example list in, only when there is no list yet."""
        with self._lock:
            if self.path.exists():
                raise StoreError("A stakeholder list already exists", 409)
            try:
                raw = json.loads(self.example.read_text(encoding="utf-8"))
                people = StakeholderFile.model_validate(raw).stakeholders
            except (OSError, ValueError) as exc:
                raise StoreError(f"The example list could not be read: {exc}", 500) from exc
            self._save(people)
            return people

    def _save(self, people: list[Stakeholder]) -> None:
        body = StakeholderFile(stakeholders=people).model_dump(mode="json")
        text = json.dumps(body, indent=2, ensure_ascii=False) + "\n"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        partial = self.path.with_suffix(".json.part")
        partial.write_text(text, encoding="utf-8")
        if self.path.exists():
            # Copy, not move: the list is never missing, even for a moment.
            shutil.copy2(self.path, self.path.with_suffix(".json.bak"))
        os.replace(partial, self.path)


def _new_id(taken: set[str]) -> str:
    while True:
        ident = f"sh-{secrets.token_hex(4)}"
        if ident not in taken:
            return ident


def _index_of(people: list[Stakeholder], ident: str) -> int:
    for index, person in enumerate(people):
        if person.id == ident:
            return index
    raise StoreError(f"No stakeholder {ident}", 404)
