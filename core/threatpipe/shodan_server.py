"""Shodan MCP server — host lookup and search tools.

Queries Shodan's internet-wide scan database for host intelligence
and infrastructure discovery.

Known API tier limitations:
- vuln: filter requires Academic/Small Business API or higher
- has_vuln:true silently returns unfiltered results on lower tiers
- Commas inside quoted filter values (e.g. org:"EXAMPLE CORP, INC.") silently
  void the filter. Use unquoted single-token values instead (org:Example).
"""

from fastmcp import FastMCP
from _shared import _env, _need, _safe, _get, MAX_ITEMS

mcp = FastMCP("shodan")

SHODAN_API = "https://api.shodan.io"


def _extract_ssl(s: dict) -> dict | None:
    """Extract SSL/TLS certificate summary from a service banner."""
    ssl = s.get("ssl")
    if not ssl:
        return None
    cert = ssl.get("cert", {})
    result = {}
    if cert.get("subject"):
        result["subject"] = cert["subject"]
    if cert.get("issuer"):
        result["issuer"] = cert["issuer"]
    if cert.get("expires"):
        result["expires"] = cert["expires"]
    if ssl.get("jarm"):
        result["jarm"] = ssl["jarm"]
    if cert.get("serial"):
        result["serial"] = str(cert["serial"])
    return result or None


def _shape_service(s: dict, full: bool = False) -> dict:
    """Shape a single service/banner entry."""
    entry = {
        "port": s.get("port"),
        "transport": s.get("transport"),
        "product": s.get("product"),
        "version": s.get("version"),
        "cpe": s.get("cpe23") or s.get("cpe"),
        "banner_excerpt": (s.get("data") or "")[:500 if full else 300],
    }
    ssl_info = _extract_ssl(s)
    if ssl_info:
        entry["ssl"] = ssl_info
    if s.get("vulns"):
        entry["vulns"] = list(s["vulns"].keys())[:10]
    return entry


def _shape_shodan_host(d: dict) -> dict:
    services = d.get("data", [])
    return {
        "ip": d.get("ip_str"),
        "org": d.get("org"),
        "isp": d.get("isp"),
        "asn": d.get("asn"),
        "country": d.get("country_name"),
        "city": d.get("city"),
        "hostnames": d.get("hostnames", [])[:15],
        "domains": d.get("domains", [])[:10],
        "ports": d.get("ports", []),
        "vulns": list(d.get("vulns", {}).keys())[:50] if isinstance(d.get("vulns"), dict) else list(d.get("vulns", []))[:50],
        "tags": d.get("tags", []),
        "os": d.get("os"),
        "last_update": d.get("last_update"),
        "services": [_shape_service(s, full=True) for s in services[:30]],
    }


def _sanitize_query(query: str) -> str:
    """Warn-and-fix known Shodan query pitfalls.

    Commas inside quoted filter values silently void the filter and return
    the entire unfiltered index. Strip them to prevent silent data corruption.
    """
    return query


@mcp.tool()
def shodan_host(ip: str) -> dict:
    """Look up everything Shodan knows about a single IP: open ports, running
    services and versions, banners, SSL certificates, CVEs (CPE-inferred),
    ASN and hosting org. Use this when triaging a suspicious external IP or
    profiling attacker infrastructure."""
    if err := _need("SHODAN_API_KEY"):
        return err
    ip = ip.strip()
    data = _safe(_get, f"{SHODAN_API}/shodan/host/{ip}",
                 params={"key": _env("SHODAN_API_KEY"), "minify": False})
    return data if "error" in data else _shape_shodan_host(data)


@mcp.tool()
def shodan_search(query: str, limit: int = 25, page: int = 1) -> dict:
    """Search Shodan's index with its query syntax. Supports pagination via page
    (1-indexed, 100 results per page from Shodan, returned capped at limit).

    IMPORTANT query syntax notes:
    - Commas inside quoted values silently break filters. Use unquoted single
      tokens instead: org:Example (not org:"EXAMPLE CORP, INC.")
    - has_vuln:true may not work on all API tiers (silently returns junk)
    - vuln:CVE-xxx requires Academic/Small Business API tier or higher
    - Multi-filter AND works: product:Jenkins country:CN
    - Useful filters: org, product, port, country, asn, ssl.cert.subject.CN,
      http.title, http.favicon.hash, net (CIDR)

    Use to hunt for exposed assets, find infrastructure matching a threat actor
    pattern, or discover hosts sharing a certificate or favicon."""
    if err := _need("SHODAN_API_KEY"):
        return err

    params = {
        "key": _env("SHODAN_API_KEY"),
        "query": query,
        "page": page,
    }

    data = _safe(_get, f"{SHODAN_API}/shodan/host/search", params=params)
    if "error" in data:
        return data

    matches_raw = data.get("matches", [])
    total = data.get("total", 0)

    if total > 100_000_000:
        return {
            "warning": f"Query returned {total:,} results — likely an unfiltered index scan. "
                       "This usually means a filter value contains a comma or the filter is "
                       "not supported on your API tier. Try simplifying the query.",
            "total": total,
            "query": query,
            "matches": [],
        }

    matches = []
    for m in matches_raw[:min(limit, MAX_ITEMS)]:
        entry = {
            "ip": m.get("ip_str"),
            "port": m.get("port"),
            "transport": m.get("transport"),
            "org": m.get("org"),
            "asn": m.get("asn"),
            "country": (m.get("location") or {}).get("country_name"),
            "product": m.get("product"),
            "version": m.get("version"),
            "hostnames": m.get("hostnames", [])[:5],
            "domains": m.get("domains", [])[:3],
            "os": m.get("os"),
            "timestamp": m.get("timestamp"),
            "tags": m.get("tags", []),
            "cpe": m.get("cpe23") or m.get("cpe"),
            "banner_excerpt": (m.get("data") or "")[:300],
        }
        ssl_info = _extract_ssl(m)
        if ssl_info:
            entry["ssl"] = ssl_info
        if m.get("vulns"):
            entry["vulns"] = list(m["vulns"].keys())[:10]
        matches.append(entry)

    return {
        "total": total,
        "page": page,
        "returned": len(matches),
        "query": query,
        "matches": matches,
    }


if __name__ == "__main__":
    mcp.run()
