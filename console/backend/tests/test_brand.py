"""The console reads the company's brand from the same file the document builders use."""

from __future__ import annotations

import dataclasses
import json
import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from cti_console.api import create_app
from cti_console.config import REPO_ROOT, Settings

GENELABS = REPO_ROOT / "config" / "companies" / "genelabs"


def _client(settings: Settings, company: Path | None = None) -> TestClient:
    if company is not None:
        settings = dataclasses.replace(settings, company_dir=company)
    return TestClient(create_app(settings, pdf_ready=False), base_url="http://127.0.0.1")


def _company(tmp_path: Path, **changes: object) -> Path:
    folder = tmp_path / "acme"
    shutil.copytree(GENELABS, folder)
    raw = json.loads((folder / "company.json").read_text(encoding="utf-8"))
    raw.update(changes)
    (folder / "company.json").write_text(json.dumps(raw), encoding="utf-8")
    return folder


def test_genelabs_brand_is_served(settings: Settings) -> None:
    body = _client(settings).get("/api/brand").json()
    assert body["name"] == "GeneLabs"
    assert body["program"] == "Cyber Threat Intelligence"
    assert body["light"]["accent"] == "#167d61"
    assert body["dark"]["accent"] == "#3fb48c"
    assert "symbol-tile" not in body["light"]


def test_the_symbol_is_served_as_a_png(settings: Settings) -> None:
    response = _client(settings).get("/api/brand/symbol")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert response.content.startswith(b"\x89PNG")


def test_another_company_needs_no_code_change(settings: Settings, tmp_path: Path) -> None:
    folder = _company(tmp_path, name="Acme", console={"light": {"accent": "AA0000"}})
    body = _client(settings, folder).get("/api/brand").json()
    assert body["name"] == "Acme"
    assert body["light"] == {"accent": "#aa0000"}
    assert body["dark"] == {}


@pytest.mark.parametrize(
    "console",
    [
        {"light": {"accent": "#AA0000"}},
        {"light": {"accent": "red"}},
        {"light": {"ok-bg": "AA0000"}},
        {"light": {"accent": "AA0000; background: url(x)"}},
        {"sepia": {}},
    ],
)
def test_bad_console_colours_are_refused(
    settings: Settings, tmp_path: Path, console: dict[str, object]
) -> None:
    response = _client(settings, _company(tmp_path, console=console)).get("/api/brand")
    assert response.status_code == 500
    detail = response.json()["detail"]
    assert "brand file" in detail or "unknown tokens" in detail


def test_a_symbol_outside_the_company_folder_is_refused(settings: Settings, tmp_path: Path) -> None:
    (tmp_path / "secret.png").write_bytes(b"\x89PNG\r\n\x1a\nsecret")
    folder = _company(tmp_path, assets={"symbol": "../secret.png"})
    response = _client(settings, folder).get("/api/brand/symbol")
    assert response.status_code == 500
    assert "inside" in response.json()["detail"]


def test_a_symbol_that_is_not_a_png_is_refused(settings: Settings, tmp_path: Path) -> None:
    folder = _company(tmp_path)
    (folder / "assets" / "symbol.png").write_text("<svg onload=alert(1)>", encoding="utf-8")
    response = _client(settings, folder).get("/api/brand/symbol")
    assert response.status_code == 500
    assert "not a PNG" in response.json()["detail"]


def test_a_missing_brand_file_says_where_it_looked(settings: Settings, tmp_path: Path) -> None:
    response = _client(settings, tmp_path).get("/api/brand")
    assert response.status_code == 500
    assert "No brand file" in response.json()["detail"]


def test_a_company_slug_cannot_climb_out(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CTI_CONSOLE_COMPANY_DIR", raising=False)
    monkeypatch.setenv("CTI_CONSOLE_COMPANY", "../secrets")
    with pytest.raises(ValueError, match="slug"):
        Settings.from_env()


def test_the_company_is_chosen_by_slug(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CTI_CONSOLE_COMPANY_DIR", raising=False)
    monkeypatch.setenv("CTI_CONSOLE_COMPANY", "acme")
    assert Settings.from_env().company_dir == REPO_ROOT / "config" / "companies" / "acme"
