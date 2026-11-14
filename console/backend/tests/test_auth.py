"""Sign in and roles: the OpenID Connect flow against a fake provider, and who may do what."""

from __future__ import annotations

import base64
import hashlib
import json
import time
from collections.abc import Callable
from urllib.parse import parse_qs, urlsplit

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

from cti_console import auth as auth_module
from cti_console.api import NO_COMPANY, create_app
from cti_console.auth import (
    LOGIN_COOKIE,
    SESSION_COOKIE,
    AuthSettings,
    OidcClient,
    roles_from_groups,
    sign,
    unsign,
)
from cti_console.config import REPO_ROOT, Settings

ISSUER = "https://login.example.test/tenant/v2.0"
CLIENT_ID = "cti-console-test"
SECRET = b"s" * 40
CONSOLE = {"X-CTI-Console": "1", "Origin": "http://127.0.0.1:5173"}
PERSON = {"name": "Dana Reyes", "team": "SOC", "email": "dana@acme.example"}
BRAND = json.loads((REPO_ROOT / "config/companies/genelabs/company.json").read_text("utf-8"))
BRAND_FORM = {
    k: BRAND[k] for k in ("name", "legal_name", "department", "program", "contact", "palette")
}


def auth_settings(**changes: object) -> AuthSettings:
    base = {
        "mode": "oidc",
        "issuer": ISSUER,
        "client_id": CLIENT_ID,
        "session_secret": SECRET,
    }
    return AuthSettings(**{**base, **changes})  # type: ignore[arg-type]


