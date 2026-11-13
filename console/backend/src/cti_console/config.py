"""Where the console reads from. Everything is read only."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

# src/cti_console/config.py -> repo root is four levels up from this file's folder.
REPO_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_COMPANY = "genelabs"
# A slug becomes a folder name, so it is held to a shape that cannot climb out.
COMPANY_SLUG = re.compile(r"^[a-z0-9][a-z0-9-]{0,39}$")


@dataclass(frozen=True)
class Settings:
    """Folders the console reads. Overridable by env so tests can point at a sample tree."""

    repo_root: Path
    out_dir: Path
    logs_dir: Path
    # The console's own scratch space: branded PDFs made from out/'s reports. Not out/,
    # which belongs to the pipeline.
    cache_dir: Path
    # Who the intelligence is for. The one file the console writes; gitignored, because
    # it holds names and email addresses.
    stakeholders_file: Path
    # The company whose brand the console shows: config/companies/<slug>/.
    company_dir: Path = REPO_ROOT / "config" / "companies" / DEFAULT_COMPANY

    @property
    def scripts_dir(self) -> Path:
        return self.repo_root / "scripts"

    @property
    def stakeholders_example(self) -> Path:
        """Made up GeneLabs teams, committed, for a first start and for demos."""
        return self.repo_root / "config" / "stakeholders.example.json"

    @classmethod
    def from_env(cls) -> Settings:
        repo = Path(os.environ.get("CTI_CONSOLE_REPO", REPO_ROOT)).resolve()
        return cls(
            repo_root=repo,
            out_dir=Path(os.environ.get("CTI_CONSOLE_OUT", repo / "out")).resolve(),
            logs_dir=Path(os.environ.get("CTI_CONSOLE_LOGS", repo / "logs")).resolve(),
            cache_dir=Path(
                os.environ.get("CTI_CONSOLE_CACHE", repo / "console" / ".cache")
            ).resolve(),
            stakeholders_file=Path(
                os.environ.get("CTI_CONSOLE_STAKEHOLDERS", repo / "config" / "stakeholders.json")
            ).resolve(),
            company_dir=_company_dir(repo),
        )


def _company_dir(repo: Path) -> Path:
    """CTI_CONSOLE_COMPANY_DIR names a folder; CTI_CONSOLE_COMPANY a slug under config/."""
    explicit = os.environ.get("CTI_CONSOLE_COMPANY_DIR")
    if explicit:
        return Path(explicit).resolve()
    slug = os.environ.get("CTI_CONSOLE_COMPANY", DEFAULT_COMPANY)
    if not COMPANY_SLUG.match(slug):
        raise ValueError(f"CTI_CONSOLE_COMPANY={slug!r} is not a company slug (a to z, 0 to 9, -)")
    return (repo / "config" / "companies" / slug).resolve()
