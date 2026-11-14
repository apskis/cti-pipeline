"""HTTP API. The pipeline's output is read only; stakeholders, brand and companies are written.

Every request is for one person (see auth.py): the local single user, or someone signed
in. Everything but the company list reads the company shown to that person, and only a
company they may read. A write must also name that company, so a tab left open on
another company cannot save into this one, and they must be allowed to change it.

Writes are guarded three ways: the browser must send a custom header (which forces a
CORS preflight that only GETs pass, so other sites cannot send it), any Origin must be
the console's own, and the Host must be the console's (no DNS rebinding).

With sign in off the console is for this machine only, so anything that arrived through a
proxy or tunnel is refused outright: tunnels rewrite Host to localhost, so the Host check
alone would let them through.
"""

from __future__ import annotations

import dataclasses
import threading
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from pathlib import Path
from typing import TypeVar
from urllib.parse import urlsplit

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, Response
from fastapi import Path as PathParam
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import FileResponse, PlainTextResponse, RedirectResponse

from .audience import audience_view
from .auth import (
    LOCAL_USER,
    LOGIN_COOKIE,
    LOGIN_SECONDS,
    SESSION_COOKIE,
    AuthError,
    AuthSettings,
    OidcClient,
    Principal,
    ViewAs,
    principal_from,
    sign,
    unsign,
)
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

