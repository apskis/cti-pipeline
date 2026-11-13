"""Who is using the console, and what they may do.

Two modes, set with CTI_AUTH:

- ``off`` (the default): the console runs on this machine for one person, who may do
  everything. Nothing here is involved.
- ``oidc``: people sign in with the identity provider the cloud already has, Entra ID on
  Azure or Cognito on AWS. The backend runs the OpenID Connect code flow with PKCE itself
  and keeps the result in a signed, HttpOnly cookie, so the page never holds a token and
  images and the framed PDF are sent the cookie like any other request.

Roles come from the groups (or Entra app roles) in the ID token, named with a prefix
(``cti-`` by default):

- ``cti-platform-admin``: every company, and may add companies.
- ``cti-admin-<slug>``: reads that company and changes its branding and stakeholders.
- ``cti-viewer-<slug>``: reads that company.

The groups are kept in the session and turned into roles on every request, so a rule
change here applies at once; a group change at the provider applies at the next sign in.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from dataclasses import dataclass, field
from typing import Literal
from urllib.parse import urlencode, urlsplit

import httpx
import jwt

from .config import COMPANY_SLUG

Role = Literal["admin", "viewer"]
SESSION_COOKIE = "cti_session"
LOGIN_COOKIE = "cti_login"
LOGIN_SECONDS = 600  # time allowed at the provider's sign in page
CALLBACK_PATH = "/api/auth/callback"
HTTP_TIMEOUT = 10.0
# Keys are refetched at most this often, so a provider's key rotation is picked up
# without fetching the key set on every sign in.
JWKS_SECONDS = 3600
MIN_SECRET_BYTES = 32


class AuthError(Exception):
    """Sign in failed or is not allowed. `status` is the HTTP answer."""

    def __init__(self, message: str, status: int = 401) -> None:
        super().__init__(message)
        self.status = status


@dataclass(frozen=True)
class Principal:
    """The person a request is for, and the companies they may see and change."""

    subject: str | None  # None for the local single user
    name: str
    email: str
    platform_admin: bool
    roles: dict[str, Role] = field(default_factory=dict)

    def can_read(self, slug: str) -> bool:
        return self.platform_admin or slug in self.roles

    def can_write(self, slug: str) -> bool:
        return self.platform_admin or self.roles.get(slug) == "admin"

    @property
    def can_manage(self) -> bool:
        """Add companies. Only a platform admin, as a new company is outside every role."""
        return self.platform_admin


LOCAL_USER = Principal(subject=None, name="Local user", email="", platform_admin=True)


def roles_from_groups(groups: list[str], prefix: str) -> tuple[bool, dict[str, Role]]:
    """(platform admin, {slug: role}) from group names; anything else is ignored."""
    platform = False
    roles: dict[str, Role] = {}
    for group in groups:
        if not group.startswith(prefix):
            continue
        rest = group[len(prefix) :]
        if rest == "platform-admin":
            platform = True
            continue
        kind, _, slug = rest.partition("-")
        if kind not in ("admin", "viewer") or not COMPANY_SLUG.match(slug):
            continue
        # admin wins over viewer when someone is in both groups
        if kind == "admin" or roles.get(slug) != "admin":
            roles[slug] = "admin" if kind == "admin" else "viewer"
    return platform, roles


# ---------------------------------------------------------------------- signed cookies
def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def sign(payload: dict[str, object], secret: bytes, seconds: int) -> str:
    """A tamper proof cookie value carrying `payload` until it expires."""
    body = _b64(json.dumps({**payload, "exp": int(time.time()) + seconds}).encode("utf-8"))
    mac = _b64(hmac.new(secret, body.encode("ascii"), hashlib.sha256).digest())
    return f"{body}.{mac}"


def unsign(value: str | None, secret: bytes) -> dict[str, object] | None:
    """The payload, or None when the value is missing, altered or expired."""
    if not value or value.count(".") != 1:
        return None
    body, mac = value.split(".")
    expected = _b64(hmac.new(secret, body.encode("ascii"), hashlib.sha256).digest())
    if not hmac.compare_digest(mac, expected):
        return None
    try:
        payload = json.loads(_unb64(body))
    except (ValueError, UnicodeDecodeError):
        return None
    if not isinstance(payload, dict) or not isinstance(payload.get("exp"), int):
        return None
    return payload if payload["exp"] > time.time() else None


# ---------------------------------------------------------------------- settings
@dataclass(frozen=True)
class AuthSettings:
    mode: Literal["off", "oidc"] = "off"
    issuer: str = ""
    client_id: str = ""
    client_secret: str = ""
    # The page's address, where the provider sends people back to.
    console_url: str = "http://127.0.0.1:5173"
    groups_claim: str = "groups"
    role_prefix: str = "cti-"
    scopes: str = "openid profile email"
    session_hours: int = 8
    session_secret: bytes = b""

    @property
    def enabled(self) -> bool:
        return self.mode == "oidc"

    @property
    def redirect_uri(self) -> str:
        return self.console_url.rstrip("/") + CALLBACK_PATH

    @property
    def secure_cookies(self) -> bool:
        return urlsplit(self.console_url).scheme == "https"

    @classmethod
    def from_env(cls) -> AuthSettings:
        mode = os.environ.get("CTI_AUTH", "off").strip().lower()
        if mode not in ("off", "oidc"):
            raise ValueError(f"CTI_AUTH={mode!r}: use off or oidc")
        if mode == "off":
            return cls()
        needed = ("CTI_OIDC_ISSUER", "CTI_OIDC_CLIENT_ID", "CTI_SESSION_SECRET")
        missing = [name for name in needed if not os.environ.get(name)]
        if missing:
            raise ValueError(f"CTI_AUTH=oidc needs {', '.join(missing)}")
        secret = os.environ["CTI_SESSION_SECRET"].encode("utf-8")
        if len(secret) < MIN_SECRET_BYTES:
            raise ValueError(f"CTI_SESSION_SECRET must be at least {MIN_SECRET_BYTES} characters")
        return cls(
            mode="oidc",
            issuer=os.environ["CTI_OIDC_ISSUER"].rstrip("/"),
            client_id=os.environ["CTI_OIDC_CLIENT_ID"],
            client_secret=os.environ.get("CTI_OIDC_CLIENT_SECRET", ""),
            console_url=os.environ.get("CTI_CONSOLE_URL", cls.console_url),
            groups_claim=os.environ.get("CTI_OIDC_GROUPS_CLAIM", cls.groups_claim),
            role_prefix=os.environ.get("CTI_OIDC_ROLE_PREFIX", cls.role_prefix),
            scopes=os.environ.get("CTI_OIDC_SCOPES", cls.scopes),
            session_hours=int(os.environ.get("CTI_SESSION_HOURS", cls.session_hours)),
            session_secret=secret,
        )


# ---------------------------------------------------------------------- the flow
def _verifier_challenge() -> tuple[str, str]:
    verifier = secrets.token_urlsafe(64)
    challenge = _b64(hashlib.sha256(verifier.encode("ascii")).digest())
    return verifier, challenge


class OidcClient:
    """The provider side of sign in. `http` is replaceable so tests need no provider."""

    def __init__(self, settings: AuthSettings, http: httpx.Client | None = None) -> None:
        self.settings = settings
        self.http = http or httpx.Client(timeout=HTTP_TIMEOUT)
        self._discovery: dict[str, object] | None = None
        self._jwks: dict[str, object] | None = None
        self._jwks_at = 0.0

    def discovery(self) -> dict[str, object]:
        if self._discovery is None:
            url = f"{self.settings.issuer}/.well-known/openid-configuration"
            found = self._get_json(url)
            if found.get("issuer") != self.settings.issuer:
                raise AuthError("The provider's discovery names a different issuer", 502)
            self._discovery = found
        return self._discovery

    def _get_json(self, url: str) -> dict[str, object]:
        try:
            response = self.http.get(url)
            response.raise_for_status()
            body = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise AuthError(f"Could not reach the identity provider ({url})", 502) from exc
        if not isinstance(body, dict):
            raise AuthError(f"The identity provider answered oddly at {url}", 502)
        return body

    def _endpoint(self, name: str) -> str:
        value = self.discovery().get(name)
        if not isinstance(value, str) or not value.startswith("https://"):
            raise AuthError(f"The provider has no https {name}", 502)
        return value

    def start(self) -> tuple[str, str]:
        """(URL of the provider's sign in page, value of the short lived login cookie)."""
        state, nonce = secrets.token_urlsafe(24), secrets.token_urlsafe(24)
        verifier, challenge = _verifier_challenge()
        query = urlencode(
            {
                "response_type": "code",
                "client_id": self.settings.client_id,
                "redirect_uri": self.settings.redirect_uri,
                "scope": self.settings.scopes,
                "state": state,
                "nonce": nonce,
                "code_challenge": challenge,
                "code_challenge_method": "S256",
            }
        )
        login = sign(
            {"state": state, "nonce": nonce, "verifier": verifier},
            self.settings.session_secret,
            LOGIN_SECONDS,
        )
        return f"{self._endpoint('authorization_endpoint')}?{query}", login

    def finish(self, code: str, state: str, login_cookie: str | None) -> dict[str, object]:
        """Trade the code for an ID token, check it, and return the session to keep."""
        login = unsign(login_cookie, self.settings.session_secret)
        if login is None or not hmac.compare_digest(str(login.get("state")), state):
            raise AuthError("Sign in expired or did not start here. Sign in again.", 400)
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.settings.redirect_uri,
            "client_id": self.settings.client_id,
            "code_verifier": str(login["verifier"]),
        }
        # Entra ID and Cognito both take a confidential client's secret as HTTP Basic.
        auth = (
            (self.settings.client_id, self.settings.client_secret)
            if self.settings.client_secret
            else None
        )
        try:
            response = self.http.post(self._endpoint("token_endpoint"), data=data, auth=auth)
            response.raise_for_status()
            tokens = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise AuthError("The identity provider refused the sign in", 502) from exc
        id_token = tokens.get("id_token") if isinstance(tokens, dict) else None
        if not isinstance(id_token, str):
            raise AuthError("The identity provider sent no ID token", 502)
        claims = self.verify(id_token)
        if not hmac.compare_digest(str(claims.get("nonce", "")), str(login["nonce"])):
            raise AuthError("The ID token does not belong to this sign in", 400)
        return self.session_from(claims)

    def _keys(self, refresh: bool = False) -> dict[str, object]:
        stale = time.time() - self._jwks_at > JWKS_SECONDS
        if self._jwks is None or stale or refresh:
            self._jwks = self._get_json(self._endpoint("jwks_uri"))
            self._jwks_at = time.time()
        return self._jwks

    def _key_for(self, kid: str) -> jwt.PyJWK:
        for refresh in (False, True):  # a new key may have been published since
            keys = self._keys(refresh).get("keys")
            for raw in keys if isinstance(keys, list) else []:
                if isinstance(raw, dict) and raw.get("kid") == kid:
                    return jwt.PyJWK(raw)
        raise AuthError("The ID token was signed with an unknown key", 401)

    def verify(self, id_token: str) -> dict[str, object]:
        try:
            header = jwt.get_unverified_header(id_token)
            key = self._key_for(str(header.get("kid", "")))
            claims = jwt.decode(
                id_token,
                key=key,
                algorithms=["RS256"],
                audience=self.settings.client_id,
                issuer=self.settings.issuer,
                options={"require": ["exp", "iat", "sub", "aud", "iss"]},
                leeway=60,
            )
        except jwt.PyJWTError as exc:
            raise AuthError(f"The ID token is not valid: {exc}", 401) from exc
        return claims

    def session_from(self, claims: dict[str, object]) -> dict[str, object]:
        """What the cookie keeps: who, and only the groups that mean something here."""
        groups = claims.get(self.settings.groups_claim, [])
        if isinstance(groups, str):
            groups = [groups]
        kept = sorted(
            g for g in groups if isinstance(g, str) and g.startswith(self.settings.role_prefix)
        )
        name = claims.get("name") or claims.get("preferred_username") or claims.get("email")
        return {
            "sub": str(claims["sub"]),
            "name": str(name or claims["sub"]),
            "email": str(claims.get("email") or ""),
            "groups": kept,
        }

    def logout_url(self) -> str | None:
        """The provider's sign out page, when it publishes one."""
        try:
            url = self.discovery().get("end_session_endpoint")
        except AuthError:
            return None
        if not isinstance(url, str) or not url.startswith("https://"):
            return None
        query = urlencode(
            {
                "client_id": self.settings.client_id,
                "post_logout_redirect_uri": self.settings.console_url,
            }
        )
        return f"{url}?{query}"


def principal_from(session: dict[str, object] | None, settings: AuthSettings) -> Principal | None:
    if session is None or not isinstance(session.get("sub"), str):
        return None
    raw_groups = session.get("groups")
    groups = [g for g in raw_groups if isinstance(g, str)] if isinstance(raw_groups, list) else []
    platform, roles = roles_from_groups(groups, settings.role_prefix)
    return Principal(
        subject=str(session["sub"]),
        name=str(session.get("name") or session["sub"]),
        email=str(session.get("email") or ""),
        platform_admin=platform,
        roles=roles,
    )
