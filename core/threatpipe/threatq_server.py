"""ThreatQuotient MCP server — queries the full TQ indicator and event library.

ThreatQuotient ingests multiple intel feeds including H-ISAC (source_id=16),
Intel 471, and others. Responses include source attribution so you can see
where each indicator originated.
"""

from typing import Optional

from fastmcp import FastMCP
from _shared import _env, _need, _safe, _get, _post, log, TIMEOUT, MAX_ITEMS

import httpx

mcp = FastMCP("threatq")

_TQ_TOKEN: Optional[str] = None
_TQ_TYPE_CACHE: Optional[dict] = None


def _tq_authenticate() -> Optional[str]:
    """Get an OAuth2 bearer token from ThreatQuotient. Caches in module."""
    global _TQ_TOKEN
    if _TQ_TOKEN:
        return _TQ_TOKEN

    base = _env("TQ_URL").rstrip("/")
    client_id = _env("TQ_CLIENT_ID")
    client_secret = _env("TQ_CLIENT_SECRET")

    try:
        with httpx.Client(timeout=TIMEOUT, follow_redirects=True) as c:
            r = c.post(f"{base}/api/token",
                       auth=(client_id, client_secret),
                       data={"grant_type": "client_credentials"})
            r.raise_for_status()
            _TQ_TOKEN = r.json().get("access_token")
            return _TQ_TOKEN
    except Exception as e:
        log.warning("TQ auth failed: %s", type(e).__name__)
        return None


def _tq_headers() -> dict:
    token = _tq_authenticate()
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }


def _tq_base() -> str:
    return _env("TQ_URL").rstrip("/")


def _resolve_type_id(type_name: str) -> Optional[int]:
    """Resolve an indicator type name (e.g. 'IP Address') to its numeric type_id.

    TQ's /api/indicators endpoint requires a numeric type_id for filtering.
    Passing the string name causes a 500.
    """
    global _TQ_TYPE_CACHE
    if _TQ_TYPE_CACHE is None:
        try:
            with httpx.Client(timeout=TIMEOUT, follow_redirects=True) as c:
                r = c.get(f"{_tq_base()}/api/indicator/types",
                          headers=_tq_headers())
                r.raise_for_status()
                data = r.json()
                types_list = data.get("data", data) if isinstance(data, dict) else data
                if isinstance(types_list, list):
                    _TQ_TYPE_CACHE = {
                        t["name"].lower(): t["id"]
                        for t in types_list
                        if isinstance(t, dict) and "name" in t and "id" in t
                    }
                else:
                    _TQ_TYPE_CACHE = {}
        except Exception as e:
            log.warning("Failed to fetch TQ indicator types: %s", e)
            _TQ_TYPE_CACHE = {}

    return _TQ_TYPE_CACHE.get(type_name.lower())


@mcp.tool()
def tq_search_indicator(value: str, limit: int = 25, offset: int = 0) -> dict:
    """Search for an indicator (IP, domain, hash, URL, email) in ThreatQuotient.
    TQ ingests H-ISAC, Intel 471, and other feeds. Results include source
    attribution showing where the match originated. Supports pagination via
    offset. Use to check whether any intel source has reported an observable."""
    if err := _need("TQ_URL", "TQ_CLIENT_ID", "TQ_CLIENT_SECRET"):
        return err
    token = _tq_authenticate()
    if not token:
        return {"error": "ThreatQuotient authentication failed"}

    base = _tq_base()
    params = {
        "value": value,
        "limit": min(limit, MAX_ITEMS),
        "offset": offset,
        "with": "type,sources,tags",
    }

    with httpx.Client(timeout=TIMEOUT, follow_redirects=True) as c:
        try:
            r = c.get(f"{base}/api/indicators", headers=_tq_headers(), params=params)
            r.raise_for_status()
            data = r.json()
        except httpx.HTTPStatusError as e:
            return {"error": f"HTTP {e.response.status_code}", "detail": e.response.text[:300]}
        except httpx.HTTPError as e:
            return {"error": "request failed", "detail": str(e)[:300]}

    indicators = data.get("data", data) if isinstance(data, dict) else data
    if not isinstance(indicators, list):
        indicators = [indicators] if isinstance(indicators, dict) else []

    total = data.get("total", len(indicators)) if isinstance(data, dict) else len(indicators)

    return {
        "query": value,
        "total": total,
        "offset": offset,
        "count": len(indicators),
        "indicators": [
            {
                "id": ind.get("id"),
                "value": ind.get("value"),
                "type": ind.get("type", {}).get("name") if isinstance(ind.get("type"), dict) else ind.get("type_id"),
                "score": ind.get("score"),
                "status": ind.get("status", {}).get("name") if isinstance(ind.get("status"), dict) else ind.get("status_id"),
                "created": ind.get("created_at"),
                "updated": ind.get("updated_at"),
                "sources": [s.get("name") for s in (ind.get("sources") or []) if s.get("name")][:5],
                "tags": [t.get("name") for t in (ind.get("tags") or []) if t.get("name")][:10],
            }
            for ind in indicators[:limit]
        ],
    }


