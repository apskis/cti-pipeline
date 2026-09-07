"""Cross-vendor enrichment MCP server — fans out an indicator to every
configured source and returns results per-source in a single envelope.

NOT a correlation engine. There is no merged verdict, normalised confidence,
conflict detection, or rollup. You get each source's raw response and must
draw your own conclusions. The value is one call instead of N, with explicit
reporting of which sources were queried, which were skipped, and why.

Data quality note on ThreatQ: a TQ "hit" means the observable appeared in an
ingested feed (H-ISAC, BleepingComputer, etc.). score:null with no threshold
means it is a lead, not a verdict. Always check the source attribution."""

import re
import httpx
from fastmcp import FastMCP
from _shared import _env, _need, _safe, _get, _post, MAX_ITEMS, TIMEOUT

mcp = FastMCP("enrich")

_RE_IPV4 = re.compile(
    r"^(?:(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)\.){3}(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)$"
)
_RE_DOMAIN = re.compile(
    r"^(?:[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$"
)
_RE_MD5 = re.compile(r"^[a-fA-F0-9]{32}$")
_RE_SHA1 = re.compile(r"^[a-fA-F0-9]{40}$")
_RE_SHA256 = re.compile(r"^[a-fA-F0-9]{64}$")
_RE_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[a-zA-Z]{2,}$")


def _classify(indicator: str) -> str | None:
    """Return the indicator type or None if it doesn't parse as anything."""
    indicator = indicator.strip()
    if _RE_IPV4.match(indicator):
        return "ip"
    if _RE_SHA256.match(indicator):
        return "sha256"
    if _RE_SHA1.match(indicator):
        return "sha1"
    if _RE_MD5.match(indicator):
        return "md5"
    if _RE_EMAIL.match(indicator):
        return "email"
    if _RE_DOMAIN.match(indicator):
        return "domain"
    return None


def _shodan_enrich(ip: str) -> dict:
    """Full Shodan host lookup — preserves decision-relevant fields."""
    data = _safe(_get, f"https://api.shodan.io/shodan/host/{ip}",
                 params={"key": _env("SHODAN_API_KEY"), "minify": False})
    if "error" in data:
        return data
    services_raw = data.get("data", [])
    services = []
    for s in services_raw[:20]:
        svc = {
            "port": s.get("port"),
            "transport": s.get("transport"),
            "product": s.get("product"),
            "version": s.get("version"),
            "cpe": s.get("cpe", [])[:3],
        }
        if s.get("vulns"):
            svc["vulns"] = list(s["vulns"].keys())[:10] if isinstance(s["vulns"], dict) else list(s["vulns"])[:10]
        ssl = s.get("ssl", {}).get("cert", {})
        if ssl:
            svc["ssl_cn"] = ssl.get("subject", {}).get("CN")
            svc["ssl_issuer"] = ssl.get("issuer", {}).get("O")
        services.append(svc)

    return {
        "ip": data.get("ip_str"),
        "org": data.get("org"),
        "isp": data.get("isp"),
        "asn": data.get("asn"),
        "country": data.get("country_name"),
        "tags": data.get("tags", []),
        "os": data.get("os"),
        "hostnames": data.get("hostnames", [])[:10],
        "last_update": data.get("last_update"),
        "vulns": list(data.get("vulns", {}).keys())[:30] if isinstance(data.get("vulns"), dict) else list(data.get("vulns", []))[:30],
        "services": services,
    }


def _intel471_enrich(indicator: str) -> dict:
    """Intel 471 indicator lookup — preserves validity window and context."""
    data = _safe(_get, "https://api.intel471.com/v1/iocs",
                 params={"ioc": indicator, "count": 10},
                 auth=(_env("INTEL471_EMAIL"), _env("INTEL471_API_KEY")))
    if "error" in data:
        return data
    out = []
    for rec in (data.get("iocs") or [])[:10]:
        d = rec.get("data", rec)
        links = d.get("links", {})
        out.append({
            "value": d.get("value") or d.get("indicator"),
            "type": d.get("type") or d.get("indicator_type"),
            "context": d.get("context"),
            "confidence": d.get("confidence"),
            "threat_type": links.get("threat", {}).get("type") if isinstance(links.get("threat"), dict) else None,
            "malware_family": links.get("malwareFamily"),
            "valid_from": d.get("first_seen") or d.get("valid_from"),
            "valid_until": d.get("last_seen") or d.get("valid_until"),
        })
    return {
        "total": data.get("iocTotalCount", len(out)),
        "indicators": out,
    }


