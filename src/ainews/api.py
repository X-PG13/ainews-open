from __future__ import annotations

import logging
import time
import uuid
from pathlib import Path
from typing import Any, List, Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import __version__
from .config import load_settings
from .logging_utils import configure_logging
from .service import NewsService


class IngestRequest(BaseModel):
    source_ids: Optional[List[str]] = None
    max_items_per_source: Optional[int] = Field(default=None, ge=1, le=200)


class EnrichRequest(BaseModel):
    source_ids: Optional[List[str]] = None
    article_ids: Optional[List[int]] = None
    since_hours: Optional[int] = Field(default=None, ge=1, le=720)
    limit: int = Field(default=20, ge=1, le=200)
    force: bool = False


class ExtractRequest(BaseModel):
    source_ids: Optional[List[str]] = None
    article_ids: Optional[List[int]] = None
    since_hours: Optional[int] = Field(default=None, ge=1, le=720)
    limit: int = Field(default=20, ge=1, le=200)
    force: bool = False


class DigestRequest(BaseModel):
    region: str = Field(default="all")
    since_hours: Optional[int] = Field(default=None, ge=1, le=720)
    limit: int = Field(default=30, ge=1, le=200)
    use_llm: bool = True
    persist: bool = True


class PipelineRequest(BaseModel):
    region: str = Field(default="all")
    since_hours: Optional[int] = Field(default=None, ge=1, le=720)
    limit: int = Field(default=30, ge=1, le=200)
    max_items_per_source: Optional[int] = Field(default=None, ge=1, le=200)
    use_llm: bool = True
    persist: bool = True
    export: bool = True
    publish: bool = False
    publish_targets: Optional[List[str]] = None
    wechat_submit: Optional[bool] = None
    force_republish: bool = False


class PublishRequest(BaseModel):
    digest_id: Optional[int] = Field(default=None, ge=1)
    region: str = Field(default="all")
    since_hours: Optional[int] = Field(default=None, ge=1, le=720)
    limit: int = Field(default=30, ge=1, le=200)
    use_llm: bool = True
    persist: bool = True
    export: bool = False
    targets: Optional[List[str]] = None
    wechat_submit: Optional[bool] = None
    force_republish: bool = False


class RefreshPublicationsRequest(BaseModel):
    publication_ids: Optional[List[int]] = None
    digest_id: Optional[int] = Field(default=None, ge=1)
    target: Optional[str] = None
    limit: int = Field(default=20, ge=1, le=100)
    only_pending: bool = True


class ArticleCurationRequest(BaseModel):
    is_hidden: Optional[bool] = None
    is_pinned: Optional[bool] = None
    editorial_note: Optional[str] = Field(default=None, max_length=500)


logger = logging.getLogger("ainews.api")
SANITIZED_ERROR_MESSAGE = "operation failed; inspect server logs with the response X-Request-ID"
BAD_REQUEST_MESSAGE = "request could not be processed; inspect server logs with the response X-Request-ID"
NOT_FOUND_MESSAGE = "requested resource was not found"


def _sanitize_service_payload(payload: Any, *, error_context: bool = False) -> Any:
    if isinstance(payload, list):
        return [
            _sanitize_service_payload(item, error_context=error_context) for item in payload
        ]

    if not isinstance(payload, dict):
        return payload

    status = str(payload.get("status", "")).strip().lower()
    dict_error_context = error_context or status == "error"
    sanitized: dict[str, Any] = {}
    for key, value in payload.items():
        if key == "error" and isinstance(value, str) and value.strip():
            sanitized[key] = SANITIZED_ERROR_MESSAGE
            continue
        if key.endswith("_error"):
            if isinstance(value, str) and value.strip():
                sanitized[key] = SANITIZED_ERROR_MESSAGE
                continue
            sanitized[key] = _sanitize_service_payload(value, error_context=True)
            continue
        if key == "message" and dict_error_context and isinstance(value, str) and value.strip():
            sanitized[key] = SANITIZED_ERROR_MESSAGE
            continue
        child_error_context = dict_error_context or key.endswith("_error")
        sanitized[key] = _sanitize_service_payload(value, error_context=child_error_context)
    return sanitized


