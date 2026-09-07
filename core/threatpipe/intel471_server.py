"""Intel 471 MCP server — indicator, report, and alert tools.

Uses the Intel 471 Titan v1 API (api.intel471.com/v1).
- Reports and IOCs use offset-based pagination (offset + count, max 100).
- Watcher alerts use cursor-based streaming.
"""

from fastmcp import FastMCP
from _shared import _env, _need, _safe, _get, MAX_ITEMS

import httpx
from _shared import TIMEOUT

mcp = FastMCP("intel471")

INTEL471_BASE = "https://api.intel471.com/v1"
I471_MAX = 100


def _i471_auth():
    return (_env("INTEL471_EMAIL"), _env("INTEL471_API_KEY"))


def _i471_get(path: str, params: dict) -> dict:
    """HTTP GET with Intel 471 auth, returns parsed JSON or error dict."""
    try:
        with httpx.Client(timeout=TIMEOUT, follow_redirects=True) as c:
            r = c.get(f"{INTEL471_BASE}{path}", params=params, auth=_i471_auth())
            r.raise_for_status()
            return r.json()
    except httpx.HTTPStatusError as e:
        return {"error": f"HTTP {e.response.status_code}", "detail": e.response.text[:500]}
    except httpx.HTTPError as e:
        return {"error": "request failed", "detail": str(e)[:300]}


@mcp.tool()
def intel471_search_indicators(
    indicator: str,
    indicator_type: str = "",
    limit: int = 25,
    offset: int = 0,
) -> dict:
    """Look up an IP, domain, URL, or file hash in Intel 471's malware
    intelligence (IOC database). Returns confidence, associated malware family,
    threat type, and context. Supports pagination via offset. Optionally filter
    by type: 'file', 'domain', 'url', 'ip'. Use this to establish whether an
    observable is tied to known criminal infrastructure."""
    if err := _need("INTEL471_EMAIL", "INTEL471_API_KEY"):
        return err

    params: dict = {
        "ioc": indicator,
        "count": min(limit, I471_MAX),
        "offset": offset,
        "sort": "latest",
    }
    if indicator_type:
        params["ioc_type"] = indicator_type

    data = _i471_get("/iocs", params)
    if "error" in data:
        return data

    out = []
    for rec in (data.get("iocs") or []):
        d = rec.get("data", {})
        links = d.get("links") or {}
        out.append({
            "value": d.get("value") or d.get("indicator"),
            "type": d.get("type"),
            "confidence": d.get("confidence"),
            "threat_type": (d.get("threat") or {}).get("type"),
            "malware_family": links.get("malwareFamily"),
            "valid_from": d.get("first_seen") or d.get("valid_from"),
            "valid_until": d.get("last_seen") or d.get("valid_until"),
            "context": (d.get("context") or {}).get("description", "")[:300],
        })

    return {
        "total": data.get("iocTotalCount", len(out)),
        "offset": offset,
        "indicators": out[:limit],
    }


@mcp.tool()
def intel471_reports(
    query: str,
    limit: int = 25,
    offset: int = 0,
    sort: str = "latest",
) -> dict:
    """Free text search across Intel 471 finished intelligence reports
    (actor profiles, breach alerts, underground activity). Returns titles,
    dates, classifications, actors, and entities. Supports pagination via
    offset. Sort: 'latest', 'earliest', or 'relevance'. Use when you need
    adversary context or want to check coverage on a campaign or actor."""
    if err := _need("INTEL471_EMAIL", "INTEL471_API_KEY"):
        return err

    params: dict = {
        "report": query,
        "count": min(limit, I471_MAX),
        "offset": offset,
        "sort": sort,
    }

    data = _i471_get("/reports", params)
    if "error" in data:
        return data

    return {
        "total": data.get("reportTotalCount"),
        "offset": offset,
        "reports": [
            {
                "uid": r.get("uid"),
                "title": r.get("subject"),
                "created": r.get("created"),
                "classification": (r.get("classification") or {}).get("intelRequirements"),
                "admiralty_code": (r.get("classification") or {}).get("admiraltyCode"),
                "summary": (r.get("executiveSummary") or r.get("rawTextShort") or "")[:800],
                "actors": [a.get("handle") for a in (r.get("actorSubjectOfReport") or [])][:10],
                "entities": [
                    {"type": e.get("type"), "value": e.get("value")}
                    for e in (r.get("entities") or [])
                    if e.get("value")
                ][:30],
            }
            for r in (data.get("reports") or [])[:limit]
        ],
    }


