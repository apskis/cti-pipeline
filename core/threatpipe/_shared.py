"""
Shared infrastructure for cti-feeds MCP sub-servers.

Provides Key Vault credential resolution, HTTP helpers, and logging setup.
Every sub-server imports from here rather than duplicating the plumbing.
"""

import logging
import os
import sys
from typing import Any, Optional

import httpx

# ---------------------------------------------------------------------------
# Logging — stderr only. stdout is the MCP JSON-RPC transport.
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    stream=sys.stderr,
    format="%(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("cti-feeds")

# ---------------------------------------------------------------------------
# Key Vault secret mapping (env name → vault secret name)
# ---------------------------------------------------------------------------

SECRET_MAP = {
    "SHODAN_API_KEY":     "shodan-api-key",
    "NVD_API_KEY":        "nvd-api-key",
    "INTEL471_EMAIL":     "intel471-email",
    "INTEL471_API_KEY":   "intel471-api-key",
    "CLAROTY_API_TOKEN":  "claroty-api-token",
    "CLAROTY_API_HOST":   "claroty-api-host",
    "RAPID7_API_KEY":     "rapid7-api-key",
    "RAPID7_REGION":      "rapid7-region",
    "RAPIDAPI_ICS_KEY":   "rapidapi-ics-key",
    "RAPIDAPI_ICS_HOST":  "rapidapi-ics-host",
    "HISAC_TAXII_URL":    "hisac-taxii-url",
    "HISAC_USERNAME":     "hisac-username",
    "HISAC_PASSWORD":     "hisac-password",
    "TQ_URL":             "threatq-url",
    "TQ_CLIENT_ID":       "threatq-client-id",
    "TQ_CLIENT_SECRET":   "threatq-client-secret",
}

_SECRETS: dict[str, str] = {}

TIMEOUT = httpx.Timeout(30.0, connect=10.0)
MAX_ITEMS = 100


def _load_secrets() -> None:
    """Populate _SECRETS from Azure Key Vault at startup. Never raises."""
    vault_url = os.environ.get("KEY_VAULT_URL", "").strip()
    if not vault_url:
        log.info("KEY_VAULT_URL not set; using environment variables only")
        return
    try:
        from azure.identity import DefaultAzureCredential
        from azure.keyvault.secrets import SecretClient
        from azure.core.exceptions import ResourceNotFoundError, HttpResponseError

        client = SecretClient(vault_url=vault_url,
                              credential=DefaultAzureCredential())
        found, missing = 0, []
        for env_name, secret_name in SECRET_MAP.items():
            try:
                _SECRETS[env_name] = client.get_secret(secret_name).value
                found += 1
            except ResourceNotFoundError:
                missing.append(env_name)
                log.debug("secret not found: %s", secret_name)
            except HttpResponseError as e:
                log.warning("cannot read %s: HTTP %s", secret_name,
                            getattr(e, "status_code", "?"))
                missing.append(env_name)
        log.info("key vault: loaded %d of %d secrets", found, len(SECRET_MAP))
        if missing:
            log.info("not found in vault: %s", ", ".join(missing))
    except Exception as e:
        log.warning("key vault unavailable (%s); "
                    "falling back to environment variables",
                    type(e).__name__)


_load_secrets()


# ---------------------------------------------------------------------------
# Credential helpers
# ---------------------------------------------------------------------------

def _env(name: str) -> Optional[str]:
    val = os.environ.get(name) or _SECRETS.get(name)
    return val.strip() if val else None


def _need(*names: str) -> Optional[dict]:
    """Return an error dict if any required env var is missing."""
    missing = [n for n in names if not _env(n)]
    if missing:
        return {"error": f"missing credentials: {', '.join(missing)}"}
    return None


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

def _get(url: str, **kwargs) -> Any:
    with httpx.Client(timeout=TIMEOUT, follow_redirects=True) as c:
        r = c.get(url, **kwargs)
        r.raise_for_status()
        return r.json()


def _post(url: str, **kwargs) -> Any:
    with httpx.Client(timeout=TIMEOUT, follow_redirects=True) as c:
        r = c.post(url, **kwargs)
        r.raise_for_status()
        return r.json()


def _safe(fn, *args, **kwargs) -> Any:
    """Turn transport errors into readable results rather than tool crashes."""
    try:
        return fn(*args, **kwargs)
    except httpx.HTTPStatusError as e:
        return {
            "error": f"HTTP {e.response.status_code}",
            "detail": e.response.text[:500],
        }
    except httpx.HTTPError as e:
        return {"error": "request failed", "detail": str(e)[:300]}
