"""
Quick connectivity test for all cti-feeds sub-servers.

Run:  uv run test_connections.py

Requires KEY_VAULT_URL set (or credentials in env) and az login done.
Tests each vendor with a minimal, low-cost API call and reports pass/fail.
"""

import sys
import os

# Ensure _shared.py is importable from this directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from _shared import _env, _get, _safe, log


def test_shodan():
    """Minimal Shodan test: resolve DNS for a known IP."""
    key = _env("SHODAN_API_KEY")
    if not key:
        return "SKIP", "no credential"
    data = _safe(_get, "https://api.shodan.io/dns/resolve",
                 params={"hostnames": "google.com", "key": key})
    if "error" in data:
        return "FAIL", data.get("detail", data.get("error"))
    return "PASS", f"resolved google.com -> {data.get('google.com')}"


def test_nvd():
    """NVD test: fetch a known CVE (no key required, key just raises rate limit)."""
    headers = {"apiKey": _env("NVD_API_KEY")} if _env("NVD_API_KEY") else {}
    data = _safe(_get, "https://services.nvd.nist.gov/rest/json/cves/2.0",
                 params={"cveId": "CVE-2024-3400"}, headers=headers)
    if "error" in data:
        return "FAIL", data.get("detail", data.get("error"))
    total = data.get("totalResults", 0)
    return ("PASS" if total > 0 else "FAIL",
            f"CVE-2024-3400 found, totalResults={total}")


def test_intel471():
    """Intel 471 test: auth check via indicators endpoint with dummy query."""
    email = _env("INTEL471_EMAIL")
    key = _env("INTEL471_API_KEY")
    if not email or not key:
        return "SKIP", "no credential"
    data = _safe(_get, "https://api.intel471.com/v1/indicators",
                 params={"indicator": "8.8.8.8", "count": 1},
                 auth=(email, key))
    if "error" in data:
        detail = data.get("detail", data.get("error", ""))
        if "401" in str(detail) or "403" in str(detail):
            return "FAIL", f"auth rejected: {detail[:200]}"
        return "WARN", f"request issue: {detail[:200]}"
    return "PASS", f"indicatorTotalCount={data.get('indicatorTotalCount', '?')}"


def test_claroty():
    """Claroty xDome test: fetch one device."""
    token = _env("CLAROTY_API_TOKEN")
    if not token:
        return "SKIP", "no credential"
    host = _env("CLAROTY_API_HOST") or "https://api.claroty.com"
    import httpx
    from _shared import TIMEOUT
    try:
        with httpx.Client(timeout=TIMEOUT, follow_redirects=True) as c:
            r = c.post(f"{host}/api/v1/devices",
                       headers={"Authorization": f"Bearer {token}",
                                "Content-Type": "application/json"},
                       json={"limit": 1, "offset": 0,
                             "fields": ["asset_id", "device_name", "risk_score"]})
            if r.status_code == 200:
                return "PASS", f"HTTP 200, got device data"
            return "FAIL", f"HTTP {r.status_code}: {r.text[:200]}"
    except Exception as e:
        return "FAIL", str(e)[:200]


def test_rapid7():
    """Rapid7 InsightVM test: simple asset query."""
    key = _env("RAPID7_API_KEY")
    if not key:
        return "SKIP", "no credential"
    region = _env("RAPID7_REGION") or "us"
    import httpx
    from _shared import TIMEOUT
    try:
        with httpx.Client(timeout=TIMEOUT) as c:
            r = c.post(f"https://{region}.api.insight.rapid7.com/vm/v4/integration/assets",
                       headers={"X-Api-Key": key, "Content-Type": "application/json"},
                       json={"size": 1})
            if r.status_code == 200:
                return "PASS", "HTTP 200, asset query works"
            return "FAIL", f"HTTP {r.status_code}: {r.text[:200]}"
    except Exception as e:
        return "FAIL", str(e)[:200]


def test_ics():
    """RapidAPI ICS test: hit the vendors endpoint."""
    key = _env("RAPIDAPI_ICS_KEY")
    host = _env("RAPIDAPI_ICS_HOST")
    if not key or not host:
        return "SKIP", "no credential"
    import httpx
    from _shared import TIMEOUT
    headers = {"X-RapidAPI-Key": key, "X-RapidAPI-Host": host}
    try:
        with httpx.Client(timeout=TIMEOUT, follow_redirects=True) as c:
            r = c.get(f"https://{host}/vendors", headers=headers)
            if r.status_code == 200:
                vendors = r.json().get("result", [])
                return "PASS", f"{len(vendors)} ICS vendors available"
            if r.status_code in (401, 403):
                return "FAIL", f"HTTP {r.status_code}: auth rejected"
            return "WARN", f"HTTP {r.status_code}: {r.text[:150]}"
    except Exception as e:
        return "FAIL", str(e)[:200]


def test_hisac():
    """Health-ISAC via ThreatQuotient: authenticate and query indicators."""
    tq_url = _env("TQ_URL")
    cid = _env("TQ_CLIENT_ID")
    csec = _env("TQ_CLIENT_SECRET")
    if not tq_url or not cid or not csec:
        return "SKIP", "no TQ credentials"
    import httpx
    from _shared import TIMEOUT
    try:
        base = tq_url.rstrip("/")
        c = httpx.Client(timeout=TIMEOUT, follow_redirects=True)
        r = c.post(f"{base}/api/token", auth=(cid, csec),
                   data={"grant_type": "client_credentials"})
        if r.status_code != 200:
            return "FAIL", f"token request HTTP {r.status_code}: {r.text[:150]}"
        token = r.json().get("access_token")
        headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
        r2 = c.get(f"{base}/api/indicators", headers=headers, params={"limit": 1})
        if r2.status_code == 200:
            total = r2.json().get("total", "?")
            return "PASS", f"TQ connected, {total} indicators available"
        return "FAIL", f"indicators query HTTP {r2.status_code}"
    except Exception as e:
        return "FAIL", str(e)[:200]


TESTS = [
    ("Shodan", test_shodan),
    ("NVD", test_nvd),
    ("Intel 471", test_intel471),
    ("Claroty xDome", test_claroty),
    ("Rapid7 InsightVM", test_rapid7),
    ("RapidAPI ICS", test_ics),
    ("Health-ISAC", test_hisac),
]


if __name__ == "__main__":
    print("=" * 60)
    print("cti-feeds connection test")
    print("=" * 60)
    print()

    results = []
    for name, fn in TESTS:
        try:
            status, detail = fn()
        except Exception as e:
            status, detail = "ERROR", str(e)[:200]
        results.append((name, status, detail))
        icon = {"PASS": "+", "FAIL": "X", "SKIP": "-", "WARN": "!", "ERROR": "X"}
        print(f"  [{icon.get(status, '?')}] {name:20s} {status:5s}  {detail}")

    print()
    print("-" * 60)
    passed = sum(1 for _, s, _ in results if s == "PASS")
    failed = sum(1 for _, s, _ in results if s in ("FAIL", "ERROR"))
    skipped = sum(1 for _, s, _ in results if s == "SKIP")
    print(f"  {passed} passed, {failed} failed, {skipped} skipped")
    print()

    sys.exit(1 if failed else 0)
