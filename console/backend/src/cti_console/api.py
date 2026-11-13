"""HTTP API. The pipeline's output is read only; stakeholders, brand and companies are written.

Everything but the company list reads the active company's folders only. A write must
also name that company, so a tab left open on another company cannot save into this one.

Writes are guarded three ways: the browser must send a custom header (which forces a
CORS preflight that only GETs pass, so other sites cannot send it), any Origin must be
the console's own, and the Host must be this machine (no DNS rebinding).
"""

from __future__ import annotations

import dataclasses
import threading
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from pathlib import Path
from typing import TypeVar

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, Response
from fastapi import Path as PathParam
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import FileResponse

from .audience import audience_view
from .brand import MAX_IMAGE_BYTES, AssetKind, BrandError, BrandIn, BrandStore
from .companies import Companies, CompanyError, CompanyIn, Pick
from .config import Settings
from .deliverables import Deliverable, load_checks, save_checks, scan, warm_checks
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
COMPANY_HEADER = "X-CTI-Company"
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


T = TypeVar("T")


@dataclasses.dataclass(frozen=True)
class CompanyContext:
    """One company's settings and stores. Made once per company and kept."""

    slug: str
    settings: Settings
    brands: BrandStore
    store: StakeholderStore
    pdfs: PdfCache


