"""Rapid7 InsightVM MCP server — asset inventory and vulnerability scanning.

Uses the InsightVM Cloud Integrations API v4. Supports cursor-based pagination
and sorting, with a max page size of 1000.

Key limitations of the v4 cloud API:
- No server-side CVE filtering on assets. For 'which assets have CVE-X', use
  the InsightVM console (/api/3/) or Claroty for OT/IoT.
- Tag filtering via body query (e.g. {"asset": "sites IN ['name']"}) works for
  sites but is unreliable for custom tags in some tenants.
- Vulnerability endpoint returns the global definition catalog, not per-asset
  vulns. Only useful for enriching CVE metadata (severity, categories).
"""

from fastmcp import FastMCP
from _shared import _env, _need, _safe, _post, MAX_ITEMS

mcp = FastMCP("rapid7")

RAPID7_MAX_PAGE = 500


def _rapid7_base() -> str:
    region = _env("RAPID7_REGION") or "us"
    return f"https://{region}.api.insight.rapid7.com"


def _rapid7_headers() -> dict:
    return {"X-Api-Key": _env("RAPID7_API_KEY"), "Content-Type": "application/json"}


@mcp.tool()
def rapid7_assets(
    limit: int = 50,
    sort: str = "risk_score,DESC",
    cursor: str = "",
    search: str = "",
) -> dict:
    """List assets from InsightVM with hostname, IP, OS, vuln counts, and risk score.

    Results are sorted by risk_score descending by default (highest-risk first).
    Other useful sort options: 'last_assessed_for_vulnerabilities,DESC' (most
    recently scanned first), 'host_name,ASC' (alphabetical).

    Pagination: use the 'next_cursor' value from a previous response to get the
    next page. Each page returns up to `limit` assets (max 500).

    Optional search: pass an InsightVM query string to filter. Examples:
      "host_name CONTAINS 'sql'"
      "ip = '10.1.1.5'"
      "sites IN ['Production']"

    NOTE: The InsightVM cloud API does not support CVE-based asset filtering. For
    'which assets are affected by CVE-X', use claroty_vulnerabilities (OT) or
    the InsightVM console directly (IT).

    Tag caveat: tags are returned as-is from the API but may be truncated or
    vary between calls due to API-side pagination of nested tag arrays. Do not
    rely on tag absence to mean an asset lacks that tag."""
    if err := _need("RAPID7_API_KEY"):
        return err

    page_size = min(limit, RAPID7_MAX_PAGE)
    params: dict = {"size": page_size, "sort": sort}
    if cursor:
        params["cursor"] = cursor

    body: dict = {}
    if search:
        body["asset"] = search

    data = _safe(_post, f"{_rapid7_base()}/vm/v4/integration/assets",
                 headers=_rapid7_headers(), params=params, json=body)
    if "error" in data:
        return data

    meta = data.get("metadata") or {}
    assets = data.get("data", [])

    return {
        "total": meta.get("totalResources") or meta.get("totalData") or meta.get("total_data"),
        "page_size": page_size,
        "sort": sort,
        "next_cursor": meta.get("cursor"),
        "search": search or None,
        "assets": [
            {
                "id": a.get("id"),
                "hostname": a.get("host_name"),
                "ip": a.get("ip"),
                "os": a.get("os_description") or a.get("os_name"),
                "risk": a.get("risk_score"),
                "critical_vulns": a.get("critical_vulnerabilities"),
                "severe_vulns": a.get("severe_vulnerabilities"),
                "moderate_vulns": a.get("moderate_vulnerabilities"),
                "last_assessed": a.get("last_assessed_for_vulnerabilities"),
                "tags": [t.get("name") for t in (a.get("tags") or []) if t.get("name")],
                "sites": [s.get("name") for s in (a.get("sites") or []) if s.get("name")][:5],
            }
            for a in assets[:limit]
        ],
    }


@mcp.tool()
def rapid7_vuln_search(query: str = "", cve_id: str = "", limit: int = 20) -> dict:
    """Search Rapid7's vulnerability definition catalog by keyword or CVE ID.
    Returns CVSS scores, severity, and categories.

    This is the GLOBAL catalog (all known vulns), not per-asset findings.
    Use rapid7_assets to find which hosts have high vuln counts.

    Limitation: this endpoint does not support robust server-side filtering.
    Results may not match the query if the API's search semantics differ from
    expectations. For authoritative CVE data, prefer nvd_cve."""
    if err := _need("RAPID7_API_KEY"):
        return err

    page_size = min(limit, RAPID7_MAX_PAGE)
    params: dict = {"size": page_size, "sort": "severity,DESC"}
    body: dict = {}

    if cve_id:
        cve_id = cve_id.upper().strip()
        body["vulnerability"] = f"cve_id CONTAINS '{cve_id}'"
    elif query:
        body["vulnerability"] = f"title CONTAINS '{query}'"

    data = _safe(_post, f"{_rapid7_base()}/vm/v4/integration/vulnerabilities",
                 headers=_rapid7_headers(), params=params, json=body)
    if "error" in data:
        # Fallback: try without filter (API may not support query syntax)
        if body:
            data = _safe(_post, f"{_rapid7_base()}/vm/v4/integration/vulnerabilities",
                         headers=_rapid7_headers(), params=params, json={})
            if "error" in data:
                return data
            # Filter client-side by CVE ID
            vulns = data.get("data", [])
            if cve_id:
                vulns = [v for v in vulns if cve_id in [c.upper() for c in (v.get("cves") or [])]]
            if not vulns:
                return {
                    "query": cve_id or query,
                    "found": False,
                    "note": "Rapid7 vuln catalog search does not support server-side CVE filtering. "
                            "Use nvd_cve for authoritative CVE data.",
                }
        else:
            return data

    vulns = data.get("data", [])
    meta = data.get("metadata") or {}

    return {
        "query": cve_id or query or "(unfiltered)",
        "total": meta.get("totalResources") or meta.get("totalData"),
        "found": len(vulns) > 0,
        "vulnerabilities": [
            {
                "id": v.get("id"),
                "title": v.get("title"),
                "cves": v.get("cves"),
                "cvss_v3": v.get("cvss_v3_score"),
                "cvss_v2": v.get("cvss_v2_score"),
                "severity": v.get("severity"),
                "categories": v.get("categories"),
                "published": v.get("published"),
            }
            for v in vulns[:limit]
        ],
    }


if __name__ == "__main__":
    mcp.run()
