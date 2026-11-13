"""Companies: the list, the active one, new and duplicated ones, and keeping them apart."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from cti_console.api import create_app
from cti_console.brand import BrandIn, BrandStore
from cti_console.config import REPO_ROOT, Settings

TEMPLATES = REPO_ROOT / "config" / "companies"
CONSOLE = {"X-CTI-Console": "1", "Origin": "http://127.0.0.1:5173"}
BRAND_FIELDS = ("name", "legal_name", "department", "program", "contact", "palette")
PERSON = {"name": "Dana Reyes", "team": "SOC", "email": "dana@acme.example"}


def _client(settings: Settings) -> TestClient:
    return TestClient(create_app(settings, pdf_ready=False), base_url="http://127.0.0.1")


def _as(company: str) -> dict[str, str]:
    """Headers for a write the page makes while it shows `company`."""
    return {**CONSOLE, "X-CTI-Company": company}


def _create(client: TestClient, **body: object) -> dict[str, object]:
    response = client.post("/api/companies", json=body, headers=CONSOLE)
    assert response.status_code == 201, response.text
    return response.json()


def _pick(client: TestClient, slug: str) -> dict[str, object]:
    response = client.put("/api/companies/active", json={"slug": slug}, headers=CONSOLE)
    assert response.status_code == 200, response.text
    return response.json()


def _raw(folder: Path) -> dict[str, object]:
    return json.loads((folder / "company.json").read_text(encoding="utf-8"))


# ---------------------------------------------------------------------- the list
def test_genelabs_is_copied_in_once_and_listed_as_the_pipeline_company(
    settings: Settings,
) -> None:
    body = _client(settings).get("/api/companies").json()
    assert body["active"] == "genelabs"
    assert body["companies"] == [
        {
            "slug": "genelabs",
            "name": "GeneLabs",
            "program": "Cyber Threat Intelligence",
            "pipeline": True,
        }
    ]
    copy = settings.data_dir / "companies" / "genelabs"
    committed = TEMPLATES / "genelabs" / "company.json"
    assert (copy / "company.json").read_bytes() == committed.read_bytes()
    images = sorted(p.name for p in (copy / "assets").iterdir())
    assert images == ["banner.png", "logo.png", "symbol.png"]


def test_the_starter_is_never_listed(settings: Settings) -> None:
    slugs = [c["slug"] for c in _client(settings).get("/api/companies").json()["companies"]]
    assert "_starter" not in slugs and "new-company" not in slugs


def test_a_restart_keeps_the_console_copy(settings: Settings) -> None:
    """Saved branding lives in data/; starting again must not put the committed copy back."""
    client = _client(settings)
    form = {**_raw(TEMPLATES / "genelabs"), "name": "GeneLabs Renamed"}
    saved = {k: form[k] for k in BRAND_FIELDS}
    assert client.put("/api/brand", json=saved, headers=_as("genelabs")).status_code == 200
    assert _client(settings).get("/api/brand").json()["name"] == "GeneLabs Renamed"
    # And the repo's own copy is untouched.
    assert _raw(TEMPLATES / "genelabs")["name"] == "GeneLabs"


# ---------------------------------------------------------------------- making companies
def test_a_new_company_starts_from_the_neutral_starter(settings: Settings) -> None:
    client = _client(settings)
    body = _create(client, name="Acme Biotech", slug="acme")
    assert body["active"] == "genelabs"  # making one does not switch to it
    assert [c["slug"] for c in body["companies"]] == ["acme", "genelabs"]

    folder = settings.data_dir / "companies" / "acme"
    raw = _raw(folder)
    assert raw["slug"] == "acme"
    assert raw["name"] == raw["legal_name"] == "Acme Biotech"
    assert raw["palette"] == _raw(TEMPLATES / "_starter")["palette"]
    assert (folder / "out").is_dir() and (folder / "logs").is_dir()
    assert not (folder / "stakeholders.json").exists()


def test_the_starter_brand_passes_every_readability_check() -> None:
    raw = _raw(TEMPLATES / "_starter")
    fields = {k: raw[k] for k in BRAND_FIELDS}
    assert BrandStore.preview(BrandIn.model_validate(fields)).ok


def test_a_duplicate_copies_the_brand_but_not_people_or_reports(settings: Settings) -> None:
    client = _client(settings)
    _create(client, name="Acme", slug="acme")
    _pick(client, "acme")
    assert client.post("/api/stakeholders", json=PERSON, headers=_as("acme")).status_code == 201
    acme = settings.data_dir / "companies" / "acme"
    (acme / "out" / "report.docx").write_bytes(b"x")
    (acme / "assets" / "logo.png.bak").write_bytes(b"old")

    _create(client, name="Acme Europe", slug="acme-eu", source="acme")
    copy = settings.data_dir / "companies" / "acme-eu"
    assert _raw(copy)["name"] == "Acme Europe"
    assert _raw(copy)["legal_name"] == _raw(acme)["legal_name"]  # kept from the source
    assert _raw(copy)["palette"] == _raw(acme)["palette"]
    assert not (copy / "stakeholders.json").exists()
    assert list((copy / "out").iterdir()) == []
    assert not (copy / "assets" / "logo.png.bak").exists()


def test_a_slug_already_taken_is_refused(settings: Settings) -> None:
    client = _client(settings)
    response = client.post(
        "/api/companies", json={"name": "Again", "slug": "genelabs"}, headers=CONSOLE
    )
    assert response.status_code == 409
    assert _raw(settings.data_dir / "companies" / "genelabs")["name"] == "GeneLabs"


@pytest.mark.parametrize(
    ("body", "status"),
    [
        ({"name": "Acme", "slug": "../escape"}, 422),
        ({"name": "Acme", "slug": "Acme"}, 422),
        ({"name": "Acme", "slug": "_starter"}, 422),
        ({"name": "", "slug": "acme"}, 422),
        ({"name": "Acme", "slug": "acme", "out_dir": "/etc"}, 422),
        ({"name": "Acme", "slug": "acme", "source": "nobody"}, 404),
    ],
)
def test_bad_new_companies_are_refused(
    settings: Settings, body: dict[str, object], status: int
) -> None:
    response = _client(settings).post("/api/companies", json=body, headers=CONSOLE)
    assert response.status_code == status
    assert sorted(p.name for p in (settings.data_dir / "companies").iterdir()) == ["genelabs"]


# ---------------------------------------------------------------------- switching
def test_switching_shows_only_that_company(settings: Settings) -> None:
    client = _client(settings)
    assert any(d["id"] == "CTI26-01" for d in client.get("/api/deliverables").json())
    _create(client, name="Acme", slug="acme")

    assert _pick(client, "acme")["active"] == "acme"
    assert client.get("/api/brand").json()["name"] == "Acme"
    assert client.get("/api/deliverables").json() == []
    assert client.get("/api/runs").json() == []
    assert client.get("/api/deliverables/CTI26-01/file").status_code == 404
    assert client.get("/api/stakeholders").json()["has_example"] is False
    assert client.get("/api/summary").status_code == 200

    _pick(client, "genelabs")
    assert client.get("/api/brand").json()["name"] == "GeneLabs"
    assert client.get("/api/deliverables/CTI26-01/file").status_code == 200


def test_the_choice_is_remembered_for_the_next_start(settings: Settings) -> None:
    client = _client(settings)
    _create(client, name="Acme", slug="acme")
    _pick(client, "acme")
    assert _client(settings).get("/api/companies").json()["active"] == "acme"


def test_a_remembered_company_that_was_removed_falls_back(settings: Settings) -> None:
    (settings.data_dir).mkdir(parents=True)
    (settings.data_dir / "console.json").write_text('{"active": "gone"}', encoding="utf-8")
    assert _client(settings).get("/api/companies").json()["active"] == "genelabs"


def test_an_unknown_company_cannot_be_picked(settings: Settings) -> None:
    client = _client(settings)
    response = client.put("/api/companies/active", json={"slug": "nobody"}, headers=CONSOLE)
    assert response.status_code == 404
    assert client.get("/api/companies").json()["active"] == "genelabs"


# ---------------------------------------------------------------------- writes
def test_stakeholders_are_kept_per_company(settings: Settings) -> None:
    client = _client(settings)
    _create(client, name="Acme", slug="acme")
    _pick(client, "acme")
    assert client.post("/api/stakeholders", json=PERSON, headers=_as("acme")).status_code == 201
    acme_file = settings.data_dir / "companies" / "acme" / "stakeholders.json"
    assert "Dana Reyes" in acme_file.read_text(encoding="utf-8")
    assert not settings.stakeholders_file.exists()  # GeneLabs' list was not touched
    _pick(client, "genelabs")
    assert client.get("/api/stakeholders").json()["stakeholders"] == []


def test_a_write_for_another_company_is_refused(settings: Settings) -> None:
    """A tab still showing GeneLabs must not save into Acme after another tab switched."""
    client = _client(settings)
    _create(client, name="Acme", slug="acme")
    _pick(client, "acme")
    stale = client.post("/api/stakeholders", json=PERSON, headers=_as("genelabs"))
    assert stale.status_code == 409
    assert "switched" in stale.json()["detail"]
    missing = client.post("/api/stakeholders", json=PERSON, headers=CONSOLE)
    assert missing.status_code == 400
    assert not (settings.data_dir / "companies" / "acme" / "stakeholders.json").exists()


@pytest.mark.parametrize(
    "headers",
    [{}, {"X-CTI-Console": "1", "Origin": "https://evil.example"}],
)
def test_picking_and_making_need_the_console_page(
    settings: Settings, headers: dict[str, str]
) -> None:
    client = _client(settings)
    _create(client, name="Acme", slug="acme")
    assert (
        client.put("/api/companies/active", json={"slug": "acme"}, headers=headers).status_code
        == 403
    )
    assert (
        client.post("/api/companies", json={"name": "B", "slug": "b"}, headers=headers).status_code
        == 403
    )
    assert client.get("/api/companies").json()["active"] == "genelabs"
