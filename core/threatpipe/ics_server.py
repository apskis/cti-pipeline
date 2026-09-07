"""ICS[AP] advisory MCP server — CISA ICS-CERT advisories via RapidAPI.

Note: The free tier returns advisory data with a 1-month delay and does not
support vendor/product filtering server-side. Filters are applied client-side.
"""

from typing import Optional

from fastmcp import FastMCP
from _shared import _env, _need, _safe, _get, MAX_ITEMS

mcp = FastMCP("ics-advisories")


def _ics_headers() -> dict:
    return {
        "X-RapidAPI-Key": _env("RAPIDAPI_ICS_KEY"),
        "X-RapidAPI-Host": _env("RAPIDAPI_ICS_HOST"),
    }


def _ics_url(path: str) -> str:
    host = _env("RAPIDAPI_ICS_HOST")
    return f"https://{host}/{path.lstrip('/')}"


@mcp.tool()
def ics_advisories(vendor: str = "", product: str = "", limit: int = 25) -> dict:
    """Get ICS-CERT advisories for industrial control system vulnerabilities.
    Optionally filter by vendor or product name (case-insensitive, client-side).
    Note: free tier data is delayed ~1 month. Use for OT vulnerability context
    that complements Claroty's asset view."""
    if err := _need("RAPIDAPI_ICS_KEY", "RAPIDAPI_ICS_HOST"):
        return err
    data = _safe(_get, _ics_url("/advisories/ics"), headers=_ics_headers())
    if isinstance(data, dict) and "error" in data and data["error"] is not False:
        return data
    results = data.get("result", []) if isinstance(data, dict) else []
    if not results:
        return {"count": 0, "advisories": [],
                "note": "No advisories returned. Free tier data is ~1 month behind."}
    # Client-side filtering since server doesn't support it
    if vendor:
        v_lower = vendor.lower()
        results = [r for r in results if v_lower in str(r.get("vendor", "")).lower()
                   or v_lower in str(r).lower()]
    if product:
        p_lower = product.lower()
        results = [r for r in results if p_lower in str(r.get("product", "")).lower()
                   or p_lower in str(r).lower()]
    return {"count": len(results), "advisories": results[:min(limit, MAX_ITEMS)]}


@mcp.tool()
def ics_vendors() -> dict:
    """List all ICS vendors tracked in the advisory database. Use to find the
    correct vendor name for filtering advisories."""
    if err := _need("RAPIDAPI_ICS_KEY", "RAPIDAPI_ICS_HOST"):
        return err
    data = _safe(_get, _ics_url("/vendors"), headers=_ics_headers())
    if isinstance(data, dict) and data.get("error") is False:
        return {"vendors": data.get("result", [])}
    return data


@mcp.tool()
def ics_products(vendor: str = "") -> dict:
    """List ICS products in the advisory database. Optionally filter by vendor
    name (case-insensitive, client-side). Use to identify which products are
    tracked for ICS vulnerabilities."""
    if err := _need("RAPIDAPI_ICS_KEY", "RAPIDAPI_ICS_HOST"):
        return err
    data = _safe(_get, _ics_url("/products"), headers=_ics_headers())
    if isinstance(data, dict) and data.get("error") is False:
        results = data.get("result", [])
        if vendor:
            v_lower = vendor.lower()
            results = [r for r in results if v_lower in (r.get("vendor") or "").lower()]
        return {"count": len(results), "products": results[:MAX_ITEMS]}
    return data


if __name__ == "__main__":
    mcp.run()
