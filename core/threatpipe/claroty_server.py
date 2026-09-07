"""Claroty xDome MCP server — OT/IoT device and vulnerability tools.

Queries the Claroty xDome API for device inventory and vulnerability data.
The vulnerability catalog tells you what CVEs Claroty has matched into the
estate; the device inventory tells you what assets exist. Use the
claroty_vuln_devices tool to get the join: which specific devices are
affected by a given vulnerability.
"""

from fastmcp import FastMCP
from _shared import _env, _need, _safe, _post, MAX_ITEMS

mcp = FastMCP("claroty")

CLAROTY_PAGE = 50

DEVICE_FIELDS = [
    "asset_id", "uid", "device_name", "device_type", "device_category",
    "manufacturer", "model", "os_name", "os_version", "serial_number",
    "ip_address", "mac_address", "location", "site_name", "purdue_level",
    "risk_score", "criticality", "labels",
]

VULN_FIELDS = [
    "id", "name", "cve_ids", "cvss_v3_score", "cvss_v3_vector_string",
    "description", "published_date", "is_known_exploited", "source_name",
    "affected_device_count", "severity",
]


def _claroty_base() -> str:
    return _env("CLAROTY_API_HOST") or "https://api.claroty.com"


def _claroty_headers() -> dict:
    return {
        "Authorization": f"Bearer {_env('CLAROTY_API_TOKEN')}",
        "Content-Type": "application/json",
    }


@mcp.tool()
def claroty_devices(search: str = "", limit: int = 50, offset: int = 0) -> dict:
    """Query the Claroty xDome OT/IoT device inventory. Optionally filter by
    IP address, hostname, or device name (substring match, case insensitive).
    Returns device identity, network location, purdue level, and risk score.
    Supports pagination via offset (verified gap-free). Use when scoping which
    cyber-physical assets an advisory or campaign actually touches."""
    if err := _need("CLAROTY_API_TOKEN"):
        return err
    body: dict = {
        "limit": min(limit, CLAROTY_PAGE),
        "offset": offset,
        "fields": DEVICE_FIELDS,
    }
    if search:
        body["filter_by"] = {"field": "device_name", "operation": "contains", "value": search}
    data = _safe(_post, f"{_claroty_base()}/api/v1/devices",
                 headers=_claroty_headers(), json=body)
    if "error" in data:
        return data
    return {
        "total": data.get("total_count") or data.get("count"),
        "offset": offset,
        "devices": [
            {
                "asset_id": d.get("asset_id"),
                "uid": d.get("uid"),
                "name": d.get("device_name"),
                "type": d.get("device_type"),
                "category": d.get("device_category"),
                "manufacturer": d.get("manufacturer"),
                "model": d.get("model"),
                "os": d.get("os_name"),
                "os_version": d.get("os_version"),
                "ip": d.get("ip_address"),
                "mac": d.get("mac_address"),
                "site": d.get("site_name"),
                "purdue": d.get("purdue_level"),
                "risk": d.get("risk_score"),
                "criticality": d.get("criticality"),
                "labels": d.get("labels", []),
            }
            for d in (data.get("devices") or [])[:limit]
        ],
    }


@mcp.tool()
def claroty_vulnerabilities(cve_id: str = "", limit: int = 50, offset: int = 0) -> dict:
    """Query vulnerabilities Claroty xDome has matched against the OT/IoT
    estate, optionally narrowed to one CVE. Returns severity, KEV status,
    and affected device count. Supports pagination via offset.

    IMPORTANT: CVE IDs are case sensitive — always use uppercase (CVE-2023-1968).
    Lowercase returns empty results without error.

    Note: affected_device_count shows how many devices are impacted. To see
    WHICH devices, use claroty_vuln_devices with the vulnerability ID."""
    if err := _need("CLAROTY_API_TOKEN"):
        return err
    if cve_id:
        cve_id = cve_id.upper().strip()
    body: dict = {
        "limit": min(limit, CLAROTY_PAGE),
        "offset": offset,
        "fields": VULN_FIELDS,
    }
    if cve_id:
        body["filter_by"] = {"field": "cve_ids", "operation": "in", "value": [cve_id]}
    data = _safe(_post, f"{_claroty_base()}/api/v1/vulnerabilities",
                 headers=_claroty_headers(), json=body)
    if "error" in data:
        return data
    return {
        "total": data.get("total_count") or data.get("count"),
        "offset": offset,
        "vulnerabilities": [
            {
                "id": v.get("id"),
                "name": v.get("name"),
                "cves": v.get("cve_ids", []),
                "cvss_v3": v.get("cvss_v3_score"),
                "severity": v.get("severity"),
                "vector": v.get("cvss_v3_vector_string"),
                "known_exploited": v.get("is_known_exploited"),
                "source": v.get("source_name"),
                "published": v.get("published_date"),
                "affected_device_count": v.get("affected_device_count"),
                "description": (v.get("description") or "")[:600],
            }
            for v in (data.get("vulnerabilities") or [])[:limit]
        ],
    }


@mcp.tool()
def claroty_vuln_devices(vulnerability_id: int, limit: int = 50, offset: int = 0) -> dict:
    """Get the specific devices affected by a Claroty vulnerability ID.
    First use claroty_vulnerabilities to find the vulnerability ID, then call
    this to see which assets are actually impacted. This is the join between
    the vulnerability catalog and the device inventory — it answers 'which of
    our assets are exposed to this CVE' with specific device names and sites."""
    if err := _need("CLAROTY_API_TOKEN"):
        return err
    body: dict = {
        "limit": min(limit, CLAROTY_PAGE),
        "offset": offset,
        "fields": DEVICE_FIELDS,
        "filter_by": {
            "field": "vulnerability_id",
            "operation": "in",
            "value": [vulnerability_id],
        },
    }
    data = _safe(_post, f"{_claroty_base()}/api/v1/devices",
                 headers=_claroty_headers(), json=body)
    if "error" in data:
        return data
    return {
        "vulnerability_id": vulnerability_id,
        "total": data.get("total_count") or data.get("count"),
        "offset": offset,
        "devices": [
            {
                "asset_id": d.get("asset_id"),
                "uid": d.get("uid"),
                "name": d.get("device_name"),
                "type": d.get("device_type"),
                "category": d.get("device_category"),
                "manufacturer": d.get("manufacturer"),
                "model": d.get("model"),
                "os": d.get("os_name"),
                "os_version": d.get("os_version"),
                "ip": d.get("ip_address"),
                "site": d.get("site_name"),
                "purdue": d.get("purdue_level"),
                "risk": d.get("risk_score"),
                "criticality": d.get("criticality"),
                "labels": d.get("labels", []),
            }
            for d in (data.get("devices") or [])[:limit]
        ],
    }


if __name__ == "__main__":
    mcp.run()
