#!/usr/bin/env python3
"""Fill one component's prompts with the run's company, ready for a headless session.

    python3 scripts/render_task.py <component> <out_dir>

Copies every ``components/<component>/*.md`` into ``out_dir`` with each ``{{name}}``
placeholder replaced from the company folder (``CTI_COMPANY`` / ``CTI_COMPANY_DIR``),
points paths to sibling prompts at the copies, and puts a short company note at the top
of each ``task*.md``. An unknown placeholder fails the run here, before any model call,
so a typo never reaches the model as literal braces.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "core" / "tools"))

from cti_profile import Company, load_company

PLACEHOLDER = re.compile(r"\{\{\s*([a-z_]+)\s*\}\}")
NOT_SET = "(not set in profile.json)"


def _listed(items: tuple[str, ...]) -> str:
    return ", ".join(items) if items else NOT_SET


def values(company: Company) -> dict[str, str]:
    """Every placeholder a prompt may use."""
    brand, profile = company.brand, company.profile
    return {
        "company": brand.name,
        "legal_name": brand.legal_name,
        "slug": brand.slug,
        "analyst": profile.analyst or "the CTI Lead",
        "industry": profile.industry or NOT_SET,
        "domains": _listed(profile.domains),
        "domain": profile.domains[0] if profile.domains else NOT_SET,
        "own_products": _listed(profile.own_products),
        "ics_products": _listed(profile.ics_products),
        "security_contact": profile.security_contact or NOT_SET,
        "company_dir": str(company.folder),
        "profile": str(company.folder / "profile.json"),
        "tech_profile": str(company.tech_profile),
        "peer_watchlist": str(company.peer_watchlist),
    }


def company_note(company: Company, fills: dict[str, str]) -> str:
    """What every session is told first, so skills that say "the company" resolve."""
    return (
        f"> **Company for this run: {fills['company']}** ({fills['legal_name']}), "
        f"{fills['industry']}. Wherever this task or a skill says \"the company\", or names "
        f"a company placeholder, it means {fills['company']}. Its facts are in "
        f"`{fills['profile']}`; its tech profile is `{fills['tech_profile']}` and its peer "
        f"watchlist `{fills['peer_watchlist']}`. Name no other organisation as the author or "
        f"owner of a deliverable.\n\n"
    )


def render(text: str, fills: dict[str, str], source: str) -> str:
    unknown = sorted({m.group(1) for m in PLACEHOLDER.finditer(text)} - fills.keys())
    if unknown:
        raise SystemExit(f"{source}: unknown placeholder(s) {', '.join(unknown)}")
    return PLACEHOLDER.sub(lambda m: fills[m.group(1)], text)


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(__doc__, file=sys.stderr)
        return 2
    component, out_dir = argv[1], Path(argv[2])
    source_dir = REPO_ROOT / "components" / component
    if not source_dir.is_dir():
        print(f"unknown component {component}", file=sys.stderr)
        return 2
    company = load_company()
    fills = values(company)
    out_dir.mkdir(parents=True, exist_ok=True)
    for source in sorted(source_dir.glob("*.md")):
        text = render(source.read_text(encoding="utf-8"), fills, str(source))
        # Sibling prompts are read from the filled copies, not the raw templates.
        text = text.replace(f"components/{component}/", f"{out_dir.as_posix()}/")
        if source.name.startswith("task"):
            text = company_note(company, fills) + text
        (out_dir / source.name).write_text(text, encoding="utf-8")
    print(f"[render_task] {component} for {fills['company']} -> {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
