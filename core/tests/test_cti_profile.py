"""The company profile: it loads beside the brand, refuses bad input, and falls back sanely."""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import pytest

CORE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CORE / "tools"))

import cti_brand
import cti_profile
from cti_profile import ProfileError, facts_dir, parse_profile

GENELABS = cti_brand.COMPANIES_DIR / "genelabs"
STARTER = cti_brand.COMPANIES_DIR / "_starter"


@pytest.fixture(autouse=True)
def _fresh(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Each test picks its own company; nothing is cached between them."""
    cti_profile._cached.cache_clear()
    for name in (cti_brand.COMPANY_ENV, cti_brand.COMPANY_DIR_ENV):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv(cti_brand.DATA_DIR_ENV, str(tmp_path / "data"))


def test_the_committed_genelabs_profile_loads() -> None:
    company = cti_profile.load_company()
    assert company.brand.name == "GeneLabs"
    assert company.profile.domains == ("genelabs.com",)
    assert "HelixSeq X" in company.profile.own_products
    assert company.tech_profile.is_file() and company.peer_watchlist.is_file()


def test_the_starter_profile_is_blank_but_valid() -> None:
    profile = parse_profile(STARTER)
    assert profile.domains == () and profile.own_products == ()
    assert profile.industry == ""


def test_a_company_dir_brings_its_own_facts(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    folder = tmp_path / "acme"
    shutil.copytree(STARTER, folder)
    raw = json.loads((folder / "profile.json").read_text(encoding="utf-8"))
    raw["domains"] = ["acme.example"]
    (folder / "profile.json").write_text(json.dumps(raw), encoding="utf-8")
    monkeypatch.setenv(cti_brand.COMPANY_DIR_ENV, str(folder))

    company = cti_profile.load_company()
    assert company.folder == folder.resolve()
    assert company.profile.domains == ("acme.example",)


def test_a_brand_only_copy_uses_the_committed_facts(tmp_path: Path) -> None:
    """A console copy from before profiles existed still runs, on the committed profile."""
    folder = tmp_path / "genelabs"
    shutil.copytree(GENELABS, folder, ignore=shutil.ignore_patterns("profile.json", "reference"))
    assert facts_dir(folder, "genelabs") == GENELABS


def test_an_unknown_company_without_a_profile_is_refused(tmp_path: Path) -> None:
    folder = tmp_path / "acme"
    shutil.copytree(STARTER, folder, ignore=shutil.ignore_patterns("profile.json"))
    with pytest.raises(ProfileError, match="No profile"):
        parse_profile(facts_dir(folder, "acme"))


@pytest.mark.parametrize(
    ("field", "value"),
    [("domains", "genelabs.com"), ("domains", [""]), ("industry", ["a list"]), ("own_products", [3])],
)
def test_malformed_fields_are_refused(tmp_path: Path, field: str, value: object) -> None:
    folder = tmp_path / "bad"
    folder.mkdir()
    (folder / "profile.json").write_text(json.dumps({field: value}), encoding="utf-8")
    with pytest.raises(ProfileError, match=field):
        parse_profile(folder)
