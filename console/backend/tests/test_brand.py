"""The company brand: read from the file the builders use, and changed from the console."""

from __future__ import annotations

import dataclasses
import json
import shutil
import struct
import zlib
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from cti_console.api import create_app
from cti_console.config import REPO_ROOT, Settings

GENELABS = REPO_ROOT / "config" / "companies" / "genelabs"
WRITE = {"X-CTI-Console": "1"}
PNG = {**WRITE, "Content-Type": "image/png"}


def png(width: int, height: int) -> bytes:
    """A real, tiny, single colour PNG of the given size."""

    def chunk(kind: bytes, body: bytes) -> bytes:
        crc = zlib.crc32(kind + body)
        return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", crc)

    rows = b"".join(b"\x00" + b"\x10\x3b\x32" * width for _ in range(height))
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(rows))
        + chunk(b"IEND", b"")
    )


def _client(settings: Settings, company: Path | None = None) -> TestClient:
    if company is not None:
        settings = dataclasses.replace(settings, company_dir=company)
    return TestClient(create_app(settings, pdf_ready=False), base_url="http://127.0.0.1")


def _raw(folder: Path) -> dict[str, object]:
    return json.loads((folder / "company.json").read_text(encoding="utf-8"))


def _company(tmp_path: Path, **changes: object) -> Path:
    """A copy of the GeneLabs folder, so tests never change the committed one."""
    folder = tmp_path / "acme"
    shutil.copytree(GENELABS, folder)
    raw = _raw(folder)
    raw.update(changes)
    (folder / "company.json").write_text(json.dumps(raw), encoding="utf-8")
    return folder


def _form(**changes: object) -> dict[str, object]:
    raw = _raw(GENELABS)
    form = {
        k: raw[k] for k in ("name", "legal_name", "department", "program", "contact", "palette")
    }
    form.update(changes)
    return form


# ---------------------------------------------------------------------- reading
def test_genelabs_brand_is_served(settings: Settings) -> None:
    body = _client(settings).get("/api/brand").json()
    assert body["name"] == "GeneLabs"
    assert body["program"] == "Cyber Threat Intelligence"
    assert body["palette"]["accent"] == "167D61"
    assert body["light"]["accent"] == "#167d61"
    assert body["dark"]["accent"] == "#3fb48c"
    assert "symbol-tile" not in body["light"]
    assert len(body["version"]) == 12


@pytest.mark.parametrize("kind", ["logo", "banner", "symbol"])
def test_each_image_is_served_as_a_png(settings: Settings, kind: str) -> None:
    response = _client(settings).get(f"/api/brand/assets/{kind}")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert response.content.startswith(b"\x89PNG")


def test_only_the_three_images_can_be_asked_for(settings: Settings) -> None:
    assert _client(settings).get("/api/brand/assets/company.json").status_code == 422


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


def test_an_image_outside_the_company_folder_is_refused(settings: Settings, tmp_path: Path) -> None:
    (tmp_path / "secret.png").write_bytes(png(20, 20))
    assets = {"logo": "assets/logo.png", "banner": "assets/banner.png", "symbol": "../secret.png"}
    response = _client(settings, _company(tmp_path, assets=assets)).get("/api/brand/assets/symbol")
    assert response.status_code == 500
    assert "inside" in response.json()["detail"]


def test_an_image_that_is_not_a_png_is_refused(settings: Settings, tmp_path: Path) -> None:
    folder = _company(tmp_path)
    (folder / "assets" / "symbol.png").write_text("<svg onload=alert(1)>", encoding="utf-8")
    response = _client(settings, folder).get("/api/brand/assets/symbol")
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


# ---------------------------------------------------------------------- preview
def test_preview_derives_both_themes_and_passes_for_genelabs(settings: Settings) -> None:
    body = _client(settings).post("/api/brand/preview", json=_form(), headers=WRITE).json()
    assert body["ok"] is True
    assert body["light"]["accent"] == "#167d61"
    assert body["dark"]["accent"] != "#167d61"
    assert all(check["ok"] for check in body["checks"])


def test_preview_reports_an_accent_too_pale_to_read(settings: Settings) -> None:
    palette = {**_raw(GENELABS)["palette"], "accent": "FFD400"}  # type: ignore[dict-item]
    body = (
        _client(settings)
        .post("/api/brand/preview", json=_form(palette=palette), headers=WRITE)
        .json()
    )
    assert body["ok"] is False
    failed = [c["label"] for c in body["checks"] if not c["ok"]]
    assert "Accent on white (links)" in failed
    # Dark mode is derived, so it is lifted until it passes, whatever the accent.
    assert not [label for label in failed if label.startswith("Dark")]


def test_preview_needs_the_console_header(settings: Settings) -> None:
    assert _client(settings).post("/api/brand/preview", json=_form()).status_code == 403


