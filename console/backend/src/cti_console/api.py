"""HTTP API. GET only: the console reads the pipeline's output and never changes it."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, Request, Response
from fastapi import Path as PathParam
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from .config import Settings
from .deliverables import Deliverable, scan
from .pipeline import load_rules
from .reader import render_docx
from .summary import build_summary, collect_runs

# The Vite dev server. Nothing else may call the API from a browser.
FRONTEND_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]
MAX_LIMIT = 1000
# Pipeline IDs (CTI26-137, TH26-54, CVE-VM-2026-11-10) and console IDs (WK-2026-46).
ID_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9-]{1,39}$"
DOCX_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
# The API only ever returns data and files. Nothing it sends should run or be framed.
API_CSP = "default-src 'none'; frame-ancestors 'none'"


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
        response.headers["Content-Security-Policy"] = API_CSP
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
    def deliverables_list(
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

    def find(ident: str) -> tuple[Deliverable, Path]:
        """The deliverable and its file, checked to sit inside the out folder."""
        items = scan(settings.out_dir, load_rules(settings.scripts_dir))
        match = next((d for d in items if d.id == ident), None)
        if match is None:
            raise HTTPException(404, f"No deliverable {ident}")
        out = settings.out_dir.resolve()
        path = (out / match.path).resolve()
        if not path.is_relative_to(out) or not path.is_file():
            raise HTTPException(404, f"No file for {ident}")
        return match, path

    @app.get("/api/deliverables/{ident}/html")
    def deliverable_html(ident: str = PathParam(pattern=ID_PATTERN)) -> dict[str, object]:
        match, path = find(ident)
        rendered = render_docx(path)
        return {**match.to_dict(), "html": rendered.html, "warnings": rendered.warnings}

    @app.get("/api/deliverables/{ident}/file")
    def deliverable_file(ident: str = PathParam(pattern=ID_PATTERN)) -> FileResponse:
        _, path = find(ident)
        return FileResponse(path, media_type=DOCX_TYPE, filename=path.name)

    return app