def _request_id_from_state(request: Request) -> str:
    return str(getattr(request.state, "request_id", "") or "")


def _error_response(status_code: int, detail: str, headers: Optional[dict[str, str]] = None) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"detail": detail},
        headers=headers,
    )


def _sanitize_http_exception(exc: HTTPException) -> JSONResponse:
    detail = SANITIZED_ERROR_MESSAGE
    if exc.status_code == 404:
        detail = NOT_FOUND_MESSAGE
    elif 400 <= exc.status_code < 500:
        detail = BAD_REQUEST_MESSAGE
    return _error_response(exc.status_code, detail, headers=exc.headers)


def _run_service_action(
    request: Request,
    action_name: str,
    runner,
) -> Any:
    request_id = _request_id_from_state(request)
    try:
        return _sanitize_service_payload(runner())
    except HTTPException as exc:
        logger.warning(
            "service action returned an http error",
            extra={
                "event": "api.action_http_error",
                "action": action_name,
                "request_id": request_id,
                "status_code": exc.status_code,
            },
        )
        return _sanitize_http_exception(exc)
    except LookupError:
        logger.warning(
            "requested resource was not found",
            extra={
                "event": "api.action_not_found",
                "action": action_name,
                "request_id": request_id,
            },
        )
        return _error_response(404, NOT_FOUND_MESSAGE)
    except ValueError:
        logger.warning(
            "request could not be processed",
            extra={
                "event": "api.action_bad_request",
                "action": action_name,
                "request_id": request_id,
            },
        )
        return _error_response(400, BAD_REQUEST_MESSAGE)
    except Exception:
        logger.exception(
            "service action failed",
            extra={
                "event": "api.action_error",
                "action": action_name,
                "request_id": request_id,
            },
        )
        return _error_response(500, SANITIZED_ERROR_MESSAGE)


