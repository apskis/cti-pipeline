"""Where the console reads from. Everything is read only."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

# src/cti_console/config.py -> repo root is four levels up from this file's folder.
REPO_ROOT = Path(__file__).resolve().parents[4]


@dataclass(frozen=True)
class Settings:
    """Folders the console reads. Overridable by env so tests can point at a sample tree."""

    repo_root: Path
    out_dir: Path
    logs_dir: Path
    # The console's own scratch space: branded PDFs made from out/'s reports. Not out/,
    # which belongs to the pipeline.
    cache_dir: Path

    @property
    def scripts_dir(self) -> Path:
        return self.repo_root / "scripts"

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
        )
