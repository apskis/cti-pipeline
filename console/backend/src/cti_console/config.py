"""Where the console reads from and keeps its companies."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

# src/cti_console/config.py -> repo root is four levels up from this file's folder.
REPO_ROOT = Path(__file__).resolve().parents[4]
# The company whose reports, logs and stakeholders predate companies. They stay where the
# pipeline and earlier consoles left them: out/, logs/ and config/stakeholders.json at the
# repo root. Every other company keeps its own under data/companies/<slug>/.
PIPELINE_COMPANY = "genelabs"
# A slug becomes a folder name, so it is held to a shape that cannot climb out.
COMPANY_SLUG = re.compile(r"^[a-z0-9][a-z0-9-]{0,39}$")


@dataclass(frozen=True)
class Settings:
    """Folders the console reads. Overridable by env so tests can point at a sample tree.

    out_dir, logs_dir and stakeholders_file are the pipeline company's. Every other
    company keeps its own under data_dir/companies/<slug>/.
    """

    repo_root: Path
    out_dir: Path
    logs_dir: Path
    # The console's own scratch space: branded PDFs made from out/'s reports. Not out/,
    # which belongs to the pipeline.
    cache_dir: Path
    # Who the intelligence is for. Gitignored, because it holds names and email addresses.
    stakeholders_file: Path
    # Every company's own folder, and the console's remembered choice. Gitignored and
    # kept out of the pipeline image: it holds stakeholders and reports.
    data_dir: Path
    # The company the console opens with, until one is picked in the header.
    company: str = PIPELINE_COMPANY

    @property
    def scripts_dir(self) -> Path:
        return self.repo_root / "scripts"

    @property
    def templates_dir(self) -> Path:
        """Committed company folders: the first copy of each, and the blank starter."""
        return self.repo_root / "config" / "companies"

    @property
    def stakeholders_example(self) -> Path:
        """Made up GeneLabs teams, committed, for a first start and for demos."""
        return self.repo_root / "config" / "stakeholders.example.json"

    @classmethod
    def from_env(cls) -> Settings:
        repo = Path(os.environ.get("CTI_CONSOLE_REPO", REPO_ROOT)).resolve()
        company = os.environ.get("CTI_CONSOLE_COMPANY", PIPELINE_COMPANY)
        if not COMPANY_SLUG.match(company):
            raise ValueError(
                f"CTI_CONSOLE_COMPANY={company!r} is not a company slug (a to z, 0 to 9, -)"
            )
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
            data_dir=Path(os.environ.get("CTI_DATA_DIR", repo / "data")).resolve(),
            company=company,
        )