@mcp.tool()
def intel471_report_detail(uid: str) -> dict:
    """Fetch a single Intel 471 report by its UID. Returns the full executive
    summary and entity list (IOCs, actors, CVEs extracted from the report).
    Use after intel471_reports to read the content of a specific report."""
    if err := _need("INTEL471_EMAIL", "INTEL471_API_KEY"):
        return err

    data = _i471_get(f"/reports/{uid}", {})
    if "error" in data:
        return data

    r = data
    return {
        "uid": r.get("uid"),
        "title": r.get("subject"),
        "created": r.get("created"),
        "updated": r.get("lastUpdated"),
        "classification": (r.get("classification") or {}).get("intelRequirements"),
        "admiralty_code": (r.get("classification") or {}).get("admiraltyCode"),
        "summary": (r.get("executiveSummary") or "")[:2000],
        "raw_text": (r.get("rawText") or r.get("rawTextShort") or "")[:3000],
        "actors": [a.get("handle") for a in (r.get("actorSubjectOfReport") or [])][:20],
        "entities": [
            {"type": e.get("type"), "value": e.get("value")}
            for e in (r.get("entities") or [])
            if e.get("value")
        ][:50],
        "tags": r.get("reportTags", [])[:20],
        "locations": [loc.get("country") for loc in (r.get("locations") or []) if loc.get("country")][:10],
    }


@mcp.tool()
def intel471_alerts(limit: int = 25, cursor: str = "") -> dict:
    """Retrieve Intel 471 Watcher alerts for the tenant's monitored assets,
    actors, and keywords. Returns breach alerts, threat reports, and forum
    activity flagged against your watchlists. Supports cursor-based pagination
    (pass the returned cursor value to get the next page). Use for a daily
    sweep of what Intel 471 flagged."""
    if err := _need("INTEL471_EMAIL", "INTEL471_API_KEY"):
        return err

    params: dict = {"count": min(limit, I471_MAX)}
    if cursor:
        params["cursor"] = cursor

    data = _i471_get("/alerts", params)
    if "error" in data:
        return data

    alerts_raw = data.get("alerts") or []
    seen_titles = set()
    deduped = []
    for a in alerts_raw:
        shaped = _shape_alert(a)
        title_key = shaped.get("title") or shaped.get("uid")
        if title_key and title_key in seen_titles:
            continue
        seen_titles.add(title_key)
        deduped.append(shaped)

    return {
        "total": data.get("alertTotalCount"),
        "cursor_next": data.get("cursorNext"),
        "alerts": deduped[:limit],
    }


def _shape_alert(a: dict) -> dict:
    """Extract title and metadata from an Intel471 alert regardless of entity type."""
    skip = {"uid", "status", "watcherUid", "watcherGroupUid", "foundTime", "highlights"}
    entity_type = next((k for k in a.keys() if k not in skip), "unknown")
    entity = a.get(entity_type, {})
    entity_data = entity.get("data", {})

    snake_type = entity_type[0].lower() + entity_type[1:]
    snake_type = "".join(f"_{c.lower()}" if c.isupper() else c for c in snake_type)
    nested = entity_data.get(snake_type, {})
    if not isinstance(nested, dict):
        nested = {}

    title = nested.get("title") or nested.get("subject") or nested.get("name")

    result = {
        "uid": a.get("uid"),
        "type": entity_type,
        "created": a.get("foundTime"),
        "title": title,
    }
    if nested.get("victim"):
        victim = nested["victim"]
        result["victim"] = victim.get("name")
        if victim.get("industries"):
            result["industry"] = victim["industries"][0].get("industry")
    if nested.get("confidence"):
        result["confidence"] = nested["confidence"].get("level")
    if nested.get("actor_or_group"):
        result["actor"] = nested["actor_or_group"]

    return result


if __name__ == "__main__":
    mcp.run()
