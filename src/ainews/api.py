from __future__ import annotations

import logging
import time
import uuid
from pathlib import Path
from typing import Any, List, Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from starlette.exceptions import HTTPException as StarletteHTTPException

from . import __version__
from .config import load_settings
from .logging_utils import configure_logging
from .metrics import render_metrics
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


class RetryExtractionRequest(BaseModel):
    source_ids: Optional[List[str]] = None
    article_ids: Optional[List[int]] = None
    since_hours: Optional[int] = Field(default=None, ge=1, le=720)
    extraction_status: Optional[str] = None
    extraction_error_category: Optional[str] = None
    due_only: bool = False
    limit: int = Field(default=20, ge=1, le=200)


class DigestRequest(BaseModel):
    region: str = Field(default="all")
    since_hours: Optional[int] = Field(default=None, ge=1, le=720)
    limit: int = Field(default=30, ge=1, le=200)
    use_llm: bool = True
    persist: bool = True


class DigestEditorItemRequest(BaseModel):
    article_id: int = Field(ge=1)
    selected: bool = True
    manual_rank: Optional[int] = Field(default=None, ge=1, le=999)
    section_override: Optional[str] = Field(default=None, max_length=80)
    publish_title_override: Optional[str] = Field(default=None, max_length=300)
    publish_summary_override: Optional[str] = Field(default=None, max_length=1000)


class DigestSnapshotRequest(BaseModel):
    region: str = Field(default="all")
    article_ids: Optional[List[int]] = None
    since_hours: Optional[int] = Field(default=None, ge=1, le=720)
    limit: int = Field(default=30, ge=1, le=200)
    use_llm: bool = True
    editor_items: Optional[List[DigestEditorItemRequest]] = None
    actor: Optional[str] = Field(default=None, max_length=80)
    change_summary: Optional[str] = Field(default=None, max_length=240)


class DigestEditorUpdateRequest(BaseModel):
    editor_items: List[DigestEditorItemRequest] = Field(min_length=1)
    actor: Optional[str] = Field(default=None, max_length=80)
    change_summary: Optional[str] = Field(default=None, max_length=240)


class DigestRollbackRequest(BaseModel):
    version: int = Field(ge=1)
    actor: Optional[str] = Field(default=None, max_length=80)
    change_summary: Optional[str] = Field(default=None, max_length=240)


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


class PublishPreviewRequest(BaseModel):
    digest_id: Optional[int] = Field(default=None, ge=1)
    region: str = Field(default="all")
    since_hours: Optional[int] = Field(default=None, ge=1, le=720)
    limit: int = Field(default=30, ge=1, le=200)
    use_llm: bool = True
    targets: Optional[List[str]] = None


class RefreshPublicationsRequest(BaseModel):
    publication_ids: Optional[List[int]] = None
    digest_id: Optional[int] = Field(default=None, ge=1)
    target: Optional[str] = None
    limit: int = Field(default=20, ge=1, le=100)
    only_pending: bool = True


class ArticleCurationRequest(BaseModel):
    is_hidden: Optional[bool] = None
    is_pinned: Optional[bool] = None
    is_suppressed: Optional[bool] = None
    must_include: Optional[bool] = None
    editorial_note: Optional[str] = Field(default=None, max_length=500)


class ResetSourceCooldownRequest(BaseModel):
    source_ids: Optional[List[str]] = None
    active_only: bool = True


class AcknowledgeSourceAlertRequest(BaseModel):
    source_ids: List[str] = Field(min_length=1)
    note: Optional[str] = Field(default=None, max_length=280)


class SnoozeSourceAlertRequest(BaseModel):
    source_ids: List[str] = Field(min_length=1)
    minutes: Optional[int] = Field(default=60, ge=1, le=10080)
    clear: bool = False


class SourceMaintenanceRequest(BaseModel):
    source_ids: List[str] = Field(min_length=1)
    enabled: bool = True


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


def _request_action_name(request: Request) -> str:
    return str(getattr(request.state, "action_name", "") or "")


def _log_api_warning(request: Request, *, event: str, message: str, status_code: int) -> None:
    logger.warning(
        message,
        extra={
            "event": event,
            "action": _request_action_name(request),
            "request_id": _request_id_from_state(request),
            "status_code": status_code,
        },
    )


def _log_api_exception(request: Request, *, event: str, message: str) -> None:
    logger.exception(
        message,
        extra={
            "event": event,
            "action": _request_action_name(request),
            "request_id": _request_id_from_state(request),
        },
    )