def create_app(
    settings: Settings | None = None,
    converter: Converter | None = None,
    pdf_ready: bool | None = None,
) -> FastAPI:
    """`converter` and `pdf_ready` replace Word in tests; by default Word is looked for."""
    settings = settings or Settings.from_env()
    has_word = word_available() if pdf_ready is None else pdf_ready
    worker = WordWorker() if converter is None and has_word else None
    convert = converter or worker
    # Results are keyed by each report's full path, so one file serves every company.
    checks_file = settings.cache_dir / "checks.json"
    companies = Companies(settings)
    contexts: dict[str, CompanyContext] = {}
    contexts_lock = threading.Lock()

    def company_call(action: Callable[[], T]) -> T:
        try:
            return action()
        except CompanyError as exc:
            raise HTTPException(exc.status, str(exc)) from exc

    def store_call(action: Callable[[], T]) -> T:
        try:
            return action()
        except StoreError as exc:
            raise HTTPException(exc.status, str(exc)) from exc

    def brand_call(action: Callable[[], T]) -> T:
        try:
            return action()
        except BrandError as exc:
            raise HTTPException(exc.status, str(exc)) from exc

    def warm(ctx: CompanyContext) -> None:
        """Check the company's new or changed reports beside the server, not in a request."""
        threading.Thread(
            target=warm_checks,
            args=(ctx.settings.out_dir, load_rules(settings.scripts_dir), checks_file),
            name=f"warm-checks-{ctx.slug}",
            daemon=True,
        ).start()

    def context(slug: str) -> CompanyContext:
        with contexts_lock:
            if slug not in contexts:
                space = companies.workspace(slug)
                scoped = dataclasses.replace(
                    settings,
                    out_dir=space.out_dir,
                    logs_dir=space.logs_dir,
                    stakeholders_file=space.stakeholders_file,
                )
                contexts[slug] = CompanyContext(
                    slug=slug,
                    settings=scoped,
                    brands=BrandStore(space.folder),
                    store=StakeholderStore(space.stakeholders_file, space.stakeholders_example),
                    # A folder per company: old versions of a PDF are tidied by report
                    # ID, and another company may use the same ID.
                    pdfs=PdfCache(settings.cache_dir / "pdf" / slug, convert),
                )
            return contexts[slug]

    def current() -> CompanyContext:
        return company_call(lambda: context(companies.active_slug()))

    def require_company(company: str | None = Header(None, alias=COMPANY_HEADER)) -> None:
        """A write names the company the page shows; refused if another is active now."""
        if company is None:
            raise HTTPException(400, f"Writes need the {COMPANY_HEADER} header")
        active = companies.active_slug()
        if company != active:
            raise HTTPException(
                409,
                f"The console has switched to another company ({active}). "
                "Reload the page and make the change again.",
            )

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        load_checks(checks_file, load_rules(settings.scripts_dir))
        # Only new or changed reports are left to check, and that runs beside the
        # server, so the health check answers at once instead of after every report.
        warm(current())
        if worker is not None:
            worker.warm_up()  # Word's slow first export happens before anyone is waiting
        try:
            yield
        finally:
            if worker is not None:
                worker.close()
        save_checks(checks_file, load_rules(settings.scripts_dir))  # keeps this run's checks

    app = FastAPI(
        title="CTI console",
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
    writes = [Depends(require_console)]
    company_writes = [Depends(require_console), Depends(require_company)]

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

    # ---------------------------------------------------------------- companies
    @app.get("/api/companies")
    def companies_list() -> dict[str, object]:
        return companies.listing().model_dump()

    @app.put("/api/companies/active", dependencies=writes)
    def companies_pick(item: Pick) -> dict[str, object]:
        listing = company_call(lambda: companies.pick(item.slug))
        warm(current())
        return listing.model_dump()

    @app.post("/api/companies", status_code=201, dependencies=writes)
    def companies_create(item: CompanyIn) -> dict[str, object]:
        return company_call(lambda: companies.create(item)).model_dump()

    # ---------------------------------------------------------------- brand
    @app.get("/api/brand")
    def brand() -> dict[str, object]:
        """Read on each call, so an edited brand file shows on the next page load."""
        return brand_call(current().brands.load).model_dump()

    @app.get("/api/brand/assets/{kind}")
    def brand_asset(kind: AssetKind) -> FileResponse:
        path = brand_call(lambda: current().brands.asset(kind))
        return FileResponse(path, media_type="image/png")

    @app.post("/api/brand/preview", dependencies=writes)
    def brand_preview(item: BrandIn) -> dict[str, object]:
        return BrandStore.preview(item).model_dump()

    @app.put("/api/brand", dependencies=company_writes)
    def brand_save(item: BrandIn) -> dict[str, object]:
        return brand_call(lambda: current().brands.save(item)).model_dump()

    @app.put("/api/brand/assets/{kind}", dependencies=company_writes)
    async def brand_asset_save(
        kind: AssetKind, request: Request, content_type: str | None = Header(None)
    ) -> dict[str, object]:
        if content_type != "image/png":
            raise HTTPException(415, "Send the image as image/png")
        brands = current().brands  # the company the header named, before the body arrives
        # Read no more than the limit allows, whatever Content-Length claims.
        data = bytearray()
        async for chunk in request.stream():
            data.extend(chunk)
            if len(data) > MAX_IMAGE_BYTES:
                raise HTTPException(413, f"The image is over {MAX_IMAGE_BYTES // 1048576} MB")
        return brand_call(lambda: brands.save_asset(kind, bytes(data))).model_dump()

    # ---------------------------------------------------------------- pipeline output
    @app.get("/api/summary")
    def summary() -> dict[str, object]:
        return build_summary(current().settings)

    @app.get("/api/runs")
    def runs(
        component: str | None = None, limit: int = Query(50, ge=1, le=MAX_LIMIT)
    ) -> list[dict[str, object]]:
        found = [r for r in collect_runs(current().settings) if component in (None, r.component)]
        return [r.to_dict() for r in reversed(found[-limit:])]

    @app.get("/api/runs/{ident}")
    def run(ident: str = PathParam(pattern=RUN_PATTERN)) -> dict[str, object]:
        scoped = current().settings
        found = find_run(scoped, ident)
        if found is None:
            raise HTTPException(404, f"No run {ident}")
        return run_detail(scoped, *found)

    @app.get("/api/cves")
    def cves() -> dict[str, object]:
        out_dir = current().settings.out_dir
        register = latest_register(out_dir)
        rows = read_register(register) if register else None
        return {
            "register": register.relative_to(out_dir).as_posix() if register else None,
            "cves": [c.to_dict() for c in rows or []],
        }

    @app.get("/api/deliverables")
    def deliverables_list(
        kind: str | None = None,
        status: str | None = None,
        q: str | None = Query(None, max_length=100),
        limit: int = Query(500, ge=1, le=MAX_LIMIT),
    ) -> list[dict[str, object]]:
        items = scan(current().settings.out_dir, load_rules(settings.scripts_dir))
        needle = (q or "").lower()
        picked = [
            d
            for d in items
            if kind in (None, d.kind)
            and status in (None, d.status)
            and needle in f"{d.id} {d.title}".lower()
        ]
        return [d.to_dict() for d in picked[:limit]]

    def find(ident: str, out_dir: Path) -> tuple[Deliverable, Path]:
        """The deliverable and its file, checked to sit inside the company's out folder."""
        items = scan(out_dir, load_rules(settings.scripts_dir))
        match = next((d for d in items if d.id == ident), None)
        if match is None:
            raise HTTPException(404, f"No deliverable {ident}")
        out = out_dir.resolve()
        path = (out / match.path).resolve()
        if not path.is_relative_to(out) or not path.is_file():
            raise HTTPException(404, f"No file for {ident}")
        return match, path

    @app.get("/api/deliverables/{ident}/html")
    def deliverable_html(ident: str = PathParam(pattern=ID_PATTERN)) -> dict[str, object]:
        match, path = find(ident, current().settings.out_dir)
        rendered = render_docx(path)
        return {
            **match.to_dict(),
            "html": rendered.html,
            "warnings": rendered.warnings,
            "pdf": has_word,
        }

    @app.get("/api/deliverables/{ident}/file")
    def deliverable_file(ident: str = PathParam(pattern=ID_PATTERN)) -> FileResponse:
        _, path = find(ident, current().settings.out_dir)
        return FileResponse(path, media_type=DOCX_TYPE, filename=path.name)

    def branded_pdf(ident: str) -> tuple[Path, Path]:
        """The report's .docx and its cached PDF, made now if this version has none."""
        if not has_word:
            raise HTTPException(503, "Microsoft Word is not available to make the PDF")
        ctx = current()
        _, path = find(ident, ctx.settings.out_dir)
        try:
            return path, ctx.pdfs.get(ident, path)
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

    # ---------------------------------------------------------------- stakeholders
    @app.get("/api/stakeholders")
    def stakeholders() -> dict[str, object]:
        ctx = current()
        people = store_call(ctx.store.load)
        return {
            "exists": ctx.store.exists(),
            "has_example": ctx.store.example.is_file(),
            "stakeholders": [p.model_dump() for p in people],
        }

    @app.post("/api/stakeholders", status_code=201, dependencies=company_writes)
    def stakeholder_add(item: StakeholderIn) -> dict[str, object]:
        return store_call(lambda: current().store.add(item)).model_dump()

    @app.put("/api/stakeholders/{ident}", dependencies=company_writes)
    def stakeholder_update(
        item: StakeholderIn, ident: str = PathParam(pattern=STAKEHOLDER_PATTERN)
    ) -> dict[str, object]:
        return store_call(lambda: current().store.update(ident, item)).model_dump()

    @app.delete("/api/stakeholders/{ident}", status_code=204, dependencies=company_writes)
    def stakeholder_remove(ident: str = PathParam(pattern=STAKEHOLDER_PATTERN)) -> Response:
        store_call(lambda: current().store.remove(ident))
        return Response(status_code=204)

    @app.post("/api/stakeholders/start-from-example", status_code=201, dependencies=company_writes)
    def stakeholders_from_example() -> dict[str, object]:
        people = store_call(current().store.start_from_example)
        return {"stakeholders": [p.model_dump() for p in people]}

    @app.get("/api/audience")
    def audience() -> dict[str, object]:
        """Teams each report names, the stakeholders who match, and teams nobody covers."""
        ctx = current()
        return audience_view(ctx.settings.out_dir, store_call(ctx.store.load))

    return app