def create_app() -> FastAPI:
    settings = load_settings()
    configure_logging(level=settings.log_level, log_format=settings.log_format)
    service = NewsService(settings)
    web_dir = Path(__file__).resolve().parent / "web"

    app = FastAPI(
        title="AI News Open",
        version=__version__,
        description="Daily domestic and international AI news aggregation API.",
    )

    allow_origins = [
        origin.strip() for origin in settings.allowed_origins.split(",") if origin.strip()
    ] or ["*"]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.mount("/assets", StaticFiles(directory=web_dir), name="assets")

    @app.middleware("http")
    async def request_logging(request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:12]
        request.state.request_id = request_id
        started = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            duration_ms = round((time.perf_counter() - started) * 1000, 2)
            logger.exception(
                "request failed",
                extra={
                    "event": "http.request_error",
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": duration_ms,
                },
            )
            response = _error_response(500, SANITIZED_ERROR_MESSAGE)
            response.headers["X-Request-ID"] = request_id
            return response

        duration_ms = round((time.perf_counter() - started) * 1000, 2)
        response.headers["X-Request-ID"] = request_id
        logger.info(
            "request completed",
            extra={
                "event": "http.request",
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
            },
        )
        return response

    def require_admin(
        x_admin_token: Optional[str] = Header(default=None),
    ) -> None:
        if settings.admin_token and x_admin_token != settings.admin_token:
            raise HTTPException(status_code=401, detail="invalid admin token")

    def curate_article_payload(article_id: int, payload: ArticleCurationRequest) -> dict[str, Any]:
        article = service.curate_article(
            article_id,
            is_hidden=payload.is_hidden,
            is_pinned=payload.is_pinned,
            editorial_note=payload.editorial_note,
        )
        if article is None:
            raise LookupError("article not found")
        return {"article": article}

    @app.get("/", include_in_schema=False)
    def index() -> FileResponse:
        return FileResponse(web_dir / "index.html")

    @app.get("/health")
    def health(request: Request) -> dict:
        return _run_service_action(
            request,
            "health",
            lambda: {
                **service.get_health(),
                "version": __version__,
            },
        )

    @app.get("/sources")
    def list_sources(request: Request) -> dict:
        return _run_service_action(
            request,
            "list_sources",
            lambda: {"sources": service.list_sources()},
        )

    @app.post("/ingest")
    def ingest(
        request: Request,
        source_id: Optional[List[str]] = Query(default=None),
        max_items_per_source: Optional[int] = Query(default=None, ge=1, le=200),
        _: None = Depends(require_admin),
    ) -> dict:
        return _run_service_action(
            request,
            "ingest",
            lambda: service.ingest(
                source_ids=source_id,
                max_items_per_source=max_items_per_source,
            ),
        )

    @app.get("/articles")
    def list_articles(
        request: Request,
        region: str = Query(default="all"),
        language: Optional[str] = Query(default=None),
        source_id: Optional[str] = Query(default=None),
        since_hours: int = Query(default=settings.default_lookback_hours, ge=1, le=720),
        limit: int = Query(default=50, ge=1, le=200),
    ) -> dict:
        return _run_service_action(
            request,
            "list_articles",
            lambda: {
                "articles": service.list_articles(
                    region=region,
                    language=language,
                    source_id=source_id,
                    since_hours=since_hours,
                    limit=limit,
                    include_hidden=False,
                )
            },
        )

    @app.get("/digest/daily")
    def digest_daily(
        request: Request,
        region: str = Query(default="all"),
        since_hours: int = Query(default=settings.default_lookback_hours, ge=1, le=720),
        limit: int = Query(default=50, ge=1, le=200),
        use_llm: bool = Query(default=False),
    ) -> dict:
        return _run_service_action(
            request,
            "digest_daily",
            lambda: service.build_digest(
                region=region,
                since_hours=since_hours,
                limit=limit,
                use_llm=use_llm,
                persist=False,
            ),
        )

    @app.get("/admin/stats")
    def admin_stats(request: Request, _: None = Depends(require_admin)) -> dict:
        return _run_service_action(
            request,
            "admin_stats",
            service.get_stats,
        )

    @app.get("/admin/operations")
    def admin_operations(request: Request, _: None = Depends(require_admin)) -> dict:
        return _run_service_action(
            request,
            "admin_operations",
            service.get_operations,
        )

    @app.get("/admin/articles")
    def admin_articles(
        request: Request,
        region: str = Query(default="all"),
        language: Optional[str] = Query(default=None),
        source_id: Optional[str] = Query(default=None),
        since_hours: int = Query(default=settings.default_lookback_hours, ge=1, le=720),
        limit: int = Query(default=100, ge=1, le=200),
        include_hidden: bool = Query(default=True),
        _: None = Depends(require_admin),
    ) -> dict:
        return _run_service_action(
            request,
            "admin_articles",
            lambda: {
                "articles": service.list_articles(
                    region=region,
                    language=language,
                    source_id=source_id,
                    since_hours=since_hours,
                    limit=limit,
                    include_hidden=include_hidden,
                )
            },
        )

    @app.post("/admin/ingest")
    def admin_ingest(
        payload: IngestRequest,
        request: Request,
        _: None = Depends(require_admin),
    ) -> dict:
        return _run_service_action(
            request,
            "admin_ingest",
            lambda: service.ingest(
                source_ids=payload.source_ids,
                max_items_per_source=payload.max_items_per_source,
            ),
        )

    @app.post("/admin/enrich")
    def admin_enrich(
        payload: EnrichRequest,
        request: Request,
        _: None = Depends(require_admin),
    ) -> dict:
        return _run_service_action(
            request,
            "admin_enrich",
            lambda: service.enrich_articles(
                source_ids=payload.source_ids,
                article_ids=payload.article_ids,
                since_hours=payload.since_hours,
                limit=payload.limit,
                force=payload.force,
            ),
        )

    @app.post("/admin/extract")
    def admin_extract(
        payload: ExtractRequest,
        request: Request,
        _: None = Depends(require_admin),
    ) -> dict:
        return _run_service_action(
            request,
            "admin_extract",
            lambda: service.extract_articles(
                source_ids=payload.source_ids,
                article_ids=payload.article_ids,
                since_hours=payload.since_hours,
                limit=payload.limit,
                force=payload.force,
            ),
        )

    @app.post("/admin/digests/generate")
    def admin_generate_digest(
        payload: DigestRequest,
        request: Request,
        _: None = Depends(require_admin),
    ) -> dict:
        return _run_service_action(
            request,
            "admin_generate_digest",
            lambda: service.build_digest(
                region=payload.region,
                since_hours=payload.since_hours,
                limit=payload.limit,
                use_llm=payload.use_llm,
                persist=payload.persist,
            ),
        )

    @app.post("/admin/pipeline")
    def admin_pipeline(
        payload: PipelineRequest,
        request: Request,
        _: None = Depends(require_admin),
    ) -> dict:
        return _run_service_action(
            request,
            "admin_pipeline",
            lambda: service.run_pipeline(
                region=payload.region,
                since_hours=payload.since_hours,
                limit=payload.limit,
                max_items_per_source=payload.max_items_per_source,
                use_llm=payload.use_llm,
                persist=payload.persist,
                export=payload.export,
                publish=payload.publish,
                publish_targets=payload.publish_targets,
                wechat_submit=payload.wechat_submit,
                force_republish=payload.force_republish,
            ),
        )

    @app.post("/admin/publish")
    def admin_publish(
        payload: PublishRequest,
        request: Request,
        _: None = Depends(require_admin),
    ) -> dict:
        return _run_service_action(
            request,
            "admin_publish",
            lambda: service.publish_digest(
                digest_id=payload.digest_id,
                region=payload.region,
                since_hours=payload.since_hours,
                limit=payload.limit,
                use_llm=payload.use_llm,
                persist=payload.persist,
                export=payload.export,
                targets=payload.targets,
                wechat_submit=payload.wechat_submit,
                force_republish=payload.force_republish,
            ),
        )

    @app.get("/admin/digests")
    def admin_digests(
        request: Request,
        region: str = Query(default="all"),
        limit: int = Query(default=20, ge=1, le=100),
        _: None = Depends(require_admin),
    ) -> dict:
        return _run_service_action(
            request,
            "admin_digests",
            lambda: {"digests": service.list_digests(region=region, limit=limit)},
        )

    @app.get("/admin/publications")
    def admin_publications(
        request: Request,
        digest_id: Optional[int] = Query(default=None, ge=1),
        target: Optional[str] = Query(default=None),
        status: Optional[str] = Query(default=None),
        limit: int = Query(default=20, ge=1, le=100),
        _: None = Depends(require_admin),
    ) -> dict:
        return _run_service_action(
            request,
            "admin_publications",
            lambda: {
                "publications": service.list_publications(
                    digest_id=digest_id,
                    target=target,
                    status=status,
                    limit=limit,
                )
            },
        )

    @app.post("/admin/publications/refresh")
    def admin_refresh_publications(
        payload: RefreshPublicationsRequest,
        request: Request,
        _: None = Depends(require_admin),
    ) -> dict:
        return _run_service_action(
            request,
            "admin_refresh_publications",
            lambda: service.refresh_publications(
                publication_ids=payload.publication_ids,
                digest_id=payload.digest_id,
                target=payload.target,
                limit=payload.limit,
                only_pending=payload.only_pending,
            ),
        )

    @app.patch("/admin/articles/{article_id}")
    def admin_curate_article(
        article_id: int,
        payload: ArticleCurationRequest,
        request: Request,
        _: None = Depends(require_admin),
    ) -> dict:
        return _run_service_action(
            request,
            "admin_curate_article",
            lambda: curate_article_payload(article_id, payload),
        )

    return app
