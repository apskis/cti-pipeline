"""
cti-feeds MCP server

Exposes commercial and open threat intelligence APIs as MCP tools so they can be
queried directly from Claude Desktop.

Design rules followed throughout:
  1. Every tool returns TRIMMED output. Raw vendor JSON blows past Claude's
     25,000 token MCP output cap almost immediately. Each _shape_* function
     keeps only the fields worth reasoning over.
  2. Docstrings are the tool selection prompt. They describe when to use the
     tool in analyst language, not API language.
  3. Credentials resolve from Azure Key Vault at startup, with environment
     variable override. Never hardcode, never log values.
  4. Missing credentials degrade gracefully: the tool reports what is missing
     instead of raising an opaque stack trace into the transport.
"""

import logging
import os
import sys
from typing import Any, Optional

import httpx
from fastmcp import FastMCP

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

mcp = FastMCP("cti-feeds")

TIMEOUT = httpx.Timeout(30.0, connect=10.0)
MAX_ITEMS = 25  # hard cap on list results returned to the model


# ---------------------------------------------------------------------------
# helpers
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


def _get(url: str, **kwargs) -> Any:
    with httpx.Client(timeout=TIMEOUT) as c:
        r = c.get(url, **kwargs)
        r.raise_for_status()
        return r.json()


def _post(url: str, **kwargs) -> Any:
    with httpx.Client(timeout=TIMEOUT) as c:
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


# ---------------------------------------------------------------------------
# Shodan
# ---------------------------------------------------------------------------

def _shape_shodan_host(d: dict) -> dict:
    return {
        "ip": d.get("ip_str"),
        "org": d.get("org"),
        "isp": d.get("isp"),
        "asn": d.get("asn"),
        "country": d.get("country_name"),
        "hostnames": d.get("hostnames", [])[:10],
        "ports": d.get("ports", []),
        "vulns": list(d.get("vulns", []))[:40],
        "tags": d.get("tags", []),
        "last_update": d.get("last_update"),
        "services": [
            {
                "port": s.get("port"),
                "transport": s.get("transport"),
                "product": s.get("product"),
                "version": s.get("version"),
                "cpe": s.get("cpe23") or s.get("cpe"),
                # banners are the single biggest source of token bloat
                "banner_excerpt": (s.get("data") or "")[:200],
            }
            for s in d.get("data", [])[:15]
        ],
    }


@mcp.tool()
def shodan_host(ip: str) -> dict:
    """Look up everything Shodan knows about a single IP: open ports, running
    services and versions, banners, CVEs, ASN and hosting org. Use this when
    triaging a suspicious external IP or profiling attacker infrastructure."""
    if err := _need("SHODAN_API_KEY"):
        return err
    data = _safe(_get, f"https://api.shodan.io/shodan/host/{ip}",
                 params={"key": _env("SHODAN_API_KEY"), "minify": False})
    return data if "error" in data else _shape_shodan_host(data)


@mcp.tool()
def shodan_search(query: str, limit: int = 10) -> dict:
    """Search Shodan's index with its query syntax (e.g.
    'ssl.cert.subject.CN:example.com', 'product:Jenkins country:CN').
    Use this to hunt for exposed assets, look for infrastructure matching a
    threat actor pattern, or find hosts sharing a certificate or favicon."""
    if err := _need("SHODAN_API_KEY"):
        return err
    data = _safe(_get, "https://api.shodan.io/shodan/host/search",
                 params={"key": _env("SHODAN_API_KEY"), "query": query})
    if "error" in data:
        return data
    return {
        "total": data.get("total"),
        "returned": min(limit, MAX_ITEMS),
        "matches": [
            {
                "ip": m.get("ip_str"),
                "port": m.get("port"),
                "org": m.get("org"),
                "country": (m.get("location") or {}).get("country_name"),
                "product": m.get("product"),
                "hostnames": m.get("hostnames", [])[:5],
                "banner_excerpt": (m.get("data") or "")[:200],
            }
            for m in data.get("matches", [])[: min(limit, MAX_ITEMS)]
        ],
    }


