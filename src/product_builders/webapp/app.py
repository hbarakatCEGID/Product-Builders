"""FastAPI application — landing, docs, catalog, onboarding, CLI install."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from product_builders import __version__
from product_builders.webapp import services as web_services
from product_builders.webapp.routes_api import router as api_router

_WEBAPP_DIR = Path(__file__).resolve().parent

_DOC_LABELS: dict[str, str] = {
    "getting-started": "Getting started",
    "cli": "CLI overview",
    "governance": "Governance model",
}


def _profiles_dir() -> Path:
    return web_services.profiles_dir_resolved()


def _template_ctx(request: Request, **extra: object) -> dict[str, object]:
    return {"request": request, "version": __version__, **extra}


def create_app() -> FastAPI:
    app = FastAPI(
        title="Product Builders",
        description="Cursor rules, hooks, and onboarding from your codebase.",
        version=__version__,
        docs_url="/api/docs",
        redoc_url=None,
    )

    templates = Jinja2Templates(directory=str(_WEBAPP_DIR / "templates"))
    static_dir = _WEBAPP_DIR / "static"
    if static_dir.is_dir():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    app.include_router(api_router)

    @app.get("/", response_class=HTMLResponse)
    def home(request: Request) -> HTMLResponse:
        return templates.TemplateResponse(
            request,
            "index.html",
            _template_ctx(request, title="Product Builders"),
        )

    @app.get("/download", response_class=HTMLResponse)
    def download(request: Request) -> HTMLResponse:
        return templates.TemplateResponse(
            request,
            "download.html",
            _template_ctx(request, title="Install CLI — Product Builders"),
        )

    @app.get("/docs", response_class=HTMLResponse)
    def docs_index(request: Request) -> HTMLResponse:
        slugs = web_services.packaged_doc_slugs()
        doc_pages = [
            (s, _DOC_LABELS.get(s, s.replace("-", " ").title())) for s in slugs
        ]
        return templates.TemplateResponse(
            request,
            "docs/index.html",
            _template_ctx(request, title="Documentation", doc_pages=doc_pages),
        )

    @app.get("/docs/{slug}", response_class=HTMLResponse)
    def docs_page(request: Request, slug: str) -> HTMLResponse:
        try:
            md = web_services.read_packaged_doc(slug)
        except (ValueError, FileNotFoundError) as e:
            raise HTTPException(status_code=404, detail="Documentation page not found.") from e
        body_html = web_services.render_markdown_to_html(md)
        doc_title = _DOC_LABELS.get(slug, slug.replace("-", " ").title())
        return templates.TemplateResponse(
            request,
            "docs/page.html",
            _template_ctx(
                request,
                title=doc_title,
                doc_title=doc_title,
                body_html=body_html,
            ),
        )

    @app.get("/products", response_class=HTMLResponse)
    def catalog(request: Request) -> HTMLResponse:
        products = web_services.list_products(_profiles_dir())
        return templates.TemplateResponse(
            request,
            "catalog.html",
            _template_ctx(request, title="Product catalog", products=products),
        )

    @app.get("/products/{product_name}", response_class=HTMLResponse)
    def product_detail(request: Request, product_name: str) -> HTMLResponse:
        product = web_services.get_product_summary(_profiles_dir(), product_name)
        if product is None:
            raise HTTPException(status_code=404, detail="Product not found.")
        onboarding_roles = []
        try:
            pd = web_services.safe_product_dir(_profiles_dir(), product_name)
            onboarding_roles = web_services.list_onboarding_roles(pd)
        except (ValueError, FileNotFoundError):
            onboarding_roles = []
        return templates.TemplateResponse(
            request,
            "product.html",
            _template_ctx(
                request,
                title=product.name,
                product=product,
                onboarding_roles=onboarding_roles,
            ),
        )

    @app.get(
        "/products/{product_name}/onboarding/{role}",
        response_class=HTMLResponse,
    )
    def onboarding_page(
        request: Request,
        product_name: str,
        role: str,
    ) -> HTMLResponse:
        try:
            md = web_services.read_onboarding_markdown(_profiles_dir(), product_name, role)
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e)) from e
        except FileNotFoundError as e:
            raise HTTPException(status_code=404, detail="Onboarding guide not found.") from e
        body_html = web_services.render_markdown_to_html(md)
        role_label = role.replace("_", " ").title()
        return templates.TemplateResponse(
            request,
            "onboarding.html",
            _template_ctx(
                request,
                title=f"Onboarding — {product_name}",
                product_name=product_name,
                role_label=role_label,
                body_html=body_html,
            ),
        )

    @app.get("/api/products")
    def api_products() -> list[dict[str, object]]:
        products = web_services.list_products(_profiles_dir())
        return [
            {
                "name": p.name,
                "description": p.description,
                "primary_language": p.primary_language,
                "analysis_timestamp": p.analysis_timestamp,
                "has_analysis": p.has_analysis,
            }
            for p in products
        ]

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "version": __version__}

    # --- Operations dashboard ---

    @app.get("/operations", response_class=HTMLResponse)
    def operations(request: Request, command: str | None = None, name: str | None = None) -> HTMLResponse:
        return templates.TemplateResponse(
            request,
            "operations.html",
            _template_ctx(
                request,
                title="Operations — Product Builders",
                preselect_command=command,
                preselect_name=name,
            ),
        )

    # Partial form routes for htmx tab swapping
    _form_templates = {
        "analyze": "partials/form_analyze.html",
        "generate": "partials/form_generate.html",
        "export": "partials/form_export.html",
        "setup": "partials/form_setup.html",
        "check-drift": "partials/form_check_drift.html",
        "feedback": "partials/form_feedback.html",
    }

    @app.get("/partials/form/{command}", response_class=HTMLResponse)
    def form_partial(request: Request, command: str) -> HTMLResponse:
        template_name = _form_templates.get(command)
        if not template_name:
            raise HTTPException(status_code=404, detail="Unknown command")
        return templates.TemplateResponse(request, template_name, {"request": request})

    return app


app = create_app()