# The Vite dev server. Nothing else may call the API from a browser, unless sign in
# names the console's address (CTI_CONSOLE_URL), which is then allowed too.
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
# Set by proxies and tunnels (Dev Tunnels, Cloudflare, nginx); never by a browser.
FORWARDED_HEADERS = ("forwarded", "x-forwarded-for", "x-forwarded-host", "x-forwarded-proto")
LOCAL_ONLY = (
    "This console is for the machine it runs on. To share it, turn on sign in "
    "(CTI_AUTH=oidc); see docs/console-sign-in.md."
)
# A signed in person whose groups name no company yet.
NO_COMPANY = "Your account has no company yet. Ask a platform admin to add you to one."
# Under CTI_AUTH=off there is one person and these routes do not exist.
SIGN_IN_OFF = "Sign in is off: the console runs for one person on this machine"


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
    auth: AuthSettings | None = None,
    oidc: OidcClient | None = None,
) -> FastAPI:
    """`converter` and `pdf_ready` replace Word in tests; by default Word is looked for.
    `oidc` replaces the identity provider in tests."""
    settings = settings or Settings.from_env()
    auth = auth or AuthSettings.from_env()
    provider = (oidc or OidcClient(auth)) if auth.enabled else None
    has_word = word_available() if pdf_ready is None else pdf_ready
    worker = WordWorker() if converter is None and has_word else None
    convert = converter or worker
    # Results are keyed by each report's full path, so one file serves every company.
    checks_file = settings.cache_dir / "checks.json"
    companies = Companies(settings)
    contexts: dict[str, CompanyContext] = {}
    # Sign in off only: the role the local user is acting as. Held in memory, so a
    # restart is always back to platform admin.
    viewing = [ViewAs()]
    contexts_lock = threading.Lock()

    console = urlsplit(auth.console_url)
    origins = list(FRONTEND_ORIGINS)
    hosts = list(LOCAL_HOSTS)
    if auth.enabled:
        origins.append(f"{console.scheme}://{console.netloc}")
        hosts.append(console.hostname or "")

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

    # ------------------------------------------------------------------ who is asking
    def who(request: Request) -> Principal:
        """The person this request is for. Signed out, under sign in, is a 401."""
        if not auth.enabled:
            return viewing[0].principal()
        session = unsign(request.cookies.get(SESSION_COOKIE), auth.session_secret)
        person = principal_from(session, auth)
        if person is None:
            raise HTTPException(401, "Sign in to use the console")
        return person

    def shown(person: Principal = Depends(who)) -> CompanyContext:
        """The company shown to this person, which they are always allowed to read."""
        slug = companies.active_slug(person)
        if slug is None:
            raise HTTPException(403, NO_COMPANY)
        return company_call(lambda: context(slug))

    def require_console(
        origin: str | None = Header(None),
        x_cti_console: str | None = Header(None, alias=WRITE_HEADER),
    ) -> None:
        """Refuse a write unless it plainly comes from the console's own page."""
        if x_cti_console != "1":
            raise HTTPException(403, f"Writes need the {WRITE_HEADER} header")
        if origin is not None and origin not in origins:
            raise HTTPException(403, "Writes are accepted from the console page only")

    def require_company(
        company: str | None = Header(None, alias=COMPANY_HEADER),
        person: Principal = Depends(who),
    ) -> None:
        """A write names the company the page shows; refused if another is shown now, or if
        this person may only read it."""
        if company is None:
            raise HTTPException(400, f"Writes need the {COMPANY_HEADER} header")
        active = companies.active_slug(person)
        if company != active:
            raise HTTPException(
                409,
                f"The console has switched to another company ({active}). "
                "Reload the page and make the change again.",
            )
        if not person.can_write(company):
            raise HTTPException(403, "You can view this company but not change it")

    def require_manager(person: Principal = Depends(who)) -> None:
        if not person.can_manage:
            raise HTTPException(403, "Only a platform admin can add companies")

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        load_checks(checks_file, load_rules(settings.scripts_dir))
        # Only new or changed reports are left to check, and that runs beside the
        # server, so the health check answers at once instead of after every report.
        default = companies.active_slug(LOCAL_USER)
        if default is not None:
            warm(context(default))
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
        CORSMiddleware, allow_origins=origins, allow_methods=["GET"], allow_headers=[]
    )
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=hosts)
    writes = [Depends(require_console)]
    company_writes = [Depends(require_console), Depends(require_company)]

    @app.middleware("http")
    async def local_only(request: Request, call_next):  # type: ignore[no-untyped-def]
        # Registered before no_sniff, so it runs inside it and its answer gets the same
        # headers as any other.
        if not auth.enabled and any(h in request.headers for h in FORWARDED_HEADERS):
            return PlainTextResponse(LOCAL_ONLY, 403)
        return await call_next(request)

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

    # ---------------------------------------------------------------- sign in
    def cookie_options(path: str = "/") -> dict[str, object]:
        # Lax, not Strict: the provider sends the browser back here with a cross site
        # GET, and the login cookie must come with it.
        return {"httponly": True, "secure": auth.secure_cookies, "samesite": "lax", "path": path}

    def sign_in_on() -> OidcClient:
        if provider is None:
            raise HTTPException(404, SIGN_IN_OFF)
        return provider

    def describe(person: Principal) -> dict[str, object]:
        return {
            "auth": auth.mode,
            "name": person.name,
            "email": person.email,
            "platform_admin": person.platform_admin,
            "can_manage": person.can_manage,
            "roles": person.roles,
            # Only the local console can act as another role.
            "view_as": None if auth.enabled else viewing[0].model_dump(),
        }

    @app.get("/api/me")
    def me(person: Principal = Depends(who)) -> dict[str, object]:
        return describe(person)

    @app.put("/api/view-as", dependencies=writes)
    def view_as(item: ViewAs) -> dict[str, object]:
        """Act as another role, to show it in a demo. Not there with sign in on."""
        if auth.enabled:
            raise HTTPException(404, "With sign in on, a role comes from each person's account")
        if item.company is not None:
            company_call(lambda: companies.workspace(item.company or ""))
        viewing[0] = item
        return describe(item.principal())

    @app.get("/api/auth/login")
    def login() -> RedirectResponse:
        client = sign_in_on()
        try:
            url, state = client.start()
        except AuthError as exc:
            raise HTTPException(exc.status, str(exc)) from exc
        response = RedirectResponse(url, status_code=302)
        response.set_cookie(
            LOGIN_COOKIE, state, max_age=LOGIN_SECONDS, **cookie_options("/api/auth")
        )
        return response

    @app.get("/api/auth/callback", response_model=None)
    def callback(
        request: Request,
        code: str | None = Query(None, max_length=4096),
        state: str | None = Query(None, max_length=512),
        error: str | None = Query(None, max_length=200),
    ) -> Response:
        client = sign_in_on()
        if error or not code or not state:
            # The provider's own words are not shown: they arrive in the URL, from anyone.
            return PlainTextResponse(
                "Sign in did not finish. Go back to the console and try again.", 400
            )
        try:
            session = client.finish(code, state, request.cookies.get(LOGIN_COOKIE))
        except AuthError as exc:
            return PlainTextResponse(f"Sign in failed: {exc}", exc.status)
        response = RedirectResponse(auth.console_url.rstrip("/") + "/#/", status_code=302)
        response.set_cookie(
            SESSION_COOKIE,
            sign(session, auth.session_secret, auth.session_hours * 3600),
            max_age=auth.session_hours * 3600,
            **cookie_options(),
        )
        response.delete_cookie(LOGIN_COOKIE, path="/api/auth")
        return response

    @app.post("/api/auth/logout", dependencies=writes)
    def logout(response: Response) -> dict[str, str]:
        client = sign_in_on()
        response.delete_cookie(SESSION_COOKIE, path="/")
        return {"redirect": client.logout_url() or auth.console_url}

    # ---------------------------------------------------------------- companies
    @app.get("/api/companies")
    def companies_list(person: Principal = Depends(who)) -> dict[str, object]:
        return companies.listing(person).model_dump()

    @app.put("/api/companies/active", dependencies=writes)
    def companies_pick(item: Pick, person: Principal = Depends(who)) -> dict[str, object]:
        listing = company_call(lambda: companies.pick(item.slug, person))
        warm(company_call(lambda: context(item.slug)))
        return listing.model_dump()

    @app.post("/api/companies", status_code=201, dependencies=[*writes, Depends(require_manager)])
    def companies_create(item: CompanyIn, person: Principal = Depends(who)) -> dict[str, object]:
        return company_call(lambda: companies.create(item, person)).model_dump()

    # ---------------------------------------------------------------- brand
    @app.get("/api/brand")
    def brand(ctx: CompanyContext = Depends(shown)) -> dict[str, object]:
        """Read on each call, so an edited brand file shows on the next page load."""
        return brand_call(ctx.brands.load).model_dump()

    @app.get("/api/brand/assets/{kind}")
    def brand_asset(kind: AssetKind, ctx: CompanyContext = Depends(shown)) -> FileResponse:
        path = brand_call(lambda: ctx.brands.asset(kind))
        return FileResponse(path, media_type="image/png")

    @app.post("/api/brand/preview", dependencies=writes)
    def brand_preview(item: BrandIn, _: CompanyContext = Depends(shown)) -> dict[str, object]:
        return BrandStore.preview(item).model_dump()

    @app.put("/api/brand", dependencies=company_writes)
    def brand_save(item: BrandIn, ctx: CompanyContext = Depends(shown)) -> dict[str, object]:
        return brand_call(lambda: ctx.brands.save(item)).model_dump()

    @app.put("/api/brand/assets/{kind}", dependencies=company_writes)
    async def brand_asset_save(
        kind: AssetKind,
        request: Request,
        content_type: str | None = Header(None),
        ctx: CompanyContext = Depends(shown),
    ) -> dict[str, object]:
        if content_type != "image/png":
            raise HTTPException(415, "Send the image as image/png")
        brands = ctx.brands  # the company the header named, before the body arrives
        # Read no more than the limit allows, whatever Content-Length claims.
        data = bytearray()
        async for chunk in request.stream():
            data.extend(chunk)
            if len(data) > MAX_IMAGE_BYTES:
                raise HTTPException(413, f"The image is over {MAX_IMAGE_BYTES // 1048576} MB")
        return brand_call(lambda: brands.save_asset(kind, bytes(data))).model_dump()

    # ---------------------------------------------------------------- pipeline output
    @app.get("/api/summary")
    def summary(ctx: CompanyContext = Depends(shown)) -> dict[str, object]:
        return build_summary(ctx.settings)

    @app.get("/api/runs")
    def runs(
        component: str | None = None,
        limit: int = Query(50, ge=1, le=MAX_LIMIT),
        ctx: CompanyContext = Depends(shown),
    ) -> list[dict[str, object]]:
        found = [r for r in collect_runs(ctx.settings) if component in (None, r.component)]
        return [r.to_dict() for r in reversed(found[-limit:])]

    @app.get("/api/runs/{ident}")
    def run(
        ident: str = PathParam(pattern=RUN_PATTERN), ctx: CompanyContext = Depends(shown)
    ) -> dict[str, object]:
        found = find_run(ctx.settings, ident)
        if found is None:
            raise HTTPException(404, f"No run {ident}")
        return run_detail(ctx.settings, *found)

    @app.get("/api/cves")
    def cves(ctx: CompanyContext = Depends(shown)) -> dict[str, object]:
        out_dir = ctx.settings.out_dir
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
        ctx: CompanyContext = Depends(shown),
    ) -> list[dict[str, object]]:
        items = scan(ctx.settings.out_dir, load_rules(settings.scripts_dir))
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
    def deliverable_html(
        ident: str = PathParam(pattern=ID_PATTERN), ctx: CompanyContext = Depends(shown)
    ) -> dict[str, object]:
        match, path = find(ident, ctx.settings.out_dir)
        rendered = render_docx(path)
        return {
            **match.to_dict(),
            "html": rendered.html,
            "warnings": rendered.warnings,
            "pdf": has_word,
        }

    @app.get("/api/deliverables/{ident}/file")
    def deliverable_file(
        ident: str = PathParam(pattern=ID_PATTERN), ctx: CompanyContext = Depends(shown)
    ) -> FileResponse:
        _, path = find(ident, ctx.settings.out_dir)
        return FileResponse(path, media_type=DOCX_TYPE, filename=path.name)

    def branded_pdf(ident: str, ctx: CompanyContext) -> tuple[Path, Path]:
        """The report's .docx and its cached PDF, made now if this version has none."""
        if not has_word:
            raise HTTPException(503, "Microsoft Word is not available to make the PDF")
        _, path = find(ident, ctx.settings.out_dir)
        try:
            return path, ctx.pdfs.get(ident, path)
        except PdfError as exc:
            raise HTTPException(exc.status, str(exc)) from exc

    @app.get("/api/deliverables/{ident}/pdf/ready")
    def deliverable_pdf_ready(
        ident: str = PathParam(pattern=ID_PATTERN), ctx: CompanyContext = Depends(shown)
    ) -> dict[str, object]:
        """Makes the PDF if needed, so the page can show progress before it frames it."""
        _, pdf = branded_pdf(ident, ctx)
        return {"id": ident, "bytes": pdf.stat().st_size}

    @app.get("/api/deliverables/{ident}/pdf")
    def deliverable_pdf(
        ident: str = PathParam(pattern=ID_PATTERN),
        download: bool = False,
        ctx: CompanyContext = Depends(shown),
    ) -> FileResponse:
        source, pdf = branded_pdf(ident, ctx)
        return FileResponse(
            pdf,
            media_type="application/pdf",
            filename=source.with_suffix(".pdf").name,
            content_disposition_type="attachment" if download else "inline",
            headers={"Content-Security-Policy": PDF_CSP},
        )

    # ---------------------------------------------------------------- stakeholders
    @app.get("/api/stakeholders")
    def stakeholders(ctx: CompanyContext = Depends(shown)) -> dict[str, object]:
        people = store_call(ctx.store.load)
        return {
            "exists": ctx.store.exists(),
            "has_example": ctx.store.example.is_file(),
            "stakeholders": [p.model_dump() for p in people],
        }

    @app.post("/api/stakeholders", status_code=201, dependencies=company_writes)
    def stakeholder_add(
        item: StakeholderIn, ctx: CompanyContext = Depends(shown)
    ) -> dict[str, object]:
        return store_call(lambda: ctx.store.add(item)).model_dump()

    @app.put("/api/stakeholders/{ident}", dependencies=company_writes)
    def stakeholder_update(
        item: StakeholderIn,
        ident: str = PathParam(pattern=STAKEHOLDER_PATTERN),
        ctx: CompanyContext = Depends(shown),
    ) -> dict[str, object]:
        return store_call(lambda: ctx.store.update(ident, item)).model_dump()

    @app.delete("/api/stakeholders/{ident}", status_code=204, dependencies=company_writes)
    def stakeholder_remove(
        ident: str = PathParam(pattern=STAKEHOLDER_PATTERN), ctx: CompanyContext = Depends(shown)
    ) -> Response:
        store_call(lambda: ctx.store.remove(ident))
        return Response(status_code=204)

    @app.post("/api/stakeholders/start-from-example", status_code=201, dependencies=company_writes)
    def stakeholders_from_example(ctx: CompanyContext = Depends(shown)) -> dict[str, object]:
        people = store_call(ctx.store.start_from_example)
        return {"stakeholders": [p.model_dump() for p in people]}

    @app.get("/api/audience")
    def audience(ctx: CompanyContext = Depends(shown)) -> dict[str, object]:
        """Teams each report names, the stakeholders who match, and teams nobody covers."""
        return audience_view(ctx.settings.out_dir, store_call(ctx.store.load))

    return app
