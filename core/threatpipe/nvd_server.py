"""NVD MCP server — CVE lookup and keyword search tools.

Queries NIST NVD 2.0 API. Supports CVSS v4.0/v3.1/v3.0/v2.0 scoring,
CISA KEV status, CPE affected product data, and paginated search.
"""

from datetime import datetime, timedelta, timezone

from fastmcp import FastMCP
from _shared import _env, _need, _safe, _get, MAX_ITEMS

mcp = FastMCP("nvd")

NVD_BASE = "https://services.nvd.nist.gov/rest/json/cves/2.0"
NVD_MAX_PAGE = 100


def _nvd_headers() -> dict:
    key = _env("NVD_API_KEY")
    return {"apiKey": key} if key else {}


def _extract_cvss(metrics: dict) -> dict | None:
    """Extract the best available CVSS score, preferring v4 > v3.1 > v3.0 > v2."""
    for key in ("cvssMetricV40", "cvssMetricV31", "cvssMetricV30", "cvssMetricV2"):
        entries = metrics.get(key)
        if entries:
            m = entries[0].get("cvssData", {})
            return {
                "version": m.get("version"),
                "score": m.get("baseScore"),
                "severity": m.get("baseSeverity") or entries[0].get("baseSeverity"),
                "vector": m.get("vectorString"),
            }
    return None


def _extract_kev(cve: dict) -> dict | None:
    """Extract CISA Known Exploited Vulnerabilities (KEV) data if present."""
    exploit_add = cve.get("cisaExploitAdd")
    if not exploit_add:
        return None
    return {
        "date_added": exploit_add,
        "vulnerability_name": cve.get("cisaVulnerabilityName"),
        "required_action": cve.get("cisaRequiredAction"),
        "due_date": cve.get("cisaActionDue"),
    }


def _extract_cpe(cve: dict, max_entries: int = 15) -> list:
    """Extract affected product CPE entries from configurations."""
    configs = cve.get("configurations", [])
    cpes = []
    seen = set()
    for config in configs:
        for node in config.get("nodes", []):
            for match in node.get("cpeMatch", []):
                if not match.get("vulnerable"):
                    continue
                criteria = match.get("criteria", "")
                if criteria in seen:
                    continue
                seen.add(criteria)
                entry = {"cpe": criteria}
                if match.get("versionStartIncluding"):
                    entry["version_from"] = match["versionStartIncluding"]
                if match.get("versionEndExcluding"):
                    entry["version_before"] = match["versionEndExcluding"]
                if match.get("versionEndIncluding"):
                    entry["version_through"] = match["versionEndIncluding"]
                cpes.append(entry)
                if len(cpes) >= max_entries:
                    return cpes
    return cpes


def _shape_cve(item: dict, full: bool = False) -> dict:
    """Shape a single CVE record from NVD API response."""
    cve = item.get("cve", item)
    metrics = cve.get("metrics", {})

    desc = next(
        (d["value"] for d in cve.get("descriptions", []) if d.get("lang") == "en"),
        "",
    )

    refs_raw = cve.get("references", [])
    seen_urls = set()
    refs = []
    for r in refs_raw:
        url = r.get("url", "")
        if url and url not in seen_urls:
            seen_urls.add(url)
            entry = {"url": url}
            tags = r.get("tags")
            if tags:
                entry["tags"] = tags
            refs.append(entry)
            if len(refs) >= (20 if full else 12):
                break

    cwes = list(dict.fromkeys(
        d["value"]
        for w in cve.get("weaknesses", [])
        for d in w.get("description", [])
        if d.get("value", "").startswith("CWE")
    ))

    result = {
        "id": cve.get("id"),
        "published": cve.get("published"),
        "modified": cve.get("lastModified"),
        "status": cve.get("vulnStatus"),
        "cvss": _extract_cvss(metrics),
        "kev": _extract_kev(cve),
        "description": desc if full else desc[:1200],
        "cwe": cwes[:5],
        "references": refs,
    }

    if full:
        result["cpe_affected"] = _extract_cpe(cve)

    return result


@mcp.tool()
def nvd_cve(cve_id: str) -> dict:
    """Get authoritative NVD detail for one CVE: CVSS v4/v3.1 score and vector,
    CISA KEV exploitation status, CWE mapping, affected CPE products/versions,
    description, and deduplicated references with tags. Use when you need the
    canonical severity and affected-product facts for a specific CVE."""
    cve_id = cve_id.upper().strip()
    params = {"cveId": cve_id}
    data = _safe(_get, NVD_BASE, params=params, headers=_nvd_headers())
    if "error" in data:
        return data
    items = data.get("vulnerabilities", [])
    return _shape_cve(items[0], full=True) if items else {"error": f"{cve_id} not found"}


@mcp.tool()
def nvd_search(
    keyword: str,
    last_days: int = 0,
    date_type: str = "published",
    limit: int = 25,
    offset: int = 0,
) -> dict:
    """Search NVD by keyword, optionally limited to CVEs published or modified
    in the last N days. Results are sorted newest first. Supports pagination
    via offset. Set date_type to 'published' (default) for new disclosures or
    'modified' for reanalysis activity. Use for 'what is new for <product>'
    sweeps or building a vulnerability picture for a technology."""
    page_size = min(limit, NVD_MAX_PAGE)
    params: dict = {
        "keywordSearch": keyword,
        "resultsPerPage": page_size,
        "startIndex": offset,
    }

    if last_days:
        now = datetime.now(timezone.utc)
        start = (now - timedelta(days=last_days)).isoformat()
        end = now.isoformat()
        if date_type == "modified":
            params["lastModStartDate"] = start
            params["lastModEndDate"] = end
        else:
            params["pubStartDate"] = start
            params["pubEndDate"] = end

    data = _safe(_get, NVD_BASE, params=params, headers=_nvd_headers())
    if "error" in data:
        return data

    items = data.get("vulnerabilities", [])
    items.sort(key=lambda v: v.get("cve", {}).get("published", ""), reverse=True)

    return {
        "total": data.get("totalResults"),
        "offset": offset,
        "date_type": date_type,
        "results": [_shape_cve(v) for v in items[:limit]],
    }


if __name__ == "__main__":
    mcp.run()