# ---------------------------------------------------------------------- saving
def test_save_writes_the_file_the_builders_read(settings: Settings, tmp_path: Path) -> None:
    folder = _company(tmp_path)
    palette = {**_raw(GENELABS)["palette"], "accent": "1D4ED8"}  # type: ignore[dict-item]
    client = _client(settings, folder)
    response = client.put("/api/brand", json=_form(name="Acme", palette=palette), headers=WRITE)
    assert response.status_code == 200
    raw = _raw(folder)
    assert raw["name"] == "Acme"
    assert raw["palette"]["accent"] == "1D4ED8"  # type: ignore[index]
    assert raw["console"]["light"]["accent"] == "1D4ED8"  # type: ignore[index]
    assert raw["slug"] == "genelabs" and "assets" in raw and "_comment" in raw
    assert (folder / "company.json.bak").exists()
    assert client.get("/api/brand").json()["name"] == "Acme"


def test_save_refuses_colours_that_fail_contrast(settings: Settings, tmp_path: Path) -> None:
    folder = _company(tmp_path)
    before = (folder / "company.json").read_bytes()
    palette = {**_raw(GENELABS)["palette"], "text": "BBBBBB"}  # type: ignore[dict-item]
    response = _client(settings, folder).put(
        "/api/brand", json=_form(palette=palette), headers=WRITE
    )
    assert response.status_code == 422
    assert "Body text on white" in response.json()["detail"]
    assert (folder / "company.json").read_bytes() == before


@pytest.mark.parametrize(
    "change",
    [
        {"name": ""},
        {"name": "x" * 201},
        {"slug": "other"},
        {"palette": {"primary": "#103B32"}},
        {"assets": {"logo": "/etc/passwd"}},
    ],
)
def test_save_refuses_bad_fields(settings: Settings, tmp_path: Path, change: dict) -> None:
    folder = _company(tmp_path)
    response = _client(settings, folder).put("/api/brand", json=_form(**change), headers=WRITE)
    assert response.status_code == 422


def test_save_needs_the_console_header(settings: Settings, tmp_path: Path) -> None:
    folder = _company(tmp_path)
    assert _client(settings, folder).put("/api/brand", json=_form()).status_code == 403


def test_save_refuses_another_site(settings: Settings, tmp_path: Path) -> None:
    folder = _company(tmp_path)
    headers = {**WRITE, "Origin": "https://evil.example"}
    assert (
        _client(settings, folder).put("/api/brand", json=_form(), headers=headers).status_code
        == 403
    )


# ---------------------------------------------------------------------- images
def test_an_uploaded_image_replaces_the_old_one(settings: Settings, tmp_path: Path) -> None:
    folder = _company(tmp_path)
    client = _client(settings, folder)
    before = client.get("/api/brand").json()["version"]
    image = png(60, 60)
    response = client.put("/api/brand/assets/symbol", content=image, headers=PNG)
    assert response.status_code == 200
    assert response.json()["version"] != before
    assert (folder / "assets" / "symbol.png").read_bytes() == image
    assert (folder / "assets" / "symbol.png.bak").exists()
    assert client.get("/api/brand/assets/symbol").content == image


@pytest.mark.parametrize(
    ("kind", "size", "message"),
    [
        ("banner", (100, 100), "times as wide"),
        ("logo", (100, 300), "times as wide"),
        ("symbol", (10, 10), "pixels"),
        ("logo", (5000, 1000), "pixels"),
    ],
)
def test_an_image_of_the_wrong_shape_is_refused(
    settings: Settings, tmp_path: Path, kind: str, size: tuple[int, int], message: str
) -> None:
    folder = _company(tmp_path)
    before = (folder / "assets" / f"{kind}.png").read_bytes()
    response = _client(settings, folder).put(
        f"/api/brand/assets/{kind}", content=png(*size), headers=PNG
    )
    assert response.status_code == 422
    assert message in response.json()["detail"]
    assert (folder / "assets" / f"{kind}.png").read_bytes() == before


def test_an_upload_that_is_not_a_png_is_refused(settings: Settings, tmp_path: Path) -> None:
    folder = _company(tmp_path)
    client = _client(settings, folder)
    svg = b"<svg xmlns='http://www.w3.org/2000/svg' onload='alert(1)'/>"
    assert client.put("/api/brand/assets/logo", content=svg, headers=PNG).status_code == 422
    jpeg = {**WRITE, "Content-Type": "image/jpeg"}
    assert (
        client.put("/api/brand/assets/logo", content=png(300, 100), headers=jpeg).status_code == 415
    )


def test_an_upload_over_the_limit_is_refused(settings: Settings, tmp_path: Path) -> None:
    folder = _company(tmp_path)
    big = png(300, 100) + b"\x00" * (2 * 1024 * 1024)
    response = _client(settings, folder).put("/api/brand/assets/logo", content=big, headers=PNG)
    assert response.status_code == 413


def test_an_upload_needs_the_console_header(settings: Settings, tmp_path: Path) -> None:
    folder = _company(tmp_path)
    response = _client(settings, folder).put(
        "/api/brand/assets/logo", content=png(300, 100), headers={"Content-Type": "image/png"}
    )
    assert response.status_code == 403