def _tq_enrich(value: str) -> dict:
    """Search ThreatQuotient for an indicator — preserves source attribution."""
    tq_url = _env("TQ_URL").rstrip("/")
    cid = _env("TQ_CLIENT_ID")
    csec = _env("TQ_CLIENT_SECRET")

    try:
        with httpx.Client(timeout=TIMEOUT, follow_redirects=True) as c:
            r = c.post(f"{tq_url}/api/token", auth=(cid, csec),
                       data={"grant_type": "client_credentials"})
            r.raise_for_status()
            token = r.json().get("access_token")

            headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
            r2 = c.get(f"{tq_url}/api/indicators", headers=headers,
                       params={"value": value, "limit": 10, "with": "type,sources,tags"})
            r2.raise_for_status()
            data = r2.json()
    except Exception as e:
        return {"error": f"TQ query failed: {type(e).__name__}"}

    indicators = data.get("data", [])
    return {
        "total": data.get("total", len(indicators)),
        "indicators": [
            {
                "value": ind.get("value"),
                "type": ind.get("type", {}).get("name") if isinstance(ind.get("type"), dict) else ind.get("type_id"),
                "score": ind.get("score"),
                "sources": [s.get("name") for s in (ind.get("sources") or []) if s.get("name")][:8],
                "tags": [t.get("name") for t in (ind.get("tags") or []) if t.get("name")][:5],
                "created": ind.get("created_at"),
                "updated": ind.get("updated_at"),
            }
            for ind in indicators[:10]
        ],
    }


def _claroty_asset_check(ip: str) -> dict:
    """Check if an IP belongs to an OT/IoT asset in Claroty xDome."""
    token = _env("CLAROTY_API_TOKEN")
    base = _env("CLAROTY_API_HOST") or "https://api.claroty.com"
    headers = {"Authorization": f"Token {token}", "Accept": "application/json"}
    body = {
        "limit": 5,
        "offset": 0,
        "fields": ["asset_id", "device_name", "device_type", "device_category",
                   "manufacturer", "ip_address", "site_name", "purdue_level",
                   "risk_score", "criticality"],
        "filter_by": {"field": "ip_address", "operation": "in", "value": [ip]},
    }
    data = _safe(_post, f"{base}/api/v1/devices/", headers=headers, json=body)
    if "error" in data:
        return data
    devices = data.get("devices") or []
    if not devices:
        return {"matched": False, "note": "IP not found in OT/IoT asset inventory"}
    return {
        "matched": True,
        "count": len(devices),
        "devices": [
            {
                "asset_id": d.get("asset_id"),
                "name": d.get("device_name"),
                "type": d.get("device_type"),
                "category": d.get("device_category"),
                "manufacturer": d.get("manufacturer"),
                "ip": d.get("ip_address"),
                "site": d.get("site_name"),
                "purdue": d.get("purdue_level"),
                "risk": d.get("risk_score"),
                "criticality": d.get("criticality"),
            }
            for d in devices[:5]
        ],
    }


@mcp.tool()
def enrich_indicator(indicator: str) -> dict:
    """Fan out a single observable across configured intel sources.

    Returns each source's response in a sources dict, plus a skipped dict
    explaining which sources were not queried and why.

    NOT a correlation engine — no merged verdict, no conflict detection.
    You get raw per-source results and must compare them yourself.

    Supported types: IPv4, domain, MD5, SHA-1, SHA-256, email.
    Sources queried vary by type:
      IP      → Shodan + Intel 471 + ThreatQ + Claroty (asset check)
      Domain  → Intel 471 + ThreatQ
      Hash    → Intel 471 + ThreatQ
      Email   → Intel 471 + ThreatQ

    ThreatQ caveat: a hit means the string appeared in an ingested feed.
    score:null means no scoring was applied. Treat as a lead, not a verdict."""

    indicator = indicator.strip()
    ioc_type = _classify(indicator)

    if ioc_type is None:
        return {
            "error": "Input does not parse as a recognised indicator type",
            "input": indicator,
            "hint": "Expected: IPv4 address, domain, MD5, SHA-1, SHA-256, or email address. "
                    "Check for typos, whitespace, or mixed-case hex.",
            "supported_formats": {
                "ip": "1.2.3.4",
                "domain": "example.com",
                "md5": "32 hex chars",
                "sha1": "40 hex chars",
                "sha256": "64 hex chars",
                "email": "user@domain.tld",
            },
        }

    results: dict = {
        "indicator": indicator,
        "type": ioc_type,
        "sources": {},
        "skipped": {},
    }

    # Shodan: IPs only
    if _env("SHODAN_API_KEY"):
        if ioc_type == "ip":
            results["sources"]["shodan"] = _shodan_enrich(indicator)
        else:
            results["skipped"]["shodan"] = f"not applicable for type '{ioc_type}' (IP only)"
    else:
        results["skipped"]["shodan"] = "not configured"

    # Intel 471: all types
    if _env("INTEL471_API_KEY"):
        results["sources"]["intel471"] = _intel471_enrich(indicator)
    else:
        results["skipped"]["intel471"] = "not configured"

    # ThreatQ: all types
    if _env("TQ_CLIENT_ID"):
        results["sources"]["threatq"] = _tq_enrich(indicator)
    else:
        results["skipped"]["threatq"] = "not configured"

    # Claroty: IPs only — checks if this is one of our OT/IoT assets
    if _env("CLAROTY_API_TOKEN"):
        if ioc_type == "ip":
            results["sources"]["claroty"] = _claroty_asset_check(indicator)
        else:
            results["skipped"]["claroty"] = f"not applicable for type '{ioc_type}' (IP only)"
    else:
        results["skipped"]["claroty"] = "not configured"

    if not results["sources"]:
        return {"error": "no intel sources configured; set KEY_VAULT_URL or credential env vars"}

    # Remove skipped if empty (all sources queried)
    if not results["skipped"]:
        del results["skipped"]

    return results


if __name__ == "__main__":
    mcp.run()
