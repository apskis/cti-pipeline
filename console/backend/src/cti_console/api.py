"""HTTP API. The pipeline's output is read only; the stakeholder list is the one write.

Writes are guarded three ways: the browser must send a custom header (which forces a
CORS preflight that only GETs pass, so other sites cannot send it), any Origin must be
the console's own, and the Host must be this machine (no DNS rebinding).
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, Response
from fastapi import Path as PathParam
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import FileResponse

from .audience import audience_view
from .config import Settings
from .deliverables import Deliverable, scan
from .pdf import Converter, PdfCache, PdfError, WordWorker, word_available
from .pipeline import load_rules
from .reader import render_docx
from .register import latest_register, read_register
from .rundetail import find_run, run_detail
from .stakeholders import StakeholderIn, StakeholderStore, StoreError
from .summary import build_summary, collect_runs

# The Vite dev server. Nothing else may call the API from a browser.
FRONTEND_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]
LOCAL_HOSTS = ["127.0.0.1", "localhost"]
WRITE_HEADER = "X-CTI-Console"
STAKEHOLDER_PATTERN = r"^sh-[a-f0-9]{8}$"
MAX_LIMIT = 1000
# Pipeline IDs (CTI26-137, TH26-54, CVE-VM-2026-11-10) and console IDs (WK-2026-46).
ID_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9-]{1,39}$"
# Run IDs are made here: component then start time, bulletin-scan-20261110T145714.
RUN_PATTERN = r"^[a-z][a-z-]{1,40}-\d{8}T\d{6}$"
DOCX_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
# The API only ever returns data and files. Nothing it sends should run or be framed.
API_CSP = "default-src 'none'; frame-ancestors 'none'"
# The one exception: the branded PDF is shown inside the console's own page.
PDF_CSP = "default-src 'none'; frame-ancestors 'self'"


def require_console(
    origin: str | None = Header(None),
    x_cti_console: str | None = Header(None, alias=WRITE_HEADER),
) -> None:
    """Refuse a write unless it plainly comes from the console's own page."""
    if x_cti_console != "1":
        raise HTTPException(403, f"Writes need the {WRITE_HEADER} header")
    if origin is not None and origin not in FRONTEND_ORIGINS:
        raise HTTPException(403, "Writes are accepted from the console page only")


def create_app(
    settings: Settings | None = None,
    converter: Converter | None = None,
    pdf_ready: bool | None = None,
) -> FastAPI:
    """`converter` and `pdf_ready` replace Word in tests; by default Word is looked for."""
    settings = settings or Settings.from_env()
    has_word = word_available() if pdf_ready is None else pdf_ready
    worker = WordWorker() if converter is None and has_word else None
    pdfs = PdfCache(settings.cache_dir / "pdf", converter or worker)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        if worker is not None:
            worker.warm_up()  # Word's slow first export happens before anyone is waiting
        yield
        if worker is not None:
            worker.close()

    app = FastAPI(
        title="GeneLabs CTI console",
        version="0.1.0",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        lifespan=lifespan,
    )
    # Cross origin, only GETs pass the preflight; writes come from the page's own origin.
    app.add_middleware(
        CORSMiddleware, allow_origins=FRONTEND_ORIGINS, allow_methods=["GET"], allow_headers=[]
    )
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=LOCAL_HOSTS)
    store = StakeholderStore(settings.stakeholders_file, settings.stakeholders_example)

    def store_call(action):  # type: ignore[no-untyped-def]
        try:
            return action()
        except StoreError as exc:
            raise HTTPException(exc.status, str(exc)) from exc

    @app.middleware("http")
    async def no_sniff(request: Request, call_next):  # type: ignore[no-untyped-def]
        response: Response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Cache-Control"] = "no-store"
        response.headers.setdefault("Content-Security-Policy", API_CSP)
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

    @app.get("/api/runs/{ident}")
    def run(ident: str = PathParam(pattern=RUN_PATTERN)) -> dict[str, object]:
        found = find_run(settings, ident)
        if found is None:
            raise HTTPException(404, f"No run {ident}")
        return run_detail(settings, *found)

    @app.get("/api/cves")
    def cves() -> dict[str, object]:
        register = latest_register(settings.out_dir)
        rows = read_register(register) if register else None
        return {
            "register": register.relative_to(settings.out_dir).as_posix() if register else None,
            "cves": [c.to_dict() for c in rows or []],
        }

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
        return {
            **match.to_dict(),
            "html": rendered.html,
            "warnings": rendered.warnings,
            "pdf": has_word,
        }

    @app.get("/api/deliverables/{ident}/file")
    def deliverable_file(ident: str = PathParam(pattern=ID_PATTERN)) -> FileResponse:
        _, path = find(ident)
        return FileResponse(path, media_type=DOCX_TYPE, filename=path.name)

    def branded_pdf(ident: str) -> tuple[Path, Path]:
        """The report's .docx and its cached PDF, made now if this version has none."""
        if not has_word:
            raise HTTPException(503, "Microsoft Word is not available to make the PDF")
        _, path = find(ident)
        try:
            return path, pdfs.get(ident, path)
        except PdfError as exc:
            raise HTTPException(exc.status, str(exc)) from exc

    @app.get("/api/deliverables/{ident}/pdf/ready")
    def deliverable_pdf_ready(ident: str = PathParam(pattern=ID_PATTERN)) -> dict[str, object]:
        """Makes the PDF if needed, so the page can show progress before it frames it."""
        _, pdf = branded_pdf(ident)
        return {"id": ident, "bytes": pdf.stat().st_size}

    @app.get("/api/deliverables/{ident}/pdf")
    def deliverable_pdf(
        ident: str = PathParam(pattern=ID_PATTERN), download: bool = False
    ) -> FileResponse:
        source, pdf = branded_pdf(ident)
        return FileResponse(
            pdf,
            media_type="application/pdf",
            filename=source.with_suffix(".pdf").name,
            content_disposition_type="attachment" if download else "inline",
            headers={"Content-Security-Policy": PDF_CSP},
        )

    @app.get("/api/stakeholders")
    def stakeholders() -> dict[str, object]:
        people = store_call(store.load)
        return {
            "exists": store.exists(),
            "has_example": settings.stakeholders_example.is_file(),
            "stakeholders": [p.model_dump() for p in people],
        }

    @app.post("/api/stakeholders", status_code=201, dependencies=[Depends(require_console)])
    def stakeholder_add(item: StakeholderIn) -> dict[str, object]:
        return store_call(lambda: store.add(item)).model_dump()

    @app.put("/api/stakeholders/{ident}", dependencies=[Depends(require_console)])
    def stakeholder_update(
        item: StakeholderIn, ident: str = PathParam(pattern=STAKEHOLDER_PATTERN)
    ) -> dict[str, object]:
        return store_call(lambda: store.update(ident, item)).model_dump()

    @app.delete(
        "/api/stakeholders/{ident}", status_code=204, dependencies=[Depends(require_console)]
    )
    def stakeholder_remove(ident: str = PathParam(pattern=STAKEHOLDER_PATTERN)) -> Response:
        store_call(lambda: store.remove(ident))
        return Response(status_code=204)

    @app.post(
        "/api/stakeholders/start-from-example",
        status_code=201,
        dependencies=[Depends(require_console)],
    )
    def stakeholders_from_example() -> dict[str, object]:
        people = store_call(store.start_from_example)
        return {"stakeholders": [p.model_dump() for p in people]}

    @app.get("/api/audience")
    def audience() -> dict[str, object]:
        """Teams each report names, the stakeholders who match, and teams nobody covers."""
        return audience_view(settings.out_dir, store_call(store.load))

    return app