# ---------------------------------------------------------------------------
# NVD
# ---------------------------------------------------------------------------

def _shape_cve(item: dict) -> dict:
    cve = item.get("cve", item)
    metrics = cve.get("metrics", {})
    cvss = None
    for key in ("cvssMetricV31", "cvssMetricV30", "cvssMetricV2"):
        if metrics.get(key):
            m = metrics[key][0].get("cvssData", {})
            cvss = {
                "version": m.get("version"),
                "score": m.get("baseScore"),
                "severity": m.get("baseSeverity"),
                "vector": m.get("vectorString"),
            }
            break
    desc = next(
        (d["value"] for d in cve.get("descriptions", []) if d.get("lang") == "en"),
        "",
    )
    return {
        "id": cve.get("id"),
        "published": cve.get("published"),
        "modified": cve.get("lastModified"),
        "status": cve.get("vulnStatus"),
        "cvss": cvss,
        "description": desc[:800],
        "cwe": [
            d["value"]
            for w in cve.get("weaknesses", [])
            for d in w.get("description", [])
            if d.get("value", "").startswith("CWE")
        ][:5],
        "references": [r.get("url") for r in cve.get("references", [])][:8],
    }


@mcp.tool()
def nvd_cve(cve_id: str) -> dict:
    """Get authoritative NVD detail for one CVE: CVSS vector and score, CWE
    mapping, description, and references. Use when you need the canonical
    severity and affected-product facts for a specific CVE."""
    params = {"cveId": cve_id}
    headers = {"apiKey": _env("NVD_API_KEY")} if _env("NVD_API_KEY") else {}
    data = _safe(_get, "https://services.nvd.nist.gov/rest/json/cves/2.0",
                 params=params, headers=headers)
    if "error" in data:
        return data
    items = data.get("vulnerabilities", [])
    return _shape_cve(items[0]) if items else {"error": f"{cve_id} not found"}


@mcp.tool()
def nvd_search(keyword: str, last_days: int = 0, limit: int = 10) -> dict:
    """Search NVD by keyword (vendor, product, or phrase), optionally limited
    to CVEs modified in the last N days. Use for 'what is new for <product>'
    sweeps or building a vulnerability picture for a technology in the estate."""
    params: dict = {"keywordSearch": keyword, "resultsPerPage": min(limit, MAX_ITEMS)}
    if last_days:
        from datetime import datetime, timedelta, timezone
        now = datetime.now(timezone.utc)
        params["lastModStartDate"] = (now - timedelta(days=last_days)).isoformat()
        params["lastModEndDate"] = now.isoformat()
    headers = {"apiKey": _env("NVD_API_KEY")} if _env("NVD_API_KEY") else {}
    data = _safe(_get, "https://services.nvd.nist.gov/rest/json/cves/2.0",
                 params=params, headers=headers)
    if "error" in data:
        return data
    return {
        "total": data.get("totalResults"),
        "results": [_shape_cve(v) for v in data.get("vulnerabilities", [])[:limit]],
    }


# ---------------------------------------------------------------------------
# Intel 471  (Titan API, HTTP Basic: email + API key)
# ---------------------------------------------------------------------------

INTEL471_BASE = "https://api.intel471.com/v1"


def _i471_auth():
    return (_env("INTEL471_EMAIL"), _env("INTEL471_API_KEY"))


