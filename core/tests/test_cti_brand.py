"""The company brand file: it loads, it refuses bad input, and the builders obey it."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

CORE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CORE / "tools"))

import cti_brand
from cti_brand import BrandError, parse_brand

GENELABS = cti_brand.COMPANIES_DIR / "genelabs"
BULLETIN = CORE / ".claude/skills/genelabs-cti-bulletin/scripts/build_bulletin.py"


def make_company(tmp_path: Path, **changes: object) -> Path:
    """A copy of the GeneLabs folder with some company.json fields replaced."""
    folder = tmp_path / "acme"
    shutil.copytree(GENELABS, folder)
    raw = json.loads((folder / "company.json").read_text(encoding="utf-8"))
    raw.update(changes)
    (folder / "company.json").write_text(json.dumps(raw), encoding="utf-8")
    return folder


def test_the_committed_genelabs_brand_loads() -> None:
    brand = parse_brand(GENELABS)
    assert brand.name == "GeneLabs"
    assert brand.palette.accent == "167D61"
    assert brand.logo.is_file() and brand.banner.is_file() and brand.symbol.is_file()
    assert (
        brand.doc_comments
        == "GeneLabs Enterprise Information Security | Cyber Threat Intelligence"
    )


def test_hex_is_normalised_to_upper_case(tmp_path: Path) -> None:
    palette = json.loads((GENELABS / "company.json").read_text(encoding="utf-8"))[
        "palette"
    ]
    folder = make_company(tmp_path, palette={**palette, "accent": "abcdef"})
    assert parse_brand(folder).palette.accent == "ABCDEF"


@pytest.mark.parametrize("colour", ["#167D61", "167D6", "GGGGGG", 167061, None])
def test_a_bad_colour_is_refused(tmp_path: Path, colour: object) -> None:
    palette = json.loads((GENELABS / "company.json").read_text(encoding="utf-8"))[
        "palette"
    ]
    folder = make_company(tmp_path, palette={**palette, "accent": colour})
    with pytest.raises(BrandError, match="palette.accent"):
        parse_brand(folder)


def test_an_asset_outside_the_company_folder_is_refused(tmp_path: Path) -> None:
    outside = tmp_path / "elsewhere.png"
    outside.write_bytes(b"png")
    folder = make_company(
        tmp_path,
        assets={
            "logo": "../elsewhere.png",
            "banner": "assets/banner.png",
            "symbol": "assets/symbol.png",
        },
    )
    with pytest.raises(BrandError, match="inside"):
        parse_brand(folder)


def test_a_missing_asset_is_refused(tmp_path: Path) -> None:
    folder = make_company(
        tmp_path,
        assets={
            "logo": "assets/nope.png",
            "banner": "assets/banner.png",
            "symbol": "assets/symbol.png",
        },
    )
    with pytest.raises(BrandError, match="does not exist"):
        parse_brand(folder)


def test_a_missing_name_is_refused(tmp_path: Path) -> None:
    with pytest.raises(BrandError, match="'name'"):
        parse_brand(make_company(tmp_path, name=""))


def test_a_missing_brand_file_says_how_to_choose_a_company(tmp_path: Path) -> None:
    with pytest.raises(BrandError, match="CTI_COMPANY"):
        parse_brand(tmp_path)


@pytest.mark.parametrize("slug", ["../secrets", "Acme", "a/b", ""])
def test_a_company_slug_cannot_leave_the_companies_folder(
    monkeypatch: pytest.MonkeyPatch, slug: str
) -> None:
    monkeypatch.delenv(cti_brand.COMPANY_DIR_ENV, raising=False)
    monkeypatch.setenv(cti_brand.COMPANY_ENV, slug)
    with pytest.raises(BrandError, match="slug"):
        cti_brand.company_dir()


def test_the_default_company_is_genelabs(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.delenv(cti_brand.COMPANY_DIR_ENV, raising=False)
    monkeypatch.delenv(cti_brand.COMPANY_ENV, raising=False)
    monkeypatch.setenv(cti_brand.DATA_DIR_ENV, str(tmp_path))  # no console copy yet
    assert cti_brand.company_dir() == GENELABS


def test_the_console_copy_wins_over_the_committed_one(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The Branding tab saves into data/, so that is what the next document uses."""
    monkeypatch.delenv(cti_brand.COMPANY_DIR_ENV, raising=False)
    monkeypatch.setenv(cti_brand.COMPANY_ENV, "acme")
    monkeypatch.setenv(cti_brand.DATA_DIR_ENV, str(tmp_path))
    assert cti_brand.company_dir() == cti_brand.COMPANIES_DIR / "acme"
    saved = make_company(tmp_path / "companies", name="Acme")
    assert saved.name == "acme"
    assert cti_brand.company_dir() == saved


def test_a_bulletin_is_built_in_the_chosen_company_brand(tmp_path: Path) -> None:
    """End to end: a different company.json changes the document, with no code change."""
    palette = json.loads((GENELABS / "company.json").read_text(encoding="utf-8"))[
        "palette"
    ]
    folder = make_company(
        tmp_path,
        name="Acme",
        legal_name="Acme Corp",
        palette={**palette, "text": "123456"},
    )
    spec = tmp_path / "spec.json"
    spec.write_text(
        json.dumps(
            {
                "report_id": "CTI26-999",
                "title": "Test bulletin",
                "category": "THREAT BULLETIN",
                "date": "November 12, 2026",
                "severity": "LOW",
                "relevance": "Why it matters.",
                "what_happened": ["Something happened [1]."],
                "sources": [{"text": "Example source", "url": "https://example.test/"}],
            }
        ),
        encoding="utf-8",
    )
    out = tmp_path / "out.docx"
    subprocess.run(
        [sys.executable, str(BULLETIN), str(spec), str(out)],
        check=True,
        capture_output=True,
        text=True,
        env={**__import__("os").environ, cti_brand.COMPANY_DIR_ENV: str(folder)},
    )
    with zipfile.ZipFile(out) as docx:
        body = docx.read("word/document.xml").decode("utf-8")
        footer = "".join(
            docx.read(n).decode("utf-8") for n in docx.namelist() if "footer" in n
        )
        core = docx.read("docProps/core.xml").decode("utf-8")
    assert "Relevance to Acme" in body
    assert 'w:val="123456"' in body
    assert "Acme Corp" in footer
    assert "Acme Enterprise Information Security" in core
    assert "GeneLabs" not in body + footer + core


def test_the_banner_shape_comes_from_the_image() -> None:
    assert parse_brand(GENELABS).banner_aspect == 230 / 1800