# ---------------------------------------------------------------------- a fake provider
class FakeProvider:
    """Discovery, keys and a token endpoint, answering like Entra ID or Cognito."""

    def __init__(self) -> None:
        self.key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        public = jwt.algorithms.RSAAlgorithm.to_jwk(self.key.public_key(), as_dict=True)
        self.jwks = {"keys": [{**public, "kid": "k1", "use": "sig", "alg": "RS256"}]}
        self.claims: dict[str, object] = {}
        self.nonce = ""
        self.token_requests: list[dict[str, list[str]]] = []
        self.sign_with = self.key

    def id_token(self, **overrides: object) -> str:
        now = int(time.time())
        claims = {
            "iss": ISSUER,
            "aud": CLIENT_ID,
            "sub": "user-1",
            "iat": now,
            "exp": now + 600,
            "nonce": self.nonce,
            "name": "Dana Reyes",
            "email": "dana@acme.example",
            **self.claims,
            **overrides,
        }
        return jwt.encode(claims, self.sign_with, algorithm="RS256", headers={"kid": "k1"})

    def handler(self, request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if url.endswith("/.well-known/openid-configuration"):
            return httpx.Response(
                200,
                json={
                    "issuer": ISSUER,
                    "authorization_endpoint": "https://login.example.test/authorize",
                    "token_endpoint": "https://login.example.test/token",
                    "jwks_uri": "https://login.example.test/keys",
                    "end_session_endpoint": "https://login.example.test/logout",
                },
            )
        if url.endswith("/keys"):
            return httpx.Response(200, json=self.jwks)
        if url.endswith("/token"):
            self.token_requests.append(parse_qs(request.content.decode("ascii")))
            return httpx.Response(200, json={"id_token": self.id_token(), "token_type": "Bearer"})
        return httpx.Response(404)


@pytest.fixture
def provider() -> FakeProvider:
    return FakeProvider()


def app_client(settings: Settings, provider: FakeProvider, **changes: object) -> TestClient:
    config = auth_settings(**changes)
    oidc = OidcClient(config, httpx.Client(transport=httpx.MockTransport(provider.handler)))
    app = create_app(settings, pdf_ready=False, auth=config, oidc=oidc)
    return TestClient(app, base_url="http://127.0.0.1", follow_redirects=False)


def as_person(client: TestClient, *groups: str, sub: str = "user-1") -> TestClient:
    """Signed in as someone in `groups`, as the callback would leave them."""
    session = {"sub": sub, "name": sub, "email": "", "groups": list(groups)}
    client.cookies.set(SESSION_COOKIE, sign(session, SECRET, 3600))
    return client


def sign_in(client: TestClient, provider: FakeProvider) -> httpx.Response:
    start = client.get("/api/auth/login")
    assert start.status_code == 302, start.text
    query = parse_qs(urlsplit(start.headers["location"]).query)
    provider.nonce = query["nonce"][0]
    return client.get("/api/auth/callback", params={"code": "c0de", "state": query["state"][0]})


# ---------------------------------------------------------------------- roles
def test_groups_become_roles() -> None:
    platform, roles = roles_from_groups(
        [
            "cti-viewer-acme",
            "cti-admin-acme",
            "cti-viewer-initech",
            "Domain Users",
            "cti-admin-../x",
        ],
        "cti-",
    )
    assert platform is False
    assert roles == {"acme": "admin", "initech": "viewer"}
    assert roles_from_groups(["cti-platform-admin"], "cti-") == (True, {})


def test_a_signed_cookie_cannot_be_altered_or_outlive_itself() -> None:
    value = sign({"sub": "a"}, SECRET, 60)
    assert unsign(value, SECRET)["sub"] == "a"
    body, mac = value.split(".")
    forged = base64.urlsafe_b64encode(b'{"sub":"b","exp":9999999999}').rstrip(b"=").decode()
    assert unsign(f"{forged}.{mac}", SECRET) is None
    assert unsign(value, b"x" * 40) is None
    assert unsign(sign({"sub": "a"}, SECRET, -1), SECRET) is None
    assert unsign("not a cookie", SECRET) is None


# ---------------------------------------------------------------------- the flow
def test_sign_in_runs_the_code_flow_with_pkce(settings: Settings, provider: FakeProvider) -> None:
    provider.claims = {"groups": ["cti-platform-admin", "Everyone"]}
    client = app_client(settings, provider)
    start = client.get("/api/auth/login")
    location = urlsplit(start.headers["location"])
    query = parse_qs(location.query)
    assert location.netloc == "login.example.test"
    assert query["code_challenge_method"] == ["S256"]
    assert query["redirect_uri"] == ["http://127.0.0.1:5173/api/auth/callback"]
    assert "HttpOnly" in start.headers["set-cookie"] and LOGIN_COOKIE in start.headers["set-cookie"]

    provider.nonce = query["nonce"][0]
    done = client.get("/api/auth/callback", params={"code": "c0de", "state": query["state"][0]})
    assert done.status_code == 302
    assert done.headers["location"] == "http://127.0.0.1:5173/#/"
    verifier = provider.token_requests[0]["code_verifier"][0]
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=")
    assert query["code_challenge"] == [challenge.decode()]

    me = client.get("/api/me").json()
    assert me == {
        "auth": "oidc",
        "name": "Dana Reyes",
        "email": "dana@acme.example",
        "platform_admin": True,
        "can_manage": True,
        "roles": {},
        "view_as": None,  # signed in, a role comes from the account alone
    }
    # Only groups that mean something here are kept in the cookie.
    session = unsign(client.cookies.get(SESSION_COOKIE), SECRET)
    assert session["groups"] == ["cti-platform-admin"]


def test_cognito_groups_claim(settings: Settings, provider: FakeProvider) -> None:
    provider.claims = {"cognito:groups": ["cti-viewer-genelabs"]}
    client = app_client(settings, provider, groups_claim="cognito:groups")
    assert sign_in(client, provider).status_code == 302
    assert client.get("/api/me").json()["roles"] == {"genelabs": "viewer"}


def test_a_callback_that_did_not_start_here_is_refused(
    settings: Settings, provider: FakeProvider
) -> None:
    client = app_client(settings, provider)
    client.get("/api/auth/login")
    response = client.get("/api/auth/callback", params={"code": "c0de", "state": "someone-else"})
    assert response.status_code == 400
    assert SESSION_COOKIE not in client.cookies


@pytest.mark.parametrize(
    "spoil",
    [
        lambda p: setattr(p, "claims", {"aud": "another-app"}),
        lambda p: setattr(p, "claims", {"iss": "https://evil.example.test"}),
        lambda p: setattr(p, "claims", {"exp": int(time.time()) - 3600}),
        lambda p: setattr(p, "claims", {"nonce": "replayed"}),
        lambda p: setattr(
            p, "sign_with", rsa.generate_private_key(public_exponent=65537, key_size=2048)
        ),
    ],
    ids=["audience", "issuer", "expired", "nonce", "signature"],
)
def test_a_bad_id_token_never_signs_in(
    settings: Settings, provider: FakeProvider, spoil: Callable[[FakeProvider], None]
) -> None:
    spoil(provider)
    client = app_client(settings, provider)
    response = sign_in(client, provider)
    assert response.status_code in (400, 401), response.text
    assert SESSION_COOKIE not in client.cookies
    assert client.get("/api/me").status_code == 401


def test_sign_out_clears_the_session(settings: Settings, provider: FakeProvider) -> None:
    client = as_person(app_client(settings, provider), "cti-platform-admin")
    response = client.post("/api/auth/logout", headers=CONSOLE)
    assert response.status_code == 200
    assert response.json()["redirect"].startswith("https://login.example.test/logout?")
    cleared = response.headers["set-cookie"]
    assert cleared.startswith(f'{SESSION_COOKIE}=""') and "Max-Age=0" in cleared


def test_with_sign_in_off_there_is_one_local_user(settings: Settings) -> None:
    client = TestClient(
        create_app(settings, pdf_ready=False, auth=AuthSettings()), base_url="http://127.0.0.1"
    )
    assert client.get("/api/auth/login").status_code == 404
    me = client.get("/api/me").json()
    assert me["auth"] == "off" and me["platform_admin"] is True


@pytest.mark.parametrize(
    ("env", "problem"),
    [
        ({"CTI_AUTH": "oidc"}, "needs CTI_OIDC_ISSUER"),
        (
            {
                "CTI_AUTH": "oidc",
                "CTI_OIDC_ISSUER": ISSUER,
                "CTI_OIDC_CLIENT_ID": "x",
                "CTI_SESSION_SECRET": "short",
            },
            "at least 32",
        ),
        ({"CTI_AUTH": "maybe"}, "use off or oidc"),
    ],
)
def test_sign_in_settings_are_checked_at_start(
    monkeypatch: pytest.MonkeyPatch, env: dict[str, str], problem: str
) -> None:
    for name in ("CTI_OIDC_ISSUER", "CTI_OIDC_CLIENT_ID", "CTI_SESSION_SECRET"):
        monkeypatch.delenv(name, raising=False)
    for name, value in env.items():
        monkeypatch.setenv(name, value)
    with pytest.raises(ValueError, match=problem):
        auth_module.AuthSettings.from_env()


# ---------------------------------------------------------------------- who may do what
@pytest.fixture
def with_acme(settings: Settings, provider: FakeProvider) -> TestClient:
    """GeneLabs and Acme, made by a platform admin. Cookies are cleared afterwards."""
    client = as_person(app_client(settings, provider), "cti-platform-admin", sub="root")
    assert (
        client.post(
            "/api/companies", json={"name": "Acme", "slug": "acme"}, headers=CONSOLE
        ).status_code
        == 201
    )
    client.cookies.clear()
    return client


def test_signed_out_sees_nothing(with_acme: TestClient) -> None:
    for path in (
        "/api/companies",
        "/api/brand",
        "/api/summary",
        "/api/brand/assets/logo",
        "/api/me",
    ):
        assert with_acme.get(path).status_code == 401, path
    assert with_acme.get("/api/health").status_code == 200


def test_a_viewer_reads_their_company_only(with_acme: TestClient) -> None:
    client = as_person(with_acme, "cti-viewer-acme")
    listing = client.get("/api/companies").json()
    assert listing == {"active": "acme", "companies": [listing["companies"][0]]}
    assert listing["companies"][0]["slug"] == "acme"
    assert client.get("/api/brand").json()["name"] == "Acme"
    assert client.get("/api/stakeholders").status_code == 200
    # Another company is not there for them, whether it exists or not.
    for slug in ("genelabs", "nobody"):
        response = client.put("/api/companies/active", json={"slug": slug}, headers=CONSOLE)
        assert response.status_code == 404


def test_a_viewer_cannot_change_anything(with_acme: TestClient) -> None:
    client = as_person(with_acme, "cti-viewer-acme")
    headers = {**CONSOLE, "X-CTI-Company": "acme"}
    assert client.put("/api/brand", json=BRAND_FORM, headers=headers).status_code == 403
    assert client.post("/api/stakeholders", json=PERSON, headers=headers).status_code == 403
    made = client.post("/api/companies", json={"name": "Mine", "slug": "mine"}, headers=CONSOLE)
    assert made.status_code == 403


def test_a_company_admin_changes_their_company(with_acme: TestClient) -> None:
    client = as_person(with_acme, "cti-admin-acme")
    headers = {**CONSOLE, "X-CTI-Company": "acme"}
    saved = client.put("/api/brand", json={**BRAND_FORM, "name": "Acme Renamed"}, headers=headers)
    assert saved.status_code == 200
    assert client.post("/api/stakeholders", json=PERSON, headers=headers).status_code == 201
    # But still adds no companies, and cannot name another to write to.
    made = client.post("/api/companies", json={"name": "Mine", "slug": "mine"}, headers=CONSOLE)
    assert made.status_code == 403
    other = client.put(
        "/api/brand", json=BRAND_FORM, headers={**CONSOLE, "X-CTI-Company": "genelabs"}
    )
    assert other.status_code == 409


def test_someone_with_no_company_is_told_so(with_acme: TestClient) -> None:
    client = as_person(with_acme, "Everyone")
    assert client.get("/api/companies").json() == {"active": "", "companies": []}
    response = client.get("/api/brand")
    assert response.status_code == 403
    assert response.json()["detail"] == NO_COMPANY


def test_each_person_keeps_their_own_shown_company(with_acme: TestClient) -> None:
    a = as_person(with_acme, "cti-platform-admin", sub="a")
    assert a.put("/api/companies/active", json={"slug": "acme"}, headers=CONSOLE).status_code == 200
    assert a.get("/api/brand").json()["name"] == "Acme"

    b = as_person(with_acme, "cti-platform-admin", sub="b")
    assert b.get("/api/brand").json()["name"] == "GeneLabs"  # a's switch did not move b

    a = as_person(with_acme, "cti-platform-admin", sub="a")
    assert a.get("/api/companies").json()["active"] == "acme"  # and a's choice is kept