@mcp.tool()
def intel471_search_indicators(indicator: str, limit: int = 10) -> dict:
    """Look up an IP, domain, URL, or file hash in Intel 471's malware
    intelligence. Returns confidence, associated malware family, threat type,
    and validity window. Use this to establish whether an observable is tied to
    known criminal infrastructure."""
    if err := _need("INTEL471_EMAIL", "INTEL471_API_KEY"):
        return err
    data = _safe(_get, f"{INTEL471_BASE}/indicators",
                 params={"indicator": indicator, "count": min(limit, MAX_ITEMS)},
                 auth=_i471_auth())
    if "error" in data:
        return data
    out = []
    for rec in (data.get("indicators") or [])[:limit]:
        d = rec.get("data", {})
        out.append({
            "value": (d.get("indicator_data") or {}).get("value"),
            "type": d.get("indicator_type"),
            "confidence": d.get("confidence"),
            "threat_type": (d.get("threat") or {}).get("type"),
            "malware_family": (d.get("threat") or {}).get("data", {}).get("family"),
            "valid_from": d.get("valid_from"),
            "valid_until": d.get("valid_until"),
            "context": (d.get("context") or {}).get("description", "")[:300],
        })
    return {"total": data.get("indicatorTotalCount"), "indicators": out}


@mcp.tool()
def intel471_reports(query: str, limit: int = 5) -> dict:
    """Free text search across Intel 471 finished intelligence reports
    (actor profiles, breach alerts, underground activity). Returns titles,
    dates, and summaries rather than full report bodies. Use when you need
    adversary context or want to check coverage on a campaign or actor."""
    if err := _need("INTEL471_EMAIL", "INTEL471_API_KEY"):
        return err
    data = _safe(_get, f"{INTEL471_BASE}/reports",
                 params={"report": query, "count": min(limit, MAX_ITEMS)},
                 auth=_i471_auth())
    if "error" in data:
        return data
    return {
        "total": data.get("reportTotalCount"),
        "reports": [
            {
                "uid": r.get("uid"),
                "title": r.get("subject"),
                "created": r.get("created"),
                "classification": (r.get("classification") or {}).get("intelRequirements"),
                "summary": (r.get("executiveSummary") or "")[:600],
                "actors": [a.get("handle") for a in (r.get("actorSubjectOfReport") or [])][:10],
                "entities": [e.get("value") for e in (r.get("entities") or [])][:20],
            }
            for r in (data.get("reports") or [])[:limit]
        ],
    }


@mcp.tool()
def intel471_alerts(limit: int = 20) -> dict:
    """Retrieve recent Intel 471 Watcher alerts for the tenant's monitored
    assets, actors, and keywords. Use for a daily sweep of what Intel 471
    flagged against our watchlists."""
    if err := _need("INTEL471_EMAIL", "INTEL471_API_KEY"):
        return err
    data = _safe(_get, f"{INTEL471_BASE}/alerts",
                 params={"count": min(limit, MAX_ITEMS)}, auth=_i471_auth())
    if "error" in data:
        return data
    return {
        "alerts": [
            {
                "uid": a.get("uid"),
                "created": a.get("foundTime"),
                "watcher": (a.get("watcherGroup") or {}).get("name"),
                "type": a.get("entityType"),
                "title": (a.get("entity") or {}).get("data", {}).get("subject")
                         or (a.get("entity") or {}).get("uid"),
            }
            for a in (data.get("alerts") or [])[:limit]
        ]
    }


# ---------------------------------------------------------------------------
# Claroty xDome  (Bearer token, POST endpoints with JSON body)
# ---------------------------------------------------------------------------

def _claroty_base() -> str:
    return _env("CLAROTY_API_HOST") or "https://api.claroty.com"


def _claroty_headers() -> dict:
    return {
        "Authorization": f"Bearer {_env('CLAROTY_API_TOKEN')}",
        "Content-Type": "application/json",
    }


