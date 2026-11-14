"""View as: the local console acting as each role for a demo, and really held to it."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from cti_console.api import create_app
from cti_console.auth import SESSION_COOKIE, AuthSettings, sign
from cti_console.config import Settings

CONSOLE = {"X-CTI-Console": "1", "Origin": "http://127.0.0.1:5173"}
WRITE = {**CONSOLE, "X-CTI-Company": "genelabs"}
PERSON = {"name": "Dana Reyes", "team": "SOC", "email": "dana@genelabs.example"}
NEW_COMPANY = {"slug": "acme", "name": "Acme Biotech"}


def _client(settings: Settings) -> TestClient:
    return TestClient(
        create_app(settings, pdf_ready=False, auth=AuthSettings()), base_url="http://127.0.0.1"
    )


def _view(client: TestClient, role: str, company: str | None = None) -> dict[str, object]:
    response = client.put("/api/view-as", json={"role": role, "company": company}, headers=CONSOLE)
    assert response.status_code == 200, response.text
    return response.json()


def test_the_local_user_starts_as_platform_admin(settings: Settings) -> None:
    me = _client(settings).get("/api/me").json()
    assert me["platform_admin"] is True
    assert me["view_as"] == {"role": "platform", "company": None}


def test_a_viewer_reads_but_every_change_is_refused(settings: Settings) -> None:
    client = _client(settings)
    me = _view(client, "viewer", "genelabs")
    assert me["platform_admin"] is False
    assert me["can_manage"] is False
    assert me["roles"] == {"genelabs": "viewer"}
    assert client.get("/api/me").json()["view_as"] == {"role": "viewer", "company": "genelabs"}

    assert client.get("/api/stakeholders").status_code == 200
    assert client.get("/api/summary").status_code == 200
    assert client.post("/api/stakeholders", json=PERSON, headers=WRITE).status_code == 403
    assert client.post("/api/companies", json=NEW_COMPANY, headers=CONSOLE).status_code == 403


def test_a_company_admin_changes_their_company_but_adds_none(settings: Settings) -> None:
    client = _client(settings)
    _view(client, "admin", "genelabs")
    assert client.post("/api/stakeholders", json=PERSON, headers=WRITE).status_code == 201
    assert client.post("/api/companies", json=NEW_COMPANY, headers=CONSOLE).status_code == 403


def test_back_to_platform_admin_restores_everything(settings: Settings) -> None:
    client = _client(settings)
    _view(client, "viewer", "genelabs")
    me = _view(client, "platform")
    assert me["platform_admin"] is True
    assert client.post("/api/companies", json=NEW_COMPANY, headers=CONSOLE).status_code == 201
    # A role for one company shows only that company.
    _view(client, "viewer", "acme")
    listing = client.get("/api/companies").json()
    assert listing["active"] == "acme"
    assert [c["slug"] for c in listing["companies"]] == ["acme"]


@pytest.mark.parametrize(
    "body",
    [
        {"role": "viewer"},  # a company role needs its company
        {"role": "platform", "company": "genelabs"},
        {"role": "owner", "company": "genelabs"},
        {"role": "viewer", "company": "../etc"},
    ],
)
def test_a_role_that_does_not_fit_is_refused(settings: Settings, body: dict[str, object]) -> None:
    response = _client(settings).put("/api/view-as", json=body, headers=CONSOLE)
    assert response.status_code == 422


def test_a_missing_company_is_refused(settings: Settings) -> None:
    response = _client(settings).put(
        "/api/view-as", json={"role": "viewer", "company": "nobody"}, headers=CONSOLE
    )
    assert response.status_code == 404


def test_switching_is_a_write_from_the_console_page(settings: Settings) -> None:
    client = _client(settings)
    body = {"role": "viewer", "company": "genelabs"}
    assert client.put("/api/view-as", json=body).status_code == 403
    other = {**CONSOLE, "Origin": "https://evil.example"}
    assert client.put("/api/view-as", json=body, headers=other).status_code == 403


def test_with_sign_in_there_is_no_view_as(settings: Settings) -> None:
    secret = b"s" * 40
    config = AuthSettings(
        mode="oidc",
        issuer="https://login.example.test/t/v2.0",
        client_id="x",
        session_secret=secret,
    )
    client = TestClient(
        create_app(settings, pdf_ready=False, auth=config), base_url="http://127.0.0.1"
    )
    session = {"sub": "v", "name": "v", "email": "", "groups": ["cti-viewer-genelabs"]}
    client.cookies.set(SESSION_COOKIE, sign(session, secret, 3600))
    assert client.get("/api/me").json()["view_as"] is None
    response = client.put(
        "/api/view-as", json={"role": "platform", "company": None}, headers=CONSOLE
    )
    assert response.status_code == 404
    assert client.get("/api/me").json()["platform_admin"] is False