def _begin_route_action(request: Request, action_name: str) -> None:
    request.state.action_name = action_name


def _handle_route_http_exception(request: Request, exc: HTTPException) -> JSONResponse:
    _log_api_warning(
        request,
        event="api.action_http_error",
        message="service action returned an http error",
        status_code=exc.status_code,
    )
    return _sanitize_http_exception(exc)


def _handle_route_lookup_error(request: Request) -> JSONResponse:
    _log_api_warning(
        request,
        event="api.action_not_found",
        message="requested resource was not found",
        status_code=404,
    )
    return _error_response(404, NOT_FOUND_MESSAGE)


def _handle_route_value_error(request: Request) -> JSONResponse:
    _log_api_warning(
        request,
        event="api.action_bad_request",
        message="request could not be processed",
        status_code=400,
    )
    return _error_response(400, BAD_REQUEST_MESSAGE)


def _handle_route_unexpected_error(request: Request) -> JSONResponse:
    _log_api_exception(
        request,
        event="api.action_error",
        message="service action failed",
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

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        _log_api_warning(
            request,
            event="api.action_http_error",
            message="service action returned an http error",
            status_code=exc.status_code,
        )
        return _sanitize_http_exception(
            HTTPException(status_code=exc.status_code, detail=exc.detail, headers=exc.headers)
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        _log_api_warning(
            request,
            event="api.action_validation_error",
            message="request validation failed",
            status_code=422,
        )
        return _error_response(422, BAD_REQUEST_MESSAGE)

    @app.exception_handler(LookupError)
    async def handle_lookup_error(request: Request, exc: LookupError) -> JSONResponse:
        _log_api_warning(
            request,
            event="api.action_not_found",
            message="requested resource was not found",
            status_code=404,
        )
        return _error_response(404, NOT_FOUND_MESSAGE)

    @app.exception_handler(ValueError)
    async def handle_value_error(request: Request, exc: ValueError) -> JSONResponse:
        _log_api_warning(
            request,
            event="api.action_bad_request",
            message="request could not be processed",
            status_code=400,
        )
        return _error_response(400, BAD_REQUEST_MESSAGE)

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        _log_api_exception(
            request,
            event="api.action_error",
            message="service action failed",
        )
        return _error_response(500, SANITIZED_ERROR_MESSAGE)

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
            is_suppressed=payload.is_suppressed,
            must_include=payload.must_include,
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
        _begin_route_action(request, "health")
        try:
            return _sanitize_service_payload({
                **service.get_health(),
                "version": __version__,
            })
        except HTTPException as exc:
            return _handle_route_http_exception(request, exc)
        except LookupError:
            return _handle_route_lookup_error(request)
        except ValueError:
            return _handle_route_value_error(request)
        except Exception:
            return _handle_route_unexpected_error(request)

    @app.get("/metrics", include_in_schema=False)
    def metrics(request: Request) -> PlainTextResponse:
        _begin_route_action(request, "metrics")
        try:
            payload = service.get_metrics_snapshot()
            return PlainTextResponse(
                render_metrics(payload),
                media_type="text/plain; version=0.0.4; charset=utf-8",
            )
        except HTTPException as exc:
            return _handle_route_http_exception(request, exc)
        except LookupError:
            return _handle_route_lookup_error(request)
        except ValueError:
            return _handle_route_value_error(request)
        except Exception:
            return _handle_route_unexpected_error(request)

    @app.get("/sources")
    def list_sources(request: Request) -> dict:
        _begin_route_action(request, "list_sources")
        try:
            return _sanitize_service_payload({"sources": service.list_sources()})
        except HTTPException as exc:
            return _handle_route_http_exception(request, exc)
        except LookupError:
            return _handle_route_lookup_error(request)
        except ValueError:
            return _handle_route_value_error(request)
        except Exception:
            return _handle_route_unexpected_error(request)

    @app.post("/ingest")
    def ingest(
        request: Request,
        source_id: Optional[List[str]] = Query(default=None),
        max_items_per_source: Optional[int] = Query(default=None, ge=1, le=200),
        _: None = Depends(require_admin),
    ) -> dict:
        _begin_route_action(request, "ingest")
        try:
            return _sanitize_service_payload(service.ingest(
                source_ids=source_id,
                max_items_per_source=max_items_per_source,
            ))
        except HTTPException as exc:
            return _handle_route_http_exception(request, exc)
        except LookupError:
            return _handle_route_lookup_error(request)
        except ValueError:
            return _handle_route_value_error(request)
        except Exception:
            return _handle_route_unexpected_error(request)

    @app.get("/articles")
    def list_articles(
        request: Request,
        region: str = Query(default="all"),
        language: Optional[str] = Query(default=None),
        source_id: Optional[str] = Query(default=None),
        duplicate_group: Optional[str] = Query(default=None),
        primary_only: bool = Query(default=False),
        extraction_status: Optional[str] = Query(default=None),
        extraction_error_category: Optional[str] = Query(default=None),
        due_only: bool = Query(default=False),
        since_hours: int = Query(default=settings.default_lookback_hours, ge=1, le=720),
        limit: int = Query(default=50, ge=1, le=200),
    ) -> dict:
        _begin_route_action(request, "list_articles")
        try:
            return _sanitize_service_payload({
                "articles": service.list_articles(
                    region=region,
                    language=language,
                    source_id=source_id,
                    duplicate_group=duplicate_group,
                    primary_only=primary_only,
                    since_hours=since_hours,
                    extraction_status=extraction_status,
                    extraction_error_category=extraction_error_category,
                    due_only=due_only,
                    limit=limit,
                    include_hidden=False,
                )
            })
        except HTTPException as exc:
            return _handle_route_http_exception(request, exc)
        except LookupError:
            return _handle_route_lookup_error(request)
        except ValueError:
            return _handle_route_value_error(request)
        except Exception:
            return _handle_route_unexpected_error(request)

    @app.get("/digest/daily")
    def digest_daily(
        request: Request,
        region: str = Query(default="all"),
        since_hours: int = Query(default=settings.default_lookback_hours, ge=1, le=720),
        limit: int = Query(default=50, ge=1, le=200),
        use_llm: bool = Query(default=False),
    ) -> dict:
        _begin_route_action(request, "digest_daily")
        try:
            return _sanitize_service_payload(service.build_digest(
                region=region,
                since_hours=since_hours,
                limit=limit,
                use_llm=use_llm,
                persist=False,
            ))
        except HTTPException as exc:
            return _handle_route_http_exception(request, exc)
        except LookupError:
            return _handle_route_lookup_error(request)
        except ValueError:
            return _handle_route_value_error(request)
        except Exception:
            return _handle_route_unexpected_error(request)

    @app.get("/admin/stats")
    def admin_stats(request: Request, _: None = Depends(require_admin)) -> dict:
        _begin_route_action(request, "admin_stats")
        try:
            return _sanitize_service_payload(service.get_stats())
        except HTTPException as exc:
            return _handle_route_http_exception(request, exc)
        except LookupError:
            return _handle_route_lookup_error(request)
        except ValueError:
            return _handle_route_value_error(request)
        except Exception:
            return _handle_route_unexpected_error(request)

    @app.get("/admin/operations")
    def admin_operations(request: Request, _: None = Depends(require_admin)) -> dict:
        _begin_route_action(request, "admin_operations")
        try:
            return _sanitize_service_payload(service.get_operations())
        except HTTPException as exc:
            return _handle_route_http_exception(request, exc)
        except LookupError:
            return _handle_route_lookup_error(request)
        except ValueError:
            return _handle_route_value_error(request)
        except Exception:
            return _handle_route_unexpected_error(request)

    @app.get("/admin/sources")
    def admin_sources(request: Request, _: None = Depends(require_admin)) -> dict:
        _begin_route_action(request, "admin_sources")
        try:
            return _sanitize_service_payload({"sources": service.list_sources(include_runtime=True)})
        except HTTPException as exc:
            return _handle_route_http_exception(request, exc)
        except LookupError:
            return _handle_route_lookup_error(request)
        except ValueError:
            return _handle_route_value_error(request)
        except Exception:
            return _handle_route_unexpected_error(request)

    @app.get("/admin/source-alerts")
    def admin_source_alerts(
        request: Request,
        source_id: Optional[str] = Query(default=None),
        limit: int = Query(default=20, ge=1, le=100),
        _: None = Depends(require_admin),
    ) -> dict:
        _begin_route_action(request, "admin_source_alerts")
        try:
            return _sanitize_service_payload(
                {"source_alerts": service.list_source_alerts(source_id=source_id, limit=limit)}
            )
        except HTTPException as exc:
            return _handle_route_http_exception(request, exc)
        except LookupError:
            return _handle_route_lookup_error(request)
        except ValueError:
            return _handle_route_value_error(request)
        except Exception:
            return _handle_route_unexpected_error(request)

    @app.get("/admin/articles")
    def admin_articles(
        request: Request,
        region: str = Query(default="all"),
        language: Optional[str] = Query(default=None),
        source_id: Optional[str] = Query(default=None),
        duplicate_group: Optional[str] = Query(default=None),
        primary_only: bool = Query(default=False),
        extraction_status: Optional[str] = Query(default=None),
        extraction_error_category: Optional[str] = Query(default=None),
        due_only: bool = Query(default=False),
        since_hours: int = Query(default=settings.default_lookback_hours, ge=1, le=720),
        limit: int = Query(default=100, ge=1, le=200),
        include_hidden: bool = Query(default=True),
        _: None = Depends(require_admin),
    ) -> dict:
        _begin_route_action(request, "admin_articles")
        try:
            return _sanitize_service_payload({
                "articles": service.list_articles(
                    region=region,
                    language=language,
                    source_id=source_id,
                    duplicate_group=duplicate_group,
                    primary_only=primary_only,
                    since_hours=since_hours,
                    extraction_status=extraction_status,
                    extraction_error_category=extraction_error_category,
                    due_only=due_only,
                    limit=limit,
                    include_hidden=include_hidden,
                )
            })
        except HTTPException as exc:
            return _handle_route_http_exception(request, exc)
        except LookupError:
            return _handle_route_lookup_error(request)
        except ValueError:
            return _handle_route_value_error(request)
        except Exception:
            return _handle_route_unexpected_error(request)

    @app.post("/admin/ingest")
    def admin_ingest(
        payload: IngestRequest,
        request: Request,
        _: None = Depends(require_admin),
    ) -> dict:
        _begin_route_action(request, "admin_ingest")
        try:
            return _sanitize_service_payload(service.ingest(
                source_ids=payload.source_ids,
                max_items_per_source=payload.max_items_per_source,
            ))
        except HTTPException as exc:
            return _handle_route_http_exception(request, exc)
        except LookupError:
            return _handle_route_lookup_error(request)
        except ValueError:
            return _handle_route_value_error(request)
        except Exception:
            return _handle_route_unexpected_error(request)

    @app.post("/admin/enrich")
    def admin_enrich(
        payload: EnrichRequest,
        request: Request,
        _: None = Depends(require_admin),
    ) -> dict:
        _begin_route_action(request, "admin_enrich")
        try:
            return _sanitize_service_payload(service.enrich_articles(
                source_ids=payload.source_ids,
                article_ids=payload.article_ids,
                since_hours=payload.since_hours,
                limit=payload.limit,
                force=payload.force,
            ))
        except HTTPException as exc:
            return _handle_route_http_exception(request, exc)
        except LookupError:
            return _handle_route_lookup_error(request)
        except ValueError:
            return _handle_route_value_error(request)
        except Exception:
            return _handle_route_unexpected_error(request)

    @app.post("/admin/extract")
    def admin_extract(
        payload: ExtractRequest,
        request: Request,
        _: None = Depends(require_admin),
    ) -> dict:
        _begin_route_action(request, "admin_extract")
        try:
            return _sanitize_service_payload(service.extract_articles(
                source_ids=payload.source_ids,
                article_ids=payload.article_ids,
                since_hours=payload.since_hours,
                limit=payload.limit,
                force=payload.force,
            ))
        except HTTPException as exc:
            return _handle_route_http_exception(request, exc)
        except LookupError:
            return _handle_route_lookup_error(request)
        except ValueError:
            return _handle_route_value_error(request)
        except Exception:
            return _handle_route_unexpected_error(request)

    @app.post("/admin/sources/cooldowns/reset")
    def admin_reset_source_cooldowns(
        payload: ResetSourceCooldownRequest,
        request: Request,
        _: None = Depends(require_admin),
    ) -> dict:
        _begin_route_action(request, "admin_reset_source_cooldowns")
        try:
            return _sanitize_service_payload(service.reset_source_cooldowns(
                source_ids=payload.source_ids,
                active_only=payload.active_only,
            ))
        except HTTPException as exc:
            return _handle_route_http_exception(request, exc)
        except LookupError:
            return _handle_route_lookup_error(request)
        except ValueError:
            return _handle_route_value_error(request)
        except Exception:
            return _handle_route_unexpected_error(request)

    @app.post("/admin/sources/acknowledge")
    def admin_acknowledge_source_alerts(
        payload: AcknowledgeSourceAlertRequest,
        request: Request,
        _: None = Depends(require_admin),
    ) -> dict:
        _begin_route_action(request, "admin_acknowledge_source_alerts")
        try:
            return _sanitize_service_payload(
                service.acknowledge_source_alerts(
                    source_ids=payload.source_ids,
                    note=str(payload.note or ""),
                )
            )
        except HTTPException as exc:
            return _handle_route_http_exception(request, exc)
        except LookupError:
            return _handle_route_lookup_error(request)
        except ValueError:
            return _handle_route_value_error(request)
        except Exception:
            return _handle_route_unexpected_error(request)

    @app.post("/admin/sources/snooze")
    def admin_snooze_source_alerts(
        payload: SnoozeSourceAlertRequest,
        request: Request,
        _: None = Depends(require_admin),
    ) -> dict:
        _begin_route_action(request, "admin_snooze_source_alerts")
        try:
            return _sanitize_service_payload(
                service.snooze_source_alerts(
                    source_ids=payload.source_ids,
                    minutes=payload.minutes,
                    clear=payload.clear,
                )
            )
        except HTTPException as exc:
            return _handle_route_http_exception(request, exc)
        except LookupError:
            return _handle_route_lookup_error(request)
        except ValueError:
            return _handle_route_value_error(request)
        except Exception:
            return _handle_route_unexpected_error(request)

    @app.post("/admin/sources/maintenance")
    def admin_set_source_maintenance(
        payload: SourceMaintenanceRequest,
        request: Request,
        _: None = Depends(require_admin),
    ) -> dict:
        _begin_route_action(request, "admin_set_source_maintenance")
        try:
            return _sanitize_service_payload(
                service.set_source_maintenance(
                    source_ids=payload.source_ids,
                    enabled=payload.enabled,
                )
            )
        except HTTPException as exc:
            return _handle_route_http_exception(request, exc)
        except LookupError:
            return _handle_route_lookup_error(request)
        except ValueError:
            return _handle_route_value_error(request)
        except Exception:
            return _handle_route_unexpected_error(request)

    @app.post("/admin/extract/retry")
    def admin_retry_extractions(
        payload: RetryExtractionRequest,
        request: Request,
        _: None = Depends(require_admin),
    ) -> dict:
        _begin_route_action(request, "admin_retry_extractions")
        try:
            return _sanitize_service_payload(service.retry_extractions(
                source_ids=payload.source_ids,
                article_ids=payload.article_ids,
                since_hours=payload.since_hours,
                extraction_status=payload.extraction_status,
                extraction_error_category=payload.extraction_error_category,
                due_only=payload.due_only,
                limit=payload.limit,
            ))
        except HTTPException as exc:
            return _handle_route_http_exception(request, exc)
        except LookupError:
            return _handle_route_lookup_error(request)
        except ValueError:
            return _handle_route_value_error(request)
        except Exception:
            return _handle_route_unexpected_error(request)

    @app.post("/admin/digests/generate")
    def admin_generate_digest(
        payload: DigestRequest,
        request: Request,
        _: None = Depends(require_admin),
    ) -> dict:
        _begin_route_action(request, "admin_generate_digest")
        try:
            return _sanitize_service_payload(service.build_digest(
                region=payload.region,
                since_hours=payload.since_hours,
                limit=payload.limit,
                use_llm=payload.use_llm,
                persist=payload.persist,
            ))
        except HTTPException as exc:
            return _handle_route_http_exception(request, exc)
        except LookupError:
            return _handle_route_lookup_error(request)
        except ValueError:
            return _handle_route_value_error(request)
        except Exception:
            return _handle_route_unexpected_error(request)

    @app.post("/admin/digests/preview")
    def admin_preview_digest(
        payload: DigestRequest,
        request: Request,
        _: None = Depends(require_admin),
    ) -> dict:
        _begin_route_action(request, "admin_preview_digest")
        try:
            return _sanitize_service_payload(service.build_digest(
                region=payload.region,
                since_hours=payload.since_hours,
                limit=payload.limit,
                use_llm=payload.use_llm,
                persist=False,
            ))
        except HTTPException as exc:
            return _handle_route_http_exception(request, exc)
        except LookupError:
            return _handle_route_lookup_error(request)
        except ValueError:
            return _handle_route_value_error(request)
        except Exception:
            return _handle_route_unexpected_error(request)

    @app.post("/admin/digests/snapshot")
    def admin_create_digest_snapshot(
        payload: DigestSnapshotRequest,
        request: Request,
        _: None = Depends(require_admin),
    ) -> dict:
        _begin_route_action(request, "admin_create_digest_snapshot")
        try:
            return _sanitize_service_payload(service.create_digest_snapshot(
                region=payload.region,
                article_ids=payload.article_ids,
                since_hours=payload.since_hours,
                limit=payload.limit,
                use_llm=payload.use_llm,
                editor_items=[item.model_dump() for item in list(payload.editor_items or [])],
                actor=payload.actor or "",
                change_summary=payload.change_summary or "",
            ))
        except HTTPException as exc:
            return _handle_route_http_exception(request, exc)
        except LookupError:
            return _handle_route_lookup_error(request)
        except ValueError:
            return _handle_route_value_error(request)
        except Exception:
            return _handle_route_unexpected_error(request)

    @app.patch("/admin/digests/{digest_id}/editor")
    def admin_update_digest_editor(
        digest_id: int,
        payload: DigestEditorUpdateRequest,
        request: Request,
        _: None = Depends(require_admin),
    ) -> dict:
        _begin_route_action(request, "admin_update_digest_editor")
        try:
            return _sanitize_service_payload(service.update_digest_editor(
                digest_id,
                editor_items=[item.model_dump() for item in payload.editor_items],
                actor=payload.actor or "",
                change_summary=payload.change_summary or "",
            ))
        except HTTPException as exc:
            return _handle_route_http_exception(request, exc)
        except LookupError:
            return _handle_route_lookup_error(request)
        except ValueError:
            return _handle_route_value_error(request)
        except Exception:
            return _handle_route_unexpected_error(request)

    @app.get("/admin/digests/{digest_id}/history")
    def admin_digest_history(
        digest_id: int,
        request: Request,
        limit: int = Query(default=20, ge=1, le=100),
        _: None = Depends(require_admin),
    ) -> dict:
        _begin_route_action(request, "admin_digest_history")
        try:
            return _sanitize_service_payload(service.list_digest_versions(digest_id, limit=limit))
        except HTTPException as exc:
            return _handle_route_http_exception(request, exc)
        except LookupError:
            return _handle_route_lookup_error(request)
        except ValueError:
            return _handle_route_value_error(request)
        except Exception:
            return _handle_route_unexpected_error(request)

    @app.post("/admin/digests/{digest_id}/rollback")
    def admin_digest_rollback(
        digest_id: int,
        payload: DigestRollbackRequest,
        request: Request,
        _: None = Depends(require_admin),
    ) -> dict:
        _begin_route_action(request, "admin_digest_rollback")
        try:
            return _sanitize_service_payload(service.rollback_digest_snapshot(
                digest_id,
                version=payload.version,
                actor=payload.actor or "",
                change_summary=payload.change_summary or "",
            ))
        except HTTPException as exc:
            return _handle_route_http_exception(request, exc)
        except LookupError:
            return _handle_route_lookup_error(request)
        except ValueError:
            return _handle_route_value_error(request)
        except Exception:
            return _handle_route_unexpected_error(request)

    @app.post("/admin/pipeline")
    def admin_pipeline(
        payload: PipelineRequest,
        request: Request,
        _: None = Depends(require_admin),
    ) -> dict:
        _begin_route_action(request, "admin_pipeline")
        try:
            return _sanitize_service_payload(service.run_pipeline(
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
            ))
        except HTTPException as exc:
            return _handle_route_http_exception(request, exc)
        except LookupError:
            return _handle_route_lookup_error(request)
        except ValueError:
            return _handle_route_value_error(request)
        except Exception:
            return _handle_route_unexpected_error(request)

    @app.post("/admin/publish")
    def admin_publish(
        payload: PublishRequest,
        request: Request,
        _: None = Depends(require_admin),
    ) -> dict:
        _begin_route_action(request, "admin_publish")
        try:
            return _sanitize_service_payload(service.publish_digest(
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
            ))
        except HTTPException as exc:
            return _handle_route_http_exception(request, exc)
        except LookupError:
            return _handle_route_lookup_error(request)
        except ValueError:
            return _handle_route_value_error(request)
        except Exception:
            return _handle_route_unexpected_error(request)

    @app.post("/admin/publish/preview")
    def admin_publish_preview(
        payload: PublishPreviewRequest,
        request: Request,
        _: None = Depends(require_admin),
    ) -> dict:
        _begin_route_action(request, "admin_publish_preview")
        try:
            return _sanitize_service_payload(service.preview_publication_targets(
                digest_id=payload.digest_id,
                region=payload.region,
                since_hours=payload.since_hours,
                limit=payload.limit,
                use_llm=payload.use_llm,
                targets=payload.targets,
            ))
        except HTTPException as exc:
            return _handle_route_http_exception(request, exc)
        except LookupError:
            return _handle_route_lookup_error(request)
        except ValueError:
            return _handle_route_value_error(request)
        except Exception:
            return _handle_route_unexpected_error(request)

    @app.get("/admin/digests")
    def admin_digests(
        request: Request,
        region: str = Query(default="all"),
        limit: int = Query(default=20, ge=1, le=100),
        _: None = Depends(require_admin),
    ) -> dict:
        _begin_route_action(request, "admin_digests")
        try:
            return _sanitize_service_payload({"digests": service.list_digests(region=region, limit=limit)})
        except HTTPException as exc:
            return _handle_route_http_exception(request, exc)
        except LookupError:
            return _handle_route_lookup_error(request)
        except ValueError:
            return _handle_route_value_error(request)
        except Exception:
            return _handle_route_unexpected_error(request)

    @app.get("/admin/publications")
    def admin_publications(
        request: Request,
        digest_id: Optional[int] = Query(default=None, ge=1),
        target: Optional[str] = Query(default=None),
        status: Optional[str] = Query(default=None),
        limit: int = Query(default=20, ge=1, le=100),
        _: None = Depends(require_admin),
    ) -> dict:
        _begin_route_action(request, "admin_publications")
        try:
            return _sanitize_service_payload({
                "publications": service.list_publications(
                    digest_id=digest_id,
                    target=target,
                    status=status,
                    limit=limit,
                )
            })
        except HTTPException as exc:
            return _handle_route_http_exception(request, exc)
        except LookupError:
            return _handle_route_lookup_error(request)
        except ValueError:
            return _handle_route_value_error(request)
        except Exception:
            return _handle_route_unexpected_error(request)

    @app.post("/admin/publications/refresh")
    def admin_refresh_publications(
        payload: RefreshPublicationsRequest,
        request: Request,
        _: None = Depends(require_admin),
    ) -> dict:
        _begin_route_action(request, "admin_refresh_publications")
        try:
            return _sanitize_service_payload(service.refresh_publications(
                publication_ids=payload.publication_ids,
                digest_id=payload.digest_id,
                target=payload.target,
                limit=payload.limit,
                only_pending=payload.only_pending,
            ))
        except HTTPException as exc:
            return _handle_route_http_exception(request, exc)
        except LookupError:
            return _handle_route_lookup_error(request)
        except ValueError:
            return _handle_route_value_error(request)
        except Exception:
            return _handle_route_unexpected_error(request)

    @app.patch("/admin/articles/{article_id}")
    def admin_curate_article(
        article_id: int,
        payload: ArticleCurationRequest,
        request: Request,
        _: None = Depends(require_admin),
    ) -> dict:
        _begin_route_action(request, "admin_curate_article")
        try:
            return _sanitize_service_payload(curate_article_payload(article_id, payload))
        except HTTPException as exc:
            return _handle_route_http_exception(request, exc)
        except LookupError:
            return _handle_route_lookup_error(request)
        except ValueError:
            return _handle_route_value_error(request)
        except Exception:
            return _handle_route_unexpected_error(request)

    @app.post("/admin/articles/{article_id}/duplicate-primary")
    def admin_set_duplicate_primary(
        article_id: int,
        request: Request,
        _: None = Depends(require_admin),
    ) -> dict:
        _begin_route_action(request, "admin_set_duplicate_primary")
        try:
            article = service.set_duplicate_primary(article_id)
            if article is None:
                raise LookupError("article not found")
            return _sanitize_service_payload({"article": article})
        except HTTPException as exc:
            return _handle_route_http_exception(request, exc)
        except LookupError:
            return _handle_route_lookup_error(request)
        except ValueError:
            return _handle_route_value_error(request)
        except Exception:
            return _handle_route_unexpected_error(request)

    return app
