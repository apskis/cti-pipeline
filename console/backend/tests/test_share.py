"""Sharing the console: nothing through a tunnel without sign in, and the page from one port."""

from __future__ import annotations

import dataclasses
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from cti_console.api import LOCAL_ONLY, PAGE_CSP, create_app
from cti_console.auth import SESSION_COOKIE, AuthSettings, sign
from cti_console.config import Settings

SECRET = b"s" * 40
TUNNEL = "https://abc123-8765.usw2.devtunnels.ms"
# What a tunnel adds: Host is rewritten to localhost, the public name moves to these.
VIA_TUNNEL = {
    "X-Forwarded-For": "203.0.113.7",
    "X-Forwarded-Host": "abc123-8765.usw2.devtunnels.ms",
    "X-Forwarded-Proto": "https",
}


def signed_in(settings: Settings) -> TestClient:
    config = AuthSettings(
        mode="oidc",
        issuer="https://login.example.test/t/v2.0",
        client_id="x",
        session_secret=SECRET,
        console_url=TUNNEL,
    )
    client = TestClient(
        create_app(settings, pdf_ready=False, auth=config), base_url="http://localhost"
    )
    session = {"sub": "a", "name": "a", "email": "", "groups": ["cti-platform-admin"]}
    client.cookies.set(SESSION_COOKIE, sign(session, SECRET, 3600))
    return client


@pytest.fixture
def page(tmp_path: Path) -> Path:
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("<!doctype html><title>console</title>", encoding="utf-8")
    (dist / "assets" / "app.js").write_text("console.log(1)", encoding="utf-8")
    (tmp_path / "secret.txt").write_text("not for you", encoding="utf-8")
    return dist


# ---------------------------------------------------------------------- the guard
@pytest.mark.parametrize("header", ["X-Forwarded-For", "X-Forwarded-Host", "Forwarded"])
def test_without_sign_in_nothing_comes_through_a_tunnel(settings: Settings, header: str) -> None:
    client = TestClient(
        create_app(settings, pdf_ready=False, auth=AuthSettings()), base_url="http://localhost"
    )
    assert client.get("/api/companies").status_code == 200  # straight from this machine
    response = client.get("/api/companies", headers={header: "203.0.113.7"})
    assert response.status_code == 403
    assert response.text == LOCAL_ONLY
    assert response.headers["X-Content-Type-Options"] == "nosniff"


def test_with_sign_in_a_tunnel_is_fine(settings: Settings) -> None:
    client = signed_in(settings)
    assert client.get("/api/companies", headers=VIA_TUNNEL).status_code == 200
    # And a write from the tunnel's page is accepted, its Origin being the console's own.
    headers = {**VIA_TUNNEL, "X-CTI-Console": "1", "Origin": TUNNEL}
    assert (
        client.put("/api/companies/active", json={"slug": "genelabs"}, headers=headers).status_code
        == 200
    )
    # But not from another site.
    other = {**headers, "Origin": "https://evil.example"}
    assert (
        client.put("/api/companies/active", json={"slug": "genelabs"}, headers=other).status_code
        == 403
    )


# ---------------------------------------------------------------------- the page
def test_the_backend_serves_the_built_page_with_its_policy(settings: Settings, page: Path) -> None:
    served = dataclasses.replace(settings, static_dir=page)
    client = TestClient(
        create_app(served, pdf_ready=False, auth=AuthSettings()), base_url="http://127.0.0.1"
    )
    index = client.get("/")
    assert index.status_code == 200 and "<title>console</title>" in index.text
    assert index.headers["Content-Security-Policy"] == PAGE_CSP
    assert client.get("/assets/app.js").text == "console.log(1)"
    # Any other path is the page, for the hash routes; nothing outside dist is reachable.
    assert "<title>console</title>" in client.get("/settings/branding").text
    assert "not for you" not in client.get("/../secret.txt").text
    assert "not for you" not in client.get("/%2e%2e/secret.txt").text
    # The API keeps its own answers, including its 404s.
    assert client.get("/api/health").json() == {"status": "ok"}
    missing = client.get("/api/nothing-here")
    assert missing.status_code == 404 and missing.headers["Content-Security-Policy"] != PAGE_CSP


def test_without_a_built_page_the_backend_serves_only_the_api(settings: Settings) -> None:
    client = TestClient(
        create_app(settings, pdf_ready=False, auth=AuthSettings()), base_url="http://127.0.0.1"
    )
    assert client.get("/").status_code == 404
