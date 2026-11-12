"""Reuse the pipeline's own rules instead of copying them.

The ID patterns live in scripts/update_state.py and the broken document check in
scripts/pending_deliverables.py. Importing them keeps the console and the pipeline in
agreement: if the pipeline tightens what counts as broken, the console follows.
"""

from __future__ import annotations

import hashlib
import importlib.util
import re
from collections.abc import Callable
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from types import ModuleType

ShellCheck = Callable[[Path, str, str], "str | None"]


@dataclass(frozen=True)
class PipelineRules:
    """The pieces of pipeline logic the console depends on."""

    kinds: dict[str, re.Pattern[str]]
    shell_reason: ShellCheck
    # Kinds the pipeline runs the shell check on. A CVE brief is a one page table, so the
    # paragraph minimum would wrongly call every brief broken.
    checked_kinds: frozenset[str]
    # Changes whenever either script changes, so results saved under older rules are dropped.
    version: str


SCRIPTS = ("update_state", "pending_deliverables")


def _scripts_version(scripts_dir: Path) -> str:
    digest = hashlib.sha256()
    for name in SCRIPTS:
        digest.update((scripts_dir / f"{name}.py").read_bytes())
    return digest.hexdigest()[:16]


def _load(scripts_dir: Path, name: str) -> ModuleType:
    path = scripts_dir / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"_pipeline_{name}", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load pipeline script {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@cache
def load_rules(scripts_dir: Path) -> PipelineRules:
    """Load once per scripts folder. Both scripts only define functions at import time."""
    update_state = _load(scripts_dir, "update_state")
    pending = _load(scripts_dir, "pending_deliverables")
    return PipelineRules(
        kinds=dict(update_state.KINDS),
        shell_reason=pending.shell_reason,
        checked_kinds=frozenset(pending.MIN_PARAS),
        version=_scripts_version(scripts_dir),
    )