@mcp.tool()
def claroty_devices(search: str = "", limit: int = 20) -> dict:
    """Query the Claroty xDome OT/IoT device inventory. Optionally filter by a
    free text term (hostname, IP, vendor, model). Returns device identity,
    network location, purdue level, and risk score. Use when scoping which
    cyber-physical assets an advisory or campaign actually touches."""
    if err := _need("CLAROTY_API_TOKEN"):
        return err
    body: dict = {"limit": min(limit, MAX_ITEMS), "offset": 0, "include_count": True}
    if search:
        body["filter_by"] = {"search": search}
    data = _safe(_post, f"{_claroty_base()}/api/v1/devices",
                 headers=_claroty_headers(), json=body)
    if "error" in data:
        return data
    return {
        "count": data.get("count"),
        "devices": [
            {
                "id": d.get("id"),
                "name": d.get("device_name") or d.get("hostname"),
                "ip": d.get("ip_list") or d.get("ip"),
                "mac": d.get("mac_list"),
                "vendor": d.get("vendor"),
                "model": d.get("model"),
                "os": d.get("os_category") or d.get("operating_system"),
                "type": d.get("device_type") or d.get("device_category"),
                "site": d.get("site_name"),
                "purdue": d.get("purdue_level"),
                "risk": d.get("risk_score"),
                "last_seen": d.get("last_seen"),
            }
            for d in (data.get("devices") or [])[:limit]
        ],
    }


@mcp.tool()
def claroty_vulnerabilities(cve_id: str = "", limit: int = 20) -> dict:
    """Query vulnerabilities Claroty xDome has matched against the OT/IoT
    estate, optionally narrowed to one CVE. Returns affected device counts and
    severity. Use to answer 'are we exposed to this ICS advisory' with real
    asset counts rather than a guess."""
    if err := _need("CLAROTY_API_TOKEN"):
        return err
    body: dict = {"limit": min(limit, MAX_ITEMS), "offset": 0, "include_count": True}
    if cve_id:
        body["filter_by"] = {"cve_id": [cve_id]}
    data = _safe(_post, f"{_claroty_base()}/api/v1/vulnerabilities",
                 headers=_claroty_headers(), json=body)
    if "error" in data:
        return data
    return {
        "count": data.get("count"),
        "vulnerabilities": [
            {
                "cve": v.get("cve_id"),
                "severity": v.get("cvss_v3_severity") or v.get("severity"),
                "score": v.get("cvss_v3_score") or v.get("cvss_score"),
                "affected_devices": v.get("num_of_devices") or v.get("affected_devices"),
                "vendor": v.get("vendor"),
                "published": v.get("published_date"),
                "description": (v.get("description") or "")[:400],
            }
            for v in (data.get("vulnerabilities") or [])[:limit]
        ],
    }


# ---------------------------------------------------------------------------
# Rapid7 InsightVM  (Insight platform cloud API, X-Api-Key)
# ---------------------------------------------------------------------------

def _rapid7_base() -> str:
    region = _env("RAPID7_REGION") or "us"
    return f"https://{region}.api.insight.rapid7.com"


@mcp.tool()
def rapid7_assets_by_cve(cve_id: str, limit: int = 20) -> dict:
    """Find assets in InsightVM affected by a specific CVE. Returns hostname,
    IP, OS, and risk score per asset. Use this to turn a new advisory into a
    concrete exposure count for the IT estate."""
    if err := _need("RAPID7_API_KEY"):
        return err
    body = {
        "asset": f"vulnerability.cve == '{cve_id}'",
        "size": min(limit, MAX_ITEMS),
    }
    data = _safe(_post, f"{_rapid7_base()}/vm/v4/integration/assets",
                 headers={"X-Api-Key": _env("RAPID7_API_KEY"),
                          "Content-Type": "application/json"},
                 json=body)
    if "error" in data:
        return data
    return {
        "total": (data.get("metadata") or {}).get("totalData"),
        "assets": [
            {
                "id": a.get("id"),
                "hostname": a.get("host_name"),
                "ip": a.get("ip"),
                "os": (a.get("os_description") or a.get("os_name")),
                "risk": a.get("risk_score"),
                "critical_vulns": a.get("critical_vulnerabilities"),
                "last_assessed": a.get("last_assessed_for_vulnerabilities"),
                "tags": [t.get("name") for t in (a.get("tags") or [])][:8],
            }
            for a in (data.get("data") or [])[:limit]
        ],
    }