@mcp.tool()
def tq_recent_indicators(
    indicator_type: str = "",
    limit: int = 25,
    offset: int = 0,
) -> dict:
    """Get indicators from ThreatQuotient sorted newest first.
    Source attribution is included per indicator. Optionally filter by type:
    'IP Address', 'FQDN', 'URL', 'MD5', 'SHA-256', 'Email Address', 'CVE', etc.
    Supports pagination via offset.

    Data quality caveat: TQ ingests article scrapers (RSS Feed Reader,
    BleepingComputer, etc.) that extract IP strings from blog posts. A hit with
    score:null means 'appeared in a feed', not 'is malicious'. Check sources."""
    if err := _need("TQ_URL", "TQ_CLIENT_ID", "TQ_CLIENT_SECRET"):
        return err
    token = _tq_authenticate()
    if not token:
        return {"error": "ThreatQuotient authentication failed"}

    base = _tq_base()

    params: dict = {
        "limit": min(limit, MAX_ITEMS),
        "offset": offset,
        "sort": "-created_at",
        "with": "type,sources,tags",
    }

    if indicator_type:
        type_id = _resolve_type_id(indicator_type)
        if type_id is None:
            return {
                "error": f"Unknown indicator type: '{indicator_type}'",
                "hint": "Use tq_recent_indicators() with no type to see available type names in results, "
                        "or try: 'IP Address', 'FQDN', 'URL', 'MD5', 'SHA-256', 'Email Address', 'CVE'",
            }
        params["type_id"] = type_id

    with httpx.Client(timeout=TIMEOUT, follow_redirects=True) as c:
        try:
            r = c.get(f"{base}/api/indicators", headers=_tq_headers(), params=params)
            r.raise_for_status()
            data = r.json()
        except httpx.HTTPStatusError as e:
            return {"error": f"HTTP {e.response.status_code}", "detail": e.response.text[:300]}
        except httpx.HTTPError as e:
            return {"error": "request failed", "detail": str(e)[:300]}

    indicators = data.get("data", []) if isinstance(data, dict) else []
    total = data.get("total", len(indicators)) if isinstance(data, dict) else len(indicators)

    return {
        "total": total,
        "offset": offset,
        "type_filter": indicator_type or None,
        "indicators": [
            {
                "id": ind.get("id"),
                "value": ind.get("value"),
                "type": ind.get("type", {}).get("name") if isinstance(ind.get("type"), dict) else ind.get("type_id"),
                "score": ind.get("score"),
                "status": ind.get("status", {}).get("name") if isinstance(ind.get("status"), dict) else ind.get("status_id"),
                "created": ind.get("created_at"),
                "sources": [s.get("name") for s in (ind.get("sources") or []) if s.get("name")][:5],
                "tags": [t.get("name") for t in (ind.get("tags") or []) if t.get("name")][:10],
            }
            for ind in indicators[:limit]
        ],
    }


@mcp.tool()
def tq_events(
    limit: int = 25,
    offset: int = 0,
    type_id: int = 0,
) -> dict:
    """Get ThreatQuotient events (intel reports, campaigns, sightings).

    Known event types (pass as type_id to filter):
      14 = Splunk sighting (indicator observed in our environment — high value)
      15 = Intel 471 alert (pointer to I471, title only, description stripped)

    Type 14 sightings include Match Count, First/Last Seen, and a deep link to
    Splunk ES. Use type_id=14 to retrieve these directly instead of paging
    through the full event list.

    Intel 471 alerts (type 15) arrive with description stripped. Use the UID
    from the title to look up full content via intel471_report_detail.

    Supports pagination via offset. Sorted newest first."""
    if err := _need("TQ_URL", "TQ_CLIENT_ID", "TQ_CLIENT_SECRET"):
        return err
    token = _tq_authenticate()
    if not token:
        return {"error": "ThreatQuotient authentication failed"}

    base = _tq_base()

    params: dict = {
        "limit": min(limit, MAX_ITEMS),
        "offset": offset,
        "sort": "-created_at",
        "with": "type,tags",
    }
    if type_id:
        params["type_id"] = type_id

    with httpx.Client(timeout=TIMEOUT, follow_redirects=True) as c:
        try:
            r = c.get(f"{base}/api/events", headers=_tq_headers(), params=params)
            r.raise_for_status()
            data = r.json()
        except httpx.HTTPStatusError as e:
            return {"error": f"HTTP {e.response.status_code}", "detail": e.response.text[:300]}
        except httpx.HTTPError as e:
            return {"error": "request failed", "detail": str(e)[:300]}

    events = data.get("data", []) if isinstance(data, dict) else []
    total = data.get("total", len(events)) if isinstance(data, dict) else len(events)

    EVENT_TYPE_NAMES = {14: "Splunk Sighting", 15: "Intel 471 Alert"}

    return {
        "total": total,
        "offset": offset,
        "type_filter": type_id or None,
        "events": [
            {
                "id": ev.get("id"),
                "title": ev.get("title"),
                "type_id": ev.get("type_id") or (ev.get("type", {}).get("id") if isinstance(ev.get("type"), dict) else None),
                "type_name": (
                    ev.get("type", {}).get("name") if isinstance(ev.get("type"), dict)
                    else EVENT_TYPE_NAMES.get(ev.get("type_id"), f"type_{ev.get('type_id')}")
                ),
                "created": ev.get("created_at"),
                "description": (ev.get("description") or "")[:800],
                "tags": [t.get("name") for t in (ev.get("tags") or []) if t.get("name")][:10],
            }
            for ev in events[:limit]
        ],
    }


if __name__ == "__main__":
    mcp.run()
