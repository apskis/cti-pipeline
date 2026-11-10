"""HTTP API. GET only: the console reads the pipeline's output and never changes it."""

from __future__ import annotations

from fastapi import FastAPI, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from .config import Settings
from .deliverables import scan
from .pipeline import load_rules
from .summary import build_summary, collect_runs

# The Vite dev server. Nothing else may call the API from a browser.
FRONTEND_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]
MAX_LIMIT = 1000


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    app = FastAPI(
        title="GeneLabs CTI console",
        version="0.1.0",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    app.add_middleware(
        CORSMiddleware, allow_origins=FRONTEND_ORIGINS, allow_methods=["GET"], allow_headers=[]
    )

    @app.middleware("http")
    async def no_sniff(request: Request, call_next):  # type: ignore[no-untyped-def]
        response: Response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/summary")
    def summary() -> dict[str, object]:
        return build_summary(settings)

    @app.get("/api/runs")
    def runs(
        component: str | None = None, limit: int = Query(50, ge=1, le=MAX_LIMIT)
    ) -> list[dict[str, object]]:
        found = [r for r in collect_runs(settings) if component in (None, r.component)]
        return [r.to_dict() for r in reversed(found[-limit:])]

    @app.get("/api/deliverables")
    def deliverables(
        kind: str | None = None,
        status: str | None = None,
        q: str | None = Query(None, max_length=100),
        limit: int = Query(500, ge=1, le=MAX_LIMIT),
    ) -> list[dict[str, object]]:
        items = scan(settings.out_dir, load_rules(settings.scripts_dir))
        needle = (q or "").lower()
        picked = [
            d
            for d in items
            if kind in (None, d.kind)
            and status in (None, d.status)
            and needle in f"{d.id} {d.title}".lower()
        ]
        return [d.to_dict() for d in picked[:limit]]

    return app