# ---------------------------------------------------------------------------
# RapidAPI ICS advisory feed
# ---------------------------------------------------------------------------

@mcp.tool()
def ics_advisories(path: str = "advisories", params: Optional[dict] = None) -> dict:
    """Query the RapidAPI ICS advisory service. 'path' is the endpoint path
    after the host root. Use for CISA ICS advisory lookups and OT vulnerability
    context that complements Claroty's asset view."""
    if err := _need("RAPIDAPI_ICS_KEY", "RAPIDAPI_ICS_HOST"):
        return err
    host = _env("RAPIDAPI_ICS_HOST")
    data = _safe(_get, f"https://{host}/{path.lstrip('/')}",
                 headers={"X-RapidAPI-Key": _env("RAPIDAPI_ICS_KEY"),
                          "X-RapidAPI-Host": host},
                 params=params or {})
    if isinstance(data, list):
        return {"count": len(data), "results": data[:MAX_ITEMS]}
    return data


# ---------------------------------------------------------------------------
# Health-ISAC  (MISP-compatible sharing instance)
# ---------------------------------------------------------------------------

@mcp.tool()
def hisac_search(value: str, limit: int = 20) -> dict:
    """Search the Health-ISAC sharing instance for an indicator (IP, domain,
    hash, email). Returns matching attributes with the event context and TLP
    marking. Use to check whether a sector peer has already reported an
    observable before treating it as novel."""
    if err := _need("HISAC_API_KEY", "HISAC_BASE_URL"):
        return err
    base = _env("HISAC_BASE_URL").rstrip("/")
    body = {"returnFormat": "json", "value": value, "limit": min(limit, MAX_ITEMS)}
    data = _safe(_post, f"{base}/attributes/restSearch",
                 headers={"Authorization": _env("HISAC_API_KEY"),
                          "Accept": "application/json",
                          "Content-Type": "application/json"},
                 json=body)
    if "error" in data:
        return data
    attrs = ((data.get("response") or {}).get("Attribute") or [])
    return {
        "count": len(attrs),
        "attributes": [
            {
                "value": a.get("value"),
                "type": a.get("type"),
                "category": a.get("category"),
                "to_ids": a.get("to_ids"),
                "timestamp": a.get("timestamp"),
                "event_id": a.get("event_id"),
                "event_info": (a.get("Event") or {}).get("info", "")[:300],
                "tags": [t.get("name") for t in (a.get("Tag") or [])][:10],
            }
            for a in attrs[:limit]
        ],
    }


# ---------------------------------------------------------------------------
# cross-vendor enrichment
# ---------------------------------------------------------------------------

@mcp.tool()
def enrich_indicator(indicator: str) -> dict:
    """Fan out a single observable (IP, domain, or hash) across every
    configured intel source and return a merged view. This is the tool to reach
    for first during triage: it is cheaper than calling each vendor by hand and
    surfaces disagreement between sources."""
    results: dict = {"indicator": indicator, "sources": {}}

    is_ip = indicator.count(".") == 3 and all(
        p.isdigit() for p in indicator.split(".")
    )

    if _env("SHODAN_API_KEY") and is_ip:
        results["sources"]["shodan"] = shodan_host(indicator)
    if _env("INTEL471_API_KEY"):
        results["sources"]["intel471"] = intel471_search_indicators(indicator, limit=5)
    if _env("HISAC_API_KEY"):
        results["sources"]["hisac"] = hisac_search(indicator, limit=5)

    if not results["sources"]:
        return {"error": "no intel sources configured; check the .env file"}
    return results


if __name__ == "__main__":
    mcp.run()
