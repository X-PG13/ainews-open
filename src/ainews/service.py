from __future__ import annotations

import json
import logging
from collections import Counter
from datetime import timedelta
from typing import Dict, Iterable, List, Optional
from urllib.error import HTTPError, URLError

from . import __version__
from .alerting import AlertNotifier
from .config import Settings, load_settings
from .content_extractor import (
    ArticleContentExtractor,
    ExtractionBlockedError,
    ExtractionSkippedError,
)
from .feed_parser import parse_feed_document, replace_article_url
from .google_news import GoogleNewsResolutionError, GoogleNewsURLResolver, is_google_news_url
from .http import fetch_text
from .llm import LLMClient, OpenAICompatibleLLMClient
from .models import ArticleRecord, DailyDigest
from .publisher import DigestPublisher
from .repository import ArticleRepository
from .source_registry import SourceRegistry
from .telemetry import OperationTracker
from .utils import (
    clean_text,
    format_local_date,
    matches_keywords,
    parse_datetime,
    truncate_text,
    url_host,
    utc_now,
)

EXPORT_SCHEMA_VERSION = "1.0"
PUBLIC_ERROR_MESSAGE = "operation failed; inspect server logs with the response X-Request-ID"
PUBLIC_SKIPPED_MESSAGE = "extraction skipped by extractor policy"
logger = logging.getLogger("ainews.service")
SOURCE_COOLDOWN_CATEGORIES = {"throttled", "blocked"}
SOURCE_COOLDOWN_ALERT_KEY_PREFIX = "source_cooldown:"
DIGEST_SYNDICATION_HOSTS = {
    "news.google.com",
    "news.googleusercontent.com",
    "news.yahoo.com",
    "www.yahoo.com",
    "finance.yahoo.com",
    "www.msn.com",
}


class NewsService:
    def __init__(
        self,
        settings: Optional[Settings] = None,
        *,
        repository: Optional[ArticleRepository] = None,
        source_registry: Optional[SourceRegistry] = None,
        llm_client: Optional[LLMClient] = None,
        content_extractor: Optional[ArticleContentExtractor] = None,
        publisher: Optional[DigestPublisher] = None,
        google_news_resolver: Optional[GoogleNewsURLResolver] = None,
        alert_notifier: Optional[AlertNotifier] = None,
    ):
        self.settings = settings or load_settings()
        self.repository = repository or ArticleRepository(self.settings.database_path)
        self.source_registry = source_registry or SourceRegistry(self.settings.sources_file)
        self.llm_client = llm_client or OpenAICompatibleLLMClient(self.settings)
        resolver = google_news_resolver or getattr(content_extractor, "google_news_resolver", None)
        if resolver is None:
            resolver = GoogleNewsURLResolver(
                timeout=self.settings.request_timeout,
                user_agent=self.settings.user_agent,
            )
        if content_extractor is None:
            self.content_extractor = ArticleContentExtractor(
                timeout=self.settings.request_timeout,
                user_agent=self.settings.user_agent,
                text_limit=self.settings.extraction_text_limit,
                google_news_resolver=resolver,
            )
        else:
            self.content_extractor = content_extractor
            if hasattr(self.content_extractor, "google_news_resolver"):
                setattr(self.content_extractor, "google_news_resolver", resolver)
        self.google_news_resolver = resolver
        self.publisher = publisher or DigestPublisher(self.settings)
        self.telemetry = OperationTracker()
        self.alert_notifier = alert_notifier or AlertNotifier(self.settings, self.repository)

    def list_sources(self, *, include_runtime: bool = False) -> List[dict]:
        sources = self.source_registry.list_sources()
        if not include_runtime:
            return [source.to_dict() for source in sources]

        source_states = {
            str(item["source_id"]): item
            for item in self.repository.list_source_states(limit=max(200, len(sources) * 2))
        }
        source_summaries = self.repository.get_source_event_summaries(
            source_ids=[source.id for source in sources],
            sample_size=20,
            limit_per_source=5,
        )
        return [
            self._present_source(
                source.to_dict(),
                source_states.get(source.id),
                source_summaries.get(source.id),
            )
            for source in sources
        ]

    def get_stats(self) -> Dict[str, object]:
        payload = self.repository.get_stats()
        payload["llm_configured"] = self.llm_client.is_configured()
        payload["llm_provider"] = self.settings.llm_provider
        payload["llm_model"] = self.settings.llm_model
        payload["source_count"] = len(self.source_registry.list_sources())
        payload["configured_publish_targets"] = self.publisher.normalize_targets(
            self.settings.publish_targets.split(",")
        )
        payload["configured_alert_targets"] = [
            item for item in clean_text(self.settings.alert_targets).split(",") if item
        ]
        telemetry = self.telemetry.snapshot()
        payload["operations"] = telemetry["operations"]
        payload["failure_categories"] = telemetry["failure_categories"]
        return payload

    def get_operations(self) -> Dict[str, object]:
        telemetry = self.telemetry.snapshot()
        stats = self.repository.get_stats()
        health = self.get_health()
        metrics = self.get_metrics_snapshot()
        recent_operations = list(telemetry.get("recent_operations", []))
        pipeline_runs = [
            item for item in recent_operations if clean_text(str(item.get("name", ""))) == "pipeline"
        ][:6]
        recent_publication_failures = self.repository.list_publications(status="error", limit=6)
        pending_publications = self.repository.list_publications(status="pending", limit=6)
        source_alerts = self.list_source_alerts(limit=8)
        runtime_sources = [
            source
            for source in self.list_sources(include_runtime=True)
            if source.get("cooldown_active")
            or source.get("maintenance_mode")
            or source.get("silenced_active")
        ][:8]
        return {
            "generated_at": utc_now().isoformat(),
            "health": health,
            "metrics": metrics,
            "stats": {
                "active_source_cooldowns": int(stats.get("active_source_cooldowns") or 0),
                "blocked_source_cooldowns": int(stats.get("blocked_source_cooldowns") or 0),
                "throttled_source_cooldowns": int(stats.get("throttled_source_cooldowns") or 0),
                "publication_errors": int(stats.get("publication_errors") or 0),
                "pending_publications": int(stats.get("pending_publications") or 0),
                "scheduled_extraction_retries": int(stats.get("scheduled_extraction_retries") or 0),
                "blocked_extractions": int(stats.get("blocked_extractions") or 0),
                "throttled_extractions": int(stats.get("throttled_extractions") or 0),
            },
            "operations": telemetry.get("operations", {}),
            "operation_totals": telemetry.get("operation_totals", {}),
            "failure_categories": telemetry.get("failure_categories", {}),
            "recent_operations": recent_operations[:12],
            "pipeline_runs": pipeline_runs,
            "source_runtime": runtime_sources,
            "source_alerts": source_alerts,
            "publication_failures": recent_publication_failures,
            "pending_publications": pending_publications,
        }

    def get_metrics_snapshot(self) -> Dict[str, object]:
        stats = self.repository.get_stats()
        telemetry = self.telemetry.snapshot()
        counters = self.repository.get_monitoring_counters()
        return {
            "build_version": __version__,
            "pipeline_runs_total": dict(
                telemetry.get("operation_totals", {}).get("pipeline", {})
                if isinstance(telemetry.get("operation_totals"), dict)
                else {}
            ),
            "operation_totals": dict(telemetry.get("operation_totals", {})),
            "extract_failures_total": dict(counters.get("extract_failures_total", {})),
            "source_cooldowns_active": int(stats.get("active_source_cooldowns") or 0),
            "source_recoveries_total": int(counters.get("source_recoveries_total") or 0),
            "alert_sends_total": int(counters.get("alert_sends_total") or 0),
            "articles_total": int(stats.get("total_articles") or 0),
            "publication_errors": int(stats.get("publication_errors") or 0),
        }

    def list_source_alerts(
        self,
        *,
        source_id: Optional[str] = None,
        limit: int = 20,
    ) -> List[dict]:
        return self.repository.list_source_alerts(source_id=source_id, limit=limit)

    def get_health(self) -> Dict[str, object]:
        stats = self.repository.get_stats()
        schema_version = self.repository.get_schema_version()
        configured_targets = self.publisher.normalize_targets(self.settings.publish_targets.split(","))
        source_count = len(self.source_registry.list_sources())
        telemetry = self.telemetry.snapshot()
        degraded_reasons: List[str] = []
        if stats["extraction_errors"]:
            degraded_reasons.append("article_extraction_errors")
        if stats["throttled_extractions"]:
            degraded_reasons.append("article_extraction_throttled")
        if stats["blocked_extractions"]:
            degraded_reasons.append("article_extraction_blocked")
        if stats["active_source_cooldowns"]:
            degraded_reasons.append("source_cooldowns_active")
        if stats["llm_errors"]:
            degraded_reasons.append("llm_enrichment_errors")
        if stats["publication_errors"]:
            degraded_reasons.append("publication_errors")
        pipeline_status = (
            telemetry["operations"].get("pipeline", {}).get("status")
            if isinstance(telemetry.get("operations"), dict)
            else None
        )
        if pipeline_status in {"partial_error", "error"}:
            degraded_reasons.append("recent_pipeline_errors")

        database_check = "ok" if schema_version >= 1 else "error"
        sources_check = "ok" if source_count > 0 else "error"
        readiness = database_check == "ok" and sources_check == "ok"
        if not readiness:
            status = "error"
        elif degraded_reasons:
            status = "degraded"
        else:
            status = "ok"
        return {
            "status": status,
            "ready": readiness,
            "checks": {
                "database": database_check,
                "sources": sources_check,
                "llm": "ok" if self.llm_client.is_configured() else "warning",
                "publish_targets": "ok" if configured_targets else "warning",
            },
            "schema_version": schema_version,
            "degraded_reasons": degraded_reasons,
            "stats": {
                "total_articles": stats["total_articles"],
                "extraction_errors": stats["extraction_errors"],
                "skipped_extractions": stats["skipped_extractions"],
                "throttled_extractions": stats["throttled_extractions"],
                "blocked_extractions": stats["blocked_extractions"],
                "temporary_extraction_errors": stats["temporary_extraction_errors"],
                "permanent_extraction_errors": stats["permanent_extraction_errors"],
                "scheduled_extraction_retries": stats["scheduled_extraction_retries"],
                "active_source_cooldowns": stats["active_source_cooldowns"],
                "throttled_source_cooldowns": stats["throttled_source_cooldowns"],
                "blocked_source_cooldowns": stats["blocked_source_cooldowns"],
                "llm_errors": stats["llm_errors"],
                "pending_publications": stats["pending_publications"],
                "publication_errors": stats["publication_errors"],
            },
            "extraction_status_counts": stats["extraction_status_counts"],
            "extraction_error_categories": stats["extraction_error_categories"],
            "source_cooldowns": stats["source_cooldowns"],
            "operations": telemetry["operations"],
            "failure_categories": telemetry["failure_categories"],
        }

    def ingest(
        self,
        *,
        source_ids: Optional[Iterable[str]] = None,
        max_items_per_source: Optional[int] = None,
    ) -> Dict[str, object]:
        operation = self.telemetry.start(
            "ingest",
            context={
                "source_ids": list(source_ids or []),
                "max_items_per_source": max_items_per_source,
            },
        )
        logger.info(
            "starting ingest",
            extra={
                "event": "ingest.start",
                "operation_id": operation.operation_id,
            },
        )
        results = []
        inserted_total = 0
        grouped_total = 0
        fetched_total = 0
        resolved_total = 0
        resolution_errors = 0
        touched_article_ids: List[int] = []
        failure_categories: Counter[str] = Counter()
        resolution_cache: Dict[str, Optional[str]] = {}

        for source in self.source_registry.list_sources(source_ids=source_ids):
            status = {
                "source_id": source.id,
                "source_name": source.name,
                "fetched": 0,
                "inserted": 0,
                "skipped": 0,
                "grouped_duplicates": 0,
                "resolved_urls": 0,
                "resolution_errors": 0,
                "article_ids": [],
                "status": "ok",
            }
            try:
                xml_text = fetch_text(
                    source.url,
                    timeout=self.settings.request_timeout,
                    user_agent=self.settings.user_agent,
                )
                articles = parse_feed_document(xml_text, source)
                capped_items = max_items_per_source or self.settings.max_articles_per_source
                articles = articles[: min(source.max_items, capped_items)]
                filtered_articles = self._filter_articles(
                    source.include_keywords,
                    source.exclude_keywords,
                    articles,
                )
                normalized_articles = []
                for article in filtered_articles:
                    try:
                        normalized_article, resolution_state = self._resolve_ingested_article(
                            article,
                            cache=resolution_cache,
                        )
                    except Exception:
                        normalized_article = article
                        resolution_state = "error"
                        logger.exception(
                            "google news url resolution failed during ingest",
                            extra={
                                "event": "ingest.google_news_resolution_error",
                                "source_id": source.id,
                                "article_title": article.title,
                            },
                        )
                    if resolution_state == "resolved":
                        status["resolved_urls"] += 1
                    elif resolution_state == "error":
                        status["resolution_errors"] += 1
                    normalized_articles.append(normalized_article)
                filtered_articles = normalized_articles
                status["fetched"] = len(filtered_articles)
                fetched_total += len(filtered_articles)
                resolved_total += int(status["resolved_urls"])
                resolution_errors += int(status["resolution_errors"])

                for article in filtered_articles:
                    insert_result = self.repository.insert_article(article)
                    stored_article = insert_result.get("article")
                    if isinstance(stored_article, dict) and stored_article.get("id") is not None:
                        article_id = int(stored_article["id"])
                        touched_article_ids.append(article_id)
                        status["article_ids"].append(article_id)
                    if insert_result.get("inserted"):
                        status["inserted"] += 1
                        if insert_result.get("grouped"):
                            grouped_total += 1
                            status["grouped_duplicates"] = int(status.get("grouped_duplicates", 0)) + 1
                    else:
                        status["skipped"] += 1
                inserted_total += status["inserted"]
                self.repository.record_source_event(
                    source_id=source.id,
                    source_name=source.name,
                    event_type="ingest",
                    status="ok",
                    message=f"fetched={status['fetched']} inserted={status['inserted']} skipped={status['skipped']}",
                )
            except Exception as exc:  # pragma: no cover
                category = self._classify_error(exc)
                status["status"] = "error"
                status["error"] = self._public_error_message(exc)
                status["error_category"] = category
                failure_categories[category] += 1
                self.repository.record_source_event(
                    source_id=source.id,
                    source_name=source.name,
                    event_type="ingest",
                    status="error",
                    error_category=category,
                    message=self._public_error_message(exc),
                )
                logger.exception(
                    "ingest source failed",
                    extra={
                        "event": "ingest.source_error",
                        "target": source.id,
                        "operation_id": operation.operation_id,
                        "error_category": category,
                    },
                )
            results.append(status)

        payload = {
            "status": "partial_error" if failure_categories else "ok",
            "sources": results,
            "fetched_total": fetched_total,
            "inserted_total": inserted_total,
            "grouped_total": grouped_total,
            "resolved_total": resolved_total,
            "resolution_errors": resolution_errors,
            "article_ids": touched_article_ids,
            "stored_total": self.repository.count_articles(),
            "failure_categories": dict(failure_categories),
        }
        operation_record = self.telemetry.finish(
            operation,
            status=str(payload["status"]),
            metrics={
                "requested": len(results),
                "fetched_total": fetched_total,
                "inserted_total": inserted_total,
                "grouped_total": grouped_total,
                "resolved_total": resolved_total,
                "resolution_errors": resolution_errors,
                "stored_total": payload["stored_total"],
            },
            error_category=self._top_failure_category(failure_categories),
        )
        payload["operation"] = operation_record
        logger.info(
            "completed ingest",
            extra={
                "event": "ingest.finish",
                "operation_id": operation.operation_id,
                "requested": len(results),
                "stored_total": payload["stored_total"],
                "duration_ms": operation_record["duration_ms"],
            },
        )
        self._dispatch_runtime_alerts()
        return payload

    def resolve_google_news_urls(
        self,
        *,
        source_ids: Optional[Iterable[str]] = None,
        article_ids: Optional[Iterable[int]] = None,
        since_hours: Optional[int] = None,
        limit: int = 50,
    ) -> Dict[str, object]:
        operation = self.telemetry.start(
            "resolve_google_news",
            context={
                "source_ids": list(source_ids or []),
                "article_ids": list(article_ids or []),
                "since_hours": since_hours,
                "limit": limit,
            },
        )
        candidates = self.repository.list_google_news_articles(
            source_ids=source_ids,
            article_ids=article_ids,
            since_hours=since_hours,
            limit=limit,
        )
        results = []
        updated = 0
        merged = 0
        errors = 0
        failure_categories: Counter[str] = Counter()
        cache: Dict[str, Optional[str]] = {}

        for article in candidates:
            original_url = clean_text(str(article.get("url", "")))
            try:
                resolved_url = self._resolve_google_news_url(original_url, cache=cache)
                if not resolved_url:
                    raise GoogleNewsResolutionError("Google News URL could not be resolved")
                repository_result = self.repository.resolve_article_urls(
                    int(article["id"]),
                    url=resolved_url,
                    canonical_url=resolved_url,
                )
                action = str(repository_result.get("action", "updated"))
                if action == "merged":
                    merged += 1
                else:
                    updated += 1
                results.append(
                    {
                        "article_id": article["id"],
                        "status": action,
                        "title": article["title"],
                        "original_url": original_url,
                        "resolved_url": resolved_url,
                        "merged_into_article_id": repository_result.get("merged_into_article_id"),
                    }
                )
            except Exception as exc:
                category = self._classify_error(exc)
                logger.exception(
                    "google news url resolution failed",
                    extra={
                        "event": "resolve_google_news.article_error",
                        "article_id": int(article["id"]),
                        "error_category": category,
                    },
                )
                results.append(
                    {
                        "article_id": article["id"],
                        "status": "error",
                        "title": article["title"],
                        "original_url": original_url,
                        "error": self._public_error_message(exc),
                        "error_category": category,
                    }
                )
                errors += 1
                failure_categories[category] += 1

        payload = {
            "status": "partial_error" if errors else "ok",
            "requested": len(candidates),
            "updated": updated,
            "merged": merged,
            "errors": errors,
            "articles": results,
            "failure_categories": dict(failure_categories),
        }
        operation_record = self.telemetry.finish(
            operation,
            status=str(payload["status"]),
            metrics={
                "requested": len(candidates),
                "updated": updated,
                "merged": merged,
                "errors": errors,
            },
            error_category=self._top_failure_category(failure_categories),
        )
        payload["operation"] = operation_record
        logger.info(
            "completed google news url resolution",
            extra={
                "event": "resolve_google_news.finish",
                "operation_id": operation.operation_id,
                "requested": len(candidates),
                "updated": updated,
                "merged": merged,
                "errors": errors,
                "duration_ms": operation_record["duration_ms"],
            },
        )
        return payload

    def list_articles(
        self,
        *,
        region: Optional[str] = None,
        language: Optional[str] = None,
        source_id: Optional[str] = None,
        duplicate_group: Optional[str] = None,
        primary_only: bool = False,
        since_hours: Optional[int] = None,
        extraction_status: Optional[str] = None,
        extraction_error_category: Optional[str] = None,
        due_only: bool = False,
        limit: int = 50,
        include_hidden: bool = False,
    ) -> List[dict]:
        rows = self.repository.list_articles(
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
        return [self._present_article(row) for row in rows]

    def enrich_articles(
        self,
        *,
        source_ids: Optional[Iterable[str]] = None,
        article_ids: Optional[Iterable[int]] = None,
        since_hours: Optional[int] = None,
        limit: int = 20,
        force: bool = False,
    ) -> Dict[str, object]:
        operation = self.telemetry.start(
            "enrich",
            context={
                "source_ids": list(source_ids or []),
                "article_ids": list(article_ids or []),
                "since_hours": since_hours,
                "limit": limit,
                "force": force,
            },
        )
        if not self.llm_client.is_configured():
            payload = {
                "status": "skipped",
                "reason": "llm_not_configured",
                "updated": 0,
                "errors": 0,
                "articles": [],
            }
            payload["operation"] = self.telemetry.finish(
                operation,
                status="skipped",
                metrics={"requested": 0, "updated": 0, "errors": 0},
            )
            return payload

        candidates = self.repository.list_articles_for_enrichment(
            source_ids=source_ids,
            article_ids=article_ids,
            since_hours=since_hours,
            limit=limit,
            force=force,
        )
        results = []
        updated = 0
        errors = 0
        failure_categories: Counter[str] = Counter()

        for article in candidates:
            try:
                article = self._maybe_extract_article_for_enrichment(article)
                enrichment = self.llm_client.enrich_article(article)
                if (
                    not enrichment.title_zh
                    or not enrichment.summary_zh
                    or not enrichment.importance_zh
                ):
                    raise ValueError("LLM returned incomplete enrichment fields")
                self.repository.save_article_enrichment(
                    int(article["id"]),
                    enrichment,
                )
                results.append(
                    {
                        "article_id": article["id"],
                        "status": "ok",
                        "title": article["title"],
                        "translated_title_zh": enrichment.title_zh,
                    }
                )
                updated += 1
            except Exception as exc:
                category = self._classify_error(exc)
                public_error = self._public_error_message(exc)
                logger.exception(
                    "article enrichment failed",
                    extra={
                        "event": "enrich.article_error",
                        "article_id": int(article["id"]),
                        "error_category": category,
                    },
                )
                self.repository.mark_article_enrichment_error(
                    int(article["id"]),
                    provider=self.settings.llm_provider,
                    model=self.settings.llm_model,
                    error=public_error,
                )
                results.append(
                    {
                        "article_id": article["id"],
                        "status": "error",
                        "title": article["title"],
                        "error": public_error,
                        "error_category": category,
                    }
                )
                errors += 1
                failure_categories[category] += 1

        payload = {
            "status": "partial_error" if errors else "ok",
            "requested": len(candidates),
            "updated": updated,
            "errors": errors,
            "articles": results,
            "failure_categories": dict(failure_categories),
        }
        operation_record = self.telemetry.finish(
            operation,
            status=str(payload["status"]),
            metrics={"requested": len(candidates), "updated": updated, "errors": errors},
            error_category=self._top_failure_category(failure_categories),
        )
        payload["operation"] = operation_record
        logger.info(
            "completed enrichment",
            extra={
                "event": "enrich.finish",
                "operation_id": operation.operation_id,
                "requested": len(candidates),
                "updated": updated,
                "errors": errors,
                "duration_ms": operation_record["duration_ms"],
            },
        )
        self._dispatch_runtime_alerts()
        return payload

    def extract_articles(
        self,
        *,
        source_ids: Optional[Iterable[str]] = None,
        article_ids: Optional[Iterable[int]] = None,
        since_hours: Optional[int] = None,
        extraction_status: Optional[str] = None,
        extraction_error_category: Optional[str] = None,
        due_only: bool = False,
        limit: int = 20,
        force: bool = False,
    ) -> Dict[str, object]:
        operation = self.telemetry.start(
            "extract",
            context={
                "source_ids": list(source_ids or []),
                "article_ids": list(article_ids or []),
                "since_hours": since_hours,
                "extraction_status": extraction_status,
                "extraction_error_category": extraction_error_category,
                "due_only": due_only,
                "limit": limit,
                "force": force,
            },
        )
        candidates = self.repository.list_articles_for_extraction(
            source_ids=source_ids,
            article_ids=article_ids,
            since_hours=since_hours,
            extraction_status=extraction_status,
            extraction_error_category=extraction_error_category,
            due_only=due_only,
            limit=limit,
            force=force,
        )
        results = []
        updated = 0
        skipped = 0
        errors = 0
        failure_categories: Counter[str] = Counter()
        source_state_cache: Dict[str, Optional[dict]] = {}

        for article in candidates:
            source_id = clean_text(str(article.get("source_id", "")))
            source_name = clean_text(str(article.get("source_name", source_id)))
            source_state = source_state_cache.get(source_id)
            if source_state is None and source_id:
                source_state = self.repository.get_source_state(source_id)
                source_state_cache[source_id] = source_state
            if self._source_cooldown_active(source_state):
                cooldown_message = self._source_cooldown_message(source_state)
                self.repository.record_source_event(
                    source_id=source_id,
                    source_name=source_name,
                    event_type="extract",
                    status="skipped",
                    error_category="source_cooldown",
                    article_id=int(article["id"]),
                    article_title=str(article["title"]),
                    message=cooldown_message,
                )
                results.append(
                    {
                        "article_id": article["id"],
                        "status": "skipped",
                        "title": article["title"],
                        "message": cooldown_message,
                        "source_id": source_id,
                        "source_cooldown_until": str(source_state.get("cooldown_until", "")),
                    }
                )
                skipped += 1
                continue
            try:
                extracted = self.content_extractor.fetch_and_extract(str(article["url"]))
                self._store_extracted_article(article, extracted)
                if source_id:
                    previous_source_state = dict(source_state or {})
                    source_state_cache[source_id] = self.repository.mark_source_success(
                        source_id=source_id,
                        source_name=source_name,
                        recovery_success_threshold=self.settings.source_recovery_success_threshold,
                    )
                    recovered_state = source_state_cache[source_id] or {}
                    if self._source_just_recovered(previous_source_state, recovered_state):
                        self.repository.record_source_event(
                            source_id=source_id,
                            source_name=source_name,
                            event_type="cooldown",
                            status="recovered",
                            message=self._source_recovery_event_message(recovered_state),
                        )
                    self.repository.record_source_event(
                        source_id=source_id,
                        source_name=source_name,
                        event_type="extract",
                        status="ok",
                        article_id=int(article["id"]),
                        article_title=str(article["title"]),
                        message=f"extracted {len(extracted.text)} characters",
                    )
                results.append(
                    {
                        "article_id": article["id"],
                        "status": "ok",
                        "title": article["title"],
                        "characters": len(extracted.text),
                    }
                )
                updated += 1
            except ExtractionSkippedError:
                logger.info(
                    "article extraction skipped",
                    extra={
                        "event": "extract.article_skipped",
                        "article_id": int(article["id"]),
                        "source_id": source_id,
                    },
                )
                message = PUBLIC_SKIPPED_MESSAGE
                self.repository.mark_article_extraction_skipped(
                    int(article["id"]),
                    error=message,
                )
                if source_id:
                    self.repository.record_source_event(
                        source_id=source_id,
                        source_name=source_name,
                        event_type="extract",
                        status="skipped",
                        article_id=int(article["id"]),
                        article_title=str(article["title"]),
                        message=message,
                    )
                results.append(
                    {
                        "article_id": article["id"],
                        "status": "skipped",
                        "title": article["title"],
                        "message": message,
                    }
                )
                skipped += 1
            except Exception as exc:
                failure = self._classify_extraction_failure(exc, attempts=int(article.get("extraction_attempts") or 0))
                public_error = self._public_error_message(exc)
                source_state = None
                if source_id:
                    source_state = self._record_source_failure(
                        source_id=source_id,
                        source_name=source_name,
                        failure=failure,
                        error=public_error,
                    )
                    source_state_cache[source_id] = source_state
                    self.repository.record_source_event(
                        source_id=source_id,
                        source_name=source_name,
                        event_type="extract",
                        status=str(failure["status"]),
                        error_category=str(failure["error_category"]),
                        http_status=int(failure["http_status"]),
                        article_id=int(article["id"]),
                        article_title=str(article["title"]),
                        message=public_error,
                    )
                logger.exception(
                    "article extraction failed",
                    extra={
                        "event": "extract.article_error",
                        "article_id": int(article["id"]),
                        "error_category": failure["error_category"],
                        "http_status": failure["http_status"],
                    },
                )
                self.repository.mark_article_extraction_failure(
                    int(article["id"]),
                    error=public_error,
                    status=str(failure["status"]),
                    error_category=str(failure["error_category"]),
                    http_status=int(failure["http_status"]),
                    next_retry_at=str(failure["next_retry_at"]),
                )
                results.append(
                    {
                        "article_id": article["id"],
                        "status": str(failure["status"]),
                        "title": article["title"],
                        "error": public_error,
                        "error_category": str(failure["error_category"]),
                        "http_status": int(failure["http_status"]),
                        "next_retry_at": str(failure["next_retry_at"]),
                        "source_cooldown_until": str((source_state or {}).get("cooldown_until", "")),
                    }
                )
                errors += 1
                failure_categories[str(failure["error_category"])] += 1

        payload = {
            "status": "partial_error" if errors else "ok",
            "requested": len(candidates),
            "updated": updated,
            "skipped": skipped,
            "errors": errors,
            "articles": results,
            "failure_categories": dict(failure_categories),
        }
        operation_record = self.telemetry.finish(
            operation,
            status=str(payload["status"]),
            metrics={"requested": len(candidates), "updated": updated, "skipped": skipped, "errors": errors},
            error_category=self._top_failure_category(failure_categories),
        )
        payload["operation"] = operation_record
        logger.info(
            "completed extraction",
            extra={
                "event": "extract.finish",
                "operation_id": operation.operation_id,
                "requested": len(candidates),
                "updated": updated,
                "skipped": skipped,
                "errors": errors,
                "duration_ms": operation_record["duration_ms"],
            },
        )
        self._dispatch_runtime_alerts()
        return payload

    def retry_extractions(
        self,
        *,
        source_ids: Optional[Iterable[str]] = None,
        article_ids: Optional[Iterable[int]] = None,
        since_hours: Optional[int] = None,
        extraction_status: Optional[str] = None,
        extraction_error_category: Optional[str] = None,
        due_only: bool = False,
        limit: int = 20,
    ) -> Dict[str, object]:
        payload = self.extract_articles(
            source_ids=source_ids,
            article_ids=article_ids,
            since_hours=since_hours,
            extraction_status=extraction_status,
            extraction_error_category=extraction_error_category,
            due_only=due_only,
            limit=limit,
            force=True,
        )
        payload["retry_mode"] = "manual"
        payload["requested_filters"] = {
            "source_ids": list(source_ids or []),
            "article_ids": list(article_ids or []),
            "since_hours": since_hours,
            "extraction_status": extraction_status,
            "extraction_error_category": extraction_error_category,
            "due_only": due_only,
            "limit": limit,
        }
        return payload

    def reset_source_cooldowns(
        self,
        *,
        source_ids: Optional[Iterable[str]] = None,
        active_only: bool = True,
    ) -> Dict[str, object]:
        cleared_sources = self.repository.reset_source_cooldowns(
            source_ids=source_ids,
            active_only=active_only,
        )
        for state in cleared_sources:
            self.repository.record_source_event(
                source_id=str(state["source_id"]),
                source_name=str(state.get("source_name") or state["source_id"]),
                event_type="cooldown",
                status="cleared",
                message="source cooldown cleared by operator",
            )
        self._dispatch_runtime_alerts()
        return {
            "status": "ok",
            "cleared": len(cleared_sources),
            "active_only": active_only,
            "sources": cleared_sources,
        }

    def acknowledge_source_alerts(
        self,
        *,
        source_ids: Iterable[str],
        note: str = "",
    ) -> Dict[str, object]:
        acknowledged = []
        acknowledged_at = utc_now().isoformat()
        for source_id in [clean_text(str(item)) for item in source_ids if clean_text(str(item))]:
            source_name = self._source_name_for_id(source_id)
            state = self.repository.update_source_runtime_controls(
                source_id=source_id,
                source_name=source_name,
                acknowledged_at=acknowledged_at,
                ack_note=note,
            )
            if not state:
                continue
            self.repository.record_source_event(
                source_id=source_id,
                source_name=source_name,
                event_type="ops",
                status="acknowledged",
                message=clean_text(note) or "source alert acknowledged by operator",
            )
            acknowledged.append(state)
        return {
            "status": "ok",
            "acknowledged": len(acknowledged),
            "acknowledged_at": acknowledged_at,
            "note": clean_text(note),
            "sources": acknowledged,
        }

    def snooze_source_alerts(
        self,
        *,
        source_ids: Iterable[str],
        minutes: Optional[int] = None,
        clear: bool = False,
    ) -> Dict[str, object]:
        updated = []
        silenced_until = ""
        if not clear:
            silenced_until = (utc_now() + timedelta(minutes=max(1, int(minutes or 60)))).isoformat()
        for source_id in [clean_text(str(item)) for item in source_ids if clean_text(str(item))]:
            source_name = self._source_name_for_id(source_id)
            state = self.repository.update_source_runtime_controls(
                source_id=source_id,
                source_name=source_name,
                silenced_until=silenced_until,
            )
            if not state:
                continue
            self._deactivate_source_cooldown_alert_state(source_id, last_status="silenced")
            self.repository.record_source_event(
                source_id=source_id,
                source_name=source_name,
                event_type="ops",
                status="unsilenced" if clear else "silenced",
                message=(
                    "source alert silence cleared"
                    if clear
                    else f"source alerts silenced until {silenced_until}"
                ),
            )
            updated.append(state)
        self._dispatch_runtime_alerts()
        return {
            "status": "ok",
            "updated": len(updated),
            "clear": clear,
            "silenced_until": silenced_until,
            "sources": updated,
        }

    def set_source_maintenance(
        self,
        *,
        source_ids: Iterable[str],
        enabled: bool,
    ) -> Dict[str, object]:
        updated = []
        for source_id in [clean_text(str(item)) for item in source_ids if clean_text(str(item))]:
            source_name = self._source_name_for_id(source_id)
            state = self.repository.update_source_runtime_controls(
                source_id=source_id,
                source_name=source_name,
                maintenance_mode=enabled,
            )
            if not state:
                continue
            if enabled:
                self._deactivate_source_cooldown_alert_state(source_id, last_status="maintenance")
            self.repository.record_source_event(
                source_id=source_id,
                source_name=source_name,
                event_type="ops",
                status="maintenance_on" if enabled else "maintenance_off",
                message=(
                    "source moved into maintenance mode"
                    if enabled
                    else "source maintenance mode cleared"
                ),
            )
            updated.append(state)
        self._dispatch_runtime_alerts()
        return {
            "status": "ok",
            "updated": len(updated),
            "maintenance_mode": enabled,
            "sources": updated,
        }

    def prune_source_runtime_history(
        self,
        *,
        retention_days: Optional[int] = None,
        archive: bool = True,
    ) -> Dict[str, object]:
        operation = self.telemetry.start(
            "source_runtime_prune",
            context={
                "retention_days": retention_days,
                "archive": archive,
            },
        )
        effective_retention = max(
            1,
            int(retention_days or self.settings.source_runtime_retention_days),
        )
        result = self.repository.prune_source_runtime_history(
            retention_days=effective_retention,
            archive=archive,
        )
        operation_record = self.telemetry.finish(
            operation,
            status="ok",
            metrics={
                "events_deleted": int(result.get("events_deleted") or 0),
                "alerts_deleted": int(result.get("alerts_deleted") or 0),
            },
        )
        result["status"] = "ok"
        result["operation"] = operation_record
        return result

    def curate_article(
        self,
        article_id: int,
        *,
        is_hidden: Optional[bool] = None,
        is_pinned: Optional[bool] = None,
        is_suppressed: Optional[bool] = None,
        must_include: Optional[bool] = None,
        editorial_note: Optional[str] = None,
    ) -> Optional[dict]:
        article = self.repository.update_article_curation(
            article_id,
            is_hidden=is_hidden,
            is_pinned=is_pinned,
            is_suppressed=is_suppressed,
            must_include=must_include,
            editorial_note=editorial_note,
        )
        return self._present_article(article) if article else None

    def set_duplicate_primary(self, article_id: int) -> Optional[dict]:
        article = self.repository.set_duplicate_primary(article_id)
        return self._present_article(article) if article else None

    def list_digests(self, *, region: Optional[str] = None, limit: int = 20) -> List[dict]:
        return self.repository.list_digests(region=region, limit=limit)

    def get_digest(self, digest_id: int) -> Dict[str, object]:
        stored_digest = self.repository.get_digest(digest_id)
        if stored_digest is None:
            raise ValueError("digest not found")
        return self._payload_from_stored_digest(stored_digest)

    def list_digest_versions(self, digest_id: int, *, limit: int = 20) -> Dict[str, object]:
        stored_digest = self.repository.get_digest(digest_id)
        if stored_digest is None:
            raise ValueError("digest not found")
        return {
            "digest_id": digest_id,
            "current_version": int(stored_digest.get("current_version") or 1),
            "versions": self.repository.list_digest_versions(digest_id, limit=limit),
        }

    def create_digest_snapshot(
        self,
        *,
        region: str = "all",
        article_ids: Optional[Iterable[int]] = None,
        since_hours: Optional[int] = None,
        limit: int = 50,
        use_llm: bool = True,
        editor_items: Optional[List[dict]] = None,
        actor: str = "",
        change_summary: str = "",
    ) -> Dict[str, object]:
        payload = self.build_digest(
            region=region,
            article_ids=article_ids,
            since_hours=since_hours,
            limit=limit,
            use_llm=use_llm,
            persist=False,
        )
        editor_snapshot = self._merge_editor_snapshot_items(
            payload.get("editor_snapshot"),
            editor_items,
        )
        persisted_payload = self._apply_editor_snapshot_to_payload(
            payload,
            editor_snapshot,
            snapshot_status="draft",
            frozen_at=utc_now().isoformat(),
            version=1,
            created_by=self._editor_actor(actor),
            updated_by=self._editor_actor(actor),
            change_summary=self._editor_change_summary(change_summary, fallback="frozen from preview"),
        )
        digest = persisted_payload["digest"]
        stored_digest = self.repository.save_digest(
            region=str(persisted_payload.get("region") or region),
            since_hours=int(persisted_payload.get("since_hours") or since_hours or self.settings.default_lookback_hours),
            digest=DailyDigest(
                title=str(digest.get("title") or ""),
                overview=str(digest.get("overview") or ""),
                highlights=list(digest.get("highlights") or []),
                sections=list(digest.get("sections") or []),
                closing=str(digest.get("closing") or ""),
                provider=str(digest.get("provider") or ""),
                model=str(digest.get("model") or ""),
            ),
            body_markdown=str(persisted_payload.get("body_markdown") or ""),
            article_count=len(list(persisted_payload.get("selection_preview") or [])),
            source_count=len(
                {
                    str(article.get("source_id") or "")
                    for article in list(persisted_payload.get("articles") or [])
                    if article.get("source_id")
                }
            ),
            payload=self._payload_for_storage(persisted_payload),
            created_by=self._editor_actor(actor),
            updated_by=self._editor_actor(actor),
            change_summary=self._editor_change_summary(change_summary, fallback="frozen from preview"),
        )
        persisted_payload["stored_digest"] = stored_digest
        return persisted_payload

    def update_digest_editor(
        self,
        digest_id: int,
        *,
        editor_items: List[dict],
        actor: str = "",
        change_summary: str = "",
    ) -> Dict[str, object]:
        stored_digest = self.repository.get_digest(digest_id)
        if stored_digest is None:
            raise ValueError("digest not found")
        payload = self._payload_from_stored_digest(stored_digest)
        editor_snapshot = self._merge_editor_snapshot_items(
            payload.get("editor_snapshot"),
            editor_items,
        )
        updated_payload = self._apply_editor_snapshot_to_payload(
            payload,
            editor_snapshot,
            snapshot_status="draft",
            frozen_at=clean_text(str((payload.get("editor_snapshot") or {}).get("frozen_at", "")))
            or utc_now().isoformat(),
            last_published_at=clean_text(
                str((payload.get("editor_snapshot") or {}).get("last_published_at", ""))
            ),
            version=int(stored_digest.get("current_version") or 1) + 1,
            created_by=clean_text(
                str((payload.get("editor_snapshot") or {}).get("created_by") or stored_digest.get("created_by") or "")
            ) or self._editor_actor(actor),
            updated_by=self._editor_actor(actor),
            change_summary=self._editor_change_summary(change_summary, fallback="updated digest editor"),
        )
        digest = updated_payload["digest"]
        stored_digest = self.repository.save_digest_version(
            digest_id,
            title=str(digest.get("title") or ""),
            body_markdown=str(updated_payload.get("body_markdown") or ""),
            provider=str(digest.get("provider") or ""),
            model=str(digest.get("model") or ""),
            article_count=len(list(updated_payload.get("selection_preview") or [])),
            source_count=len(
                {
                    str(article.get("source_id") or "")
                    for article in list(updated_payload.get("articles") or [])
                    if article.get("source_id")
                }
            ),
            payload=self._payload_for_storage(updated_payload),
            updated_by=self._editor_actor(actor),
            change_summary=self._editor_change_summary(change_summary, fallback="updated digest editor"),
            action="edit",
        )
        if stored_digest is None:
            raise ValueError("digest not found")
        updated_payload["stored_digest"] = stored_digest
        return updated_payload

    def rollback_digest_snapshot(
        self,
        digest_id: int,
        *,
        version: int,
        actor: str = "",
        change_summary: str = "",
    ) -> Dict[str, object]:
        stored_digest = self.repository.get_digest(digest_id)
        if stored_digest is None:
            raise ValueError("digest not found")
        target_version = self.repository.get_digest_version(digest_id, version)
        if target_version is None:
            raise ValueError("digest snapshot version not found")
        payload = self._payload_from_stored_digest(stored_digest)
        version_payload = target_version.get("payload")
        if not isinstance(version_payload, dict) or not version_payload.get("digest"):
            raise ValueError("digest snapshot version payload is invalid")
        rollback_payload = dict(version_payload)
        rollback_payload["stored_digest"] = stored_digest
        rollback_payload["generation_mode"] = "editor"
        updated_payload = self._apply_editor_snapshot_to_payload(
            rollback_payload,
            rollback_payload.get("editor_snapshot") if isinstance(rollback_payload.get("editor_snapshot"), dict) else {},
            snapshot_status="draft",
            frozen_at=clean_text(
                str((rollback_payload.get("editor_snapshot") or {}).get("frozen_at", ""))
            ) or utc_now().isoformat(),
            last_published_at=clean_text(
                str((rollback_payload.get("editor_snapshot") or {}).get("last_published_at", ""))
            ),
            version=int(stored_digest.get("current_version") or 1) + 1,
            created_by=clean_text(
                str((payload.get("editor_snapshot") or {}).get("created_by") or stored_digest.get("created_by") or "")
            ) or self._editor_actor(actor),
            updated_by=self._editor_actor(actor),
            change_summary=self._editor_change_summary(
                change_summary,
                fallback=f"rolled back to version {version}",
            ),
        )
        digest = updated_payload["digest"]
        stored_digest = self.repository.save_digest_version(
            digest_id,
            title=str(digest.get("title") or ""),
            body_markdown=str(updated_payload.get("body_markdown") or ""),
            provider=str(digest.get("provider") or ""),
            model=str(digest.get("model") or ""),
            article_count=len(list(updated_payload.get("selection_preview") or [])),
            source_count=len(
                {
                    str(article.get("source_id") or "")
                    for article in list(updated_payload.get("articles") or [])
                    if article.get("source_id")
                }
            ),
            payload=self._payload_for_storage(updated_payload),
            updated_by=self._editor_actor(actor),
            change_summary=self._editor_change_summary(
                change_summary,
                fallback=f"rolled back to version {version}",
            ),
            action="rollback",
            restored_from_version=version,
        )
        if stored_digest is None:
            raise ValueError("digest not found")
        updated_payload["stored_digest"] = stored_digest
        return updated_payload

    def preview_publication_targets(
        self,
        *,
        digest_id: Optional[int] = None,
        region: str = "all",
        since_hours: Optional[int] = None,
        limit: int = 30,
        use_llm: bool = True,
        targets: Optional[Iterable[str]] = None,
    ) -> Dict[str, object]:
        if digest_id is not None:
            stored_digest = self.repository.get_digest(digest_id)
            if stored_digest is None:
                raise ValueError("digest not found")
            payload = self._payload_from_stored_digest(stored_digest)
        else:
            payload = self.build_digest(
                region=region,
                since_hours=since_hours,
                limit=limit,
                use_llm=use_llm,
                persist=False,
            )
        return {
            "digest": payload,
            "preview_targets": self.publisher.preview(payload, targets=targets),
        }

    def list_publications(
        self,
        *,
        publication_ids: Optional[Iterable[int]] = None,
        digest_id: Optional[int] = None,
        target: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 20,
    ) -> List[dict]:
        return self.repository.list_publications(
            publication_ids=publication_ids,
            digest_id=digest_id,
            target=target,
            status=status,
            limit=limit,
        )

    def refresh_publications(
        self,
        *,
        publication_ids: Optional[Iterable[int]] = None,
        digest_id: Optional[int] = None,
        target: Optional[str] = None,
        limit: int = 20,
        only_pending: bool = True,
    ) -> Dict[str, object]:
        operation = self.telemetry.start(
            "refresh_publications",
            context={
                "publication_ids": list(publication_ids or []),
                "digest_id": digest_id,
                "target": target,
                "limit": limit,
                "only_pending": only_pending,
            },
        )
        publications = self.repository.list_publications(
            publication_ids=publication_ids,
            digest_id=digest_id,
            target=target,
            limit=limit,
        )
        results = []
        refreshed = 0
        skipped = 0
        errors = 0
        failure_categories: Counter[str] = Counter()

        for publication in publications:
            if not self.publisher.can_refresh_publication(publication):
                results.append(
                    {
                        "publication_id": publication["id"],
                        "target": publication["target"],
                        "status": "skipped",
                        "message": "refresh is not supported for this target",
                    }
                )
                skipped += 1
                continue

            if only_pending and not self._publication_needs_refresh(publication):
                results.append(
                    {
                        "publication_id": publication["id"],
                        "target": publication["target"],
                        "status": "skipped",
                        "message": "publication is already in a final state",
                    }
                )
                skipped += 1
                continue

            try:
                update = self.publisher.refresh_publication(publication)
                stored = self.repository.update_publication(
                    int(publication["id"]),
                    status=update.status,
                    external_id=update.external_id or str(publication.get("external_id", "")),
                    message=update.message,
                    response_payload=self._merge_publication_response(
                        publication.get("response_payload"),
                        update.response,
                    ),
                )
                results.append(
                    {
                        "publication_id": publication["id"],
                        "target": publication["target"],
                        "status": update.status,
                        "message": update.message,
                        "publication": stored or publication,
                    }
                )
                refreshed += 1
            except Exception as exc:
                category = self._classify_error(exc)
                public_error = self._public_error_message(exc)
                logger.exception(
                    "publication refresh failed",
                    extra={
                        "event": "publication.refresh_error",
                        "publication_id": int(publication["id"]),
                        "target": publication["target"],
                        "error_category": category,
                    },
                )
                stored = self.repository.update_publication(
                    int(publication["id"]),
                    status="error",
                    message=public_error,
                    response_payload=self._merge_publication_response(
                        publication.get("response_payload"),
                        {"status_query_error": {"message": public_error}},
                    ),
                )
                results.append(
                    {
                        "publication_id": publication["id"],
                        "target": publication["target"],
                        "status": "error",
                        "message": public_error,
                        "error_category": category,
                        "publication": stored or publication,
                    }
                )
                errors += 1
                failure_categories[category] += 1

        payload = {
            "status": "ok" if errors == 0 else "partial_error",
            "requested": len(publications),
            "refreshed": refreshed,
            "skipped": skipped,
            "errors": errors,
            "publications": results,
            "failure_categories": dict(failure_categories),
        }
        operation_record = self.telemetry.finish(
            operation,
            status=str(payload["status"]),
            metrics={
                "requested": len(publications),
                "refreshed": refreshed,
                "skipped": skipped,
                "errors": errors,
            },
            error_category=self._top_failure_category(failure_categories),
        )
        payload["operation"] = operation_record
        logger.info(
            "completed publication refresh",
            extra={
                "event": "publish.refresh_finish",
                "operation_id": operation.operation_id,
                "requested": len(publications),
                "updated": refreshed,
                "errors": errors,
                "duration_ms": operation_record["duration_ms"],
            },
        )
        self._dispatch_runtime_alerts()
        return payload

    def run_pipeline(
        self,
        *,
        region: str = "all",
        since_hours: Optional[int] = None,
        limit: int = 30,
        max_items_per_source: Optional[int] = None,
        use_llm: bool = True,
        persist: bool = True,
        export: bool = False,
        publish: bool = False,
        publish_targets: Optional[Iterable[str]] = None,
        wechat_submit: Optional[bool] = None,
        force_republish: bool = False,
    ) -> Dict[str, object]:
        lookback = since_hours or self.settings.default_lookback_hours
        effective_persist = persist or publish
        operation = self.telemetry.start(
            "pipeline",
            context={
                "region": region,
                "since_hours": lookback,
                "limit": limit,
                "publish": publish,
                "export": export,
                "use_llm": use_llm,
            },
        )
        logger.info(
            "starting pipeline",
            extra={
                "event": "pipeline.start",
                "operation_id": operation.operation_id,
                "region": region,
                "since_hours": lookback,
                "limit": limit,
            },
        )
        ingest_result = self.ingest(max_items_per_source=max_items_per_source)
        touched_article_ids = [
            int(article_id)
            for article_id in ingest_result.get("article_ids", [])
            if article_id is not None
        ]
        extract_result = self.extract_articles(
            article_ids=touched_article_ids or None,
            since_hours=None if touched_article_ids else lookback,
            limit=limit,
            force=False,
        )
        enrich_result = self.enrich_articles(
            article_ids=touched_article_ids or None,
            since_hours=None if touched_article_ids else lookback,
            limit=limit,
            force=False,
        )
        digest_result = self.build_digest(
            region=region,
            article_ids=touched_article_ids or None,
            since_hours=None if touched_article_ids else lookback,
            limit=limit,
            use_llm=use_llm,
            persist=effective_persist,
        )

        exported_files: List[str] = []
        if export:
            exported_files = self._export_digest_payload(digest_result)

        result = {
            "ingest": ingest_result,
            "extract": extract_result,
            "enrich": enrich_result,
            "digest": digest_result,
            "exported_files": exported_files,
        }
        if publish:
            result["publish"] = self.publish_digest_payload(
                digest_result,
                targets=publish_targets,
                wechat_submit=wechat_submit,
                force_republish=force_republish,
            )
        failure_categories: Counter[str] = Counter()
        for section_name in ("ingest", "extract", "enrich", "publish"):
            section = result.get(section_name)
            if not isinstance(section, dict):
                continue
            for name, total in dict(section.get("failure_categories", {})).items():
                failure_categories[str(name)] += int(total)
        section_statuses = [
            str(result[name].get("status", "ok"))
            for name in ("ingest", "extract", "enrich", "publish")
            if isinstance(result.get(name), dict)
        ]
        pipeline_status = "ok"
        if any(status == "error" for status in section_statuses):
            pipeline_status = "error"
        elif any(status == "partial_error" for status in section_statuses):
            pipeline_status = "partial_error"
        result["status"] = pipeline_status
        result["failure_categories"] = dict(failure_categories)
        operation_record = self.telemetry.finish(
            operation,
            status=pipeline_status,
            metrics={
                "published": int(
                    result.get("publish", {}).get("published", 0)
                    if isinstance(result.get("publish"), dict)
                    else 0
                ),
                "exported_files": len(exported_files),
                "total_articles": int(digest_result.get("total_articles", 0)),
            },
            error_category=self._top_failure_category(failure_categories),
        )
        result["operation"] = operation_record
        logger.info(
            "completed pipeline",
            extra={
                "event": "pipeline.finish",
                "operation_id": operation.operation_id,
                "region": region,
                "since_hours": lookback,
                "limit": limit,
                "generation_mode": digest_result.get("generation_mode"),
                "duration_ms": operation_record["duration_ms"],
            },
        )
        section_summaries = ", ".join(
            f"{name}={result[name].get('status')}"
            for name in ("ingest", "extract", "enrich", "publish")
            if isinstance(result.get(name), dict)
        )
        self._dispatch_operation_alert(
            "pipeline_status",
            active=pipeline_status in {"partial_error", "error"},
            title=f"pipeline status is {pipeline_status}",
            message=f"{section_summaries or 'no sections'}; failure_categories={dict(failure_categories)}",
            fingerprint=f"{pipeline_status}|{section_summaries}|{dict(failure_categories)}",
        )
        self._dispatch_runtime_alerts()
        return result

    def publish_digest(
        self,
        *,
        digest_id: Optional[int] = None,
        region: str = "all",
        since_hours: Optional[int] = None,
        limit: int = 30,
        use_llm: bool = True,
        persist: bool = True,
        export: bool = False,
        targets: Optional[Iterable[str]] = None,
        wechat_submit: Optional[bool] = None,
        force_republish: bool = False,
    ) -> Dict[str, object]:
        if digest_id is not None:
            stored_digest = self.repository.get_digest(digest_id)
            if stored_digest is None:
                raise ValueError("digest not found")
            payload = self._payload_from_stored_digest(stored_digest)
        else:
            payload = self.build_digest(
                region=region,
                since_hours=since_hours,
                limit=limit,
                use_llm=use_llm,
                persist=True,
            )

        exported_files: List[str] = []
        if export:
            exported_files = self._export_digest_payload(payload)

        publish_result = self.publish_digest_payload(
            payload,
            targets=targets,
            wechat_submit=wechat_submit,
            force_republish=force_republish,
        )
        publish_result["digest"] = payload
        publish_result["exported_files"] = exported_files
        return publish_result

    def publish_digest_payload(
        self,
        payload: Dict[str, object],
        *,
        targets: Optional[Iterable[str]] = None,
        wechat_submit: Optional[bool] = None,
        force_republish: bool = False,
    ) -> Dict[str, object]:
        requested_targets = self.publisher.normalize_targets(targets)
        operation = self.telemetry.start(
            "publish",
            context={
                "requested_targets": list(requested_targets),
                "force_republish": force_republish,
            },
        )
        digest_id = None
        stored_digest = payload.get("stored_digest")
        if isinstance(stored_digest, dict) and stored_digest.get("id") is not None:
            digest_id = int(stored_digest["id"])

        if not requested_targets:
            requested_targets = self.publisher.normalize_targets(
                self.settings.publish_targets.split(",")
            )
        if not requested_targets:
            publish_result = self.publisher.publish(
                payload,
                targets=targets,
                wechat_submit=wechat_submit,
            )
            publish_result["publication_records"] = []
            publish_result["operation"] = self.telemetry.finish(
                operation,
                status=str(publish_result.get("status", "skipped")),
                metrics={"requested": 0, "published": 0, "errors": 0, "skipped": 0},
            )
            return publish_result

        already_published: Dict[str, dict] = {}
        targets_to_publish = list(requested_targets)
        if digest_id is not None and not force_republish:
            filtered_targets: List[str] = []
            for target in requested_targets:
                existing = self.repository.get_latest_publication(
                    digest_id=digest_id,
                    target=target,
                    statuses=("ok", "pending"),
                )
                if existing is not None:
                    already_published[target] = existing
                    continue
                filtered_targets.append(target)
            targets_to_publish = filtered_targets

        if targets_to_publish:
            publish_result = self.publisher.publish(
                payload,
                targets=targets_to_publish,
                wechat_submit=wechat_submit,
            )
        else:
            publish_result = {
                "status": "ok",
                "requested_targets": requested_targets,
                "targets": [],
                "published": 0,
                "errors": 0,
            }

        published_by_target = {
            str(item.get("target", "")): item for item in publish_result.get("targets", [])
        }
        records = []
        merged_targets = []
        snapshot_version = int(
            (payload.get("editor_snapshot") or {}).get("version")
            or (payload.get("stored_digest") or {}).get("current_version")
            or 0
        )
        failure_categories: Counter[str] = Counter()
        for target in requested_targets:
            if target in already_published:
                existing = already_published[target]
                merged_targets.append(
                    {
                        "target": target,
                        "status": "skipped",
                        "message": "skipped duplicate publish for existing digest target",
                        "external_id": str(existing.get("external_id", "")),
                        "response": dict(existing.get("response_payload", {}))
                        if isinstance(existing.get("response_payload"), dict)
                        else {},
                        "existing_publication_id": existing.get("id"),
                    }
                )
                continue

            item = published_by_target.get(target)
            if item is None:
                continue
            item_status = clean_text(str(item.get("status", ""))).lower()
            if item_status and item_status != "ok":
                category = self._classify_error_message(str(item.get("message", "")))
                item["error_category"] = category
                failure_categories[category] += 1
            merged_targets.append(item)
            record = self.repository.save_publication(
                digest_id=digest_id,
                digest_snapshot_version=snapshot_version,
                target=str(item.get("target", "")),
                status=self._publication_record_status(item),
                external_id=str(item.get("external_id", "")),
                message=str(item.get("message", "")),
                response_payload=dict(item.get("response", {}))
                if isinstance(item.get("response"), dict)
                else {},
            )
            records.append(record)
        publish_result["requested_targets"] = requested_targets
        publish_result["targets"] = merged_targets
        publish_result["published"] = int(publish_result.get("published", 0))
        publish_result["skipped"] = len(already_published)
        publish_result["digest_snapshot_version"] = snapshot_version
        if publish_result.get("errors", 0):
            publish_result["status"] = "partial_error"
        else:
            publish_result["status"] = "ok"
        publish_result["publication_records"] = records
        publish_result["failure_categories"] = dict(failure_categories)
        if digest_id is not None and int(publish_result.get("published", 0)) > 0:
            updated_payload = self._mark_editor_snapshot_published(payload)
            updated_digest = self.repository.update_digest(
                digest_id,
                title=str(updated_payload.get("digest", {}).get("title") or ""),
                body_markdown=str(updated_payload.get("body_markdown") or ""),
                provider=str(updated_payload.get("digest", {}).get("provider") or ""),
                model=str(updated_payload.get("digest", {}).get("model") or ""),
                article_count=len(list(updated_payload.get("selection_preview") or [])),
                source_count=len(
                    {
                        str(article.get("source_id") or "")
                        for article in list(updated_payload.get("articles") or [])
                        if article.get("source_id")
                    }
                ),
                payload=self._payload_for_storage(updated_payload),
            )
            if updated_digest is not None:
                payload["editor_snapshot"] = updated_payload.get("editor_snapshot", {})
                payload["stored_digest"] = updated_digest
        operation_record = self.telemetry.finish(
            operation,
            status=str(publish_result["status"]),
            metrics={
                "requested": len(requested_targets),
                "published": int(publish_result.get("published", 0)),
                "errors": int(publish_result.get("errors", 0)),
                "skipped": int(publish_result.get("skipped", 0)),
                "digest_id": digest_id or 0,
            },
            error_category=self._top_failure_category(failure_categories),
        )
        publish_result["operation"] = operation_record
        logger.info(
            "completed publish",
            extra={
                "event": "publish.finish",
                "operation_id": operation.operation_id,
                "published": publish_result.get("published", 0),
                "errors": publish_result.get("errors", 0),
                "requested": len(requested_targets),
                "duration_ms": operation_record["duration_ms"],
            },
        )
        failure_summary = ", ".join(
            f"{item.get('target')}={item.get('status')}"
            for item in merged_targets
            if clean_text(str(item.get("status", ""))).lower() not in {"ok", "skipped"}
        )
        self._dispatch_operation_alert(
            "publish_status",
            active=str(publish_result["status"]) in {"partial_error", "error"},
            title=f"publish status is {publish_result['status']}",
            message=f"{failure_summary or 'all targets completed successfully'}; failure_categories={dict(failure_categories)}",
            fingerprint=f"{publish_result['status']}|{failure_summary}|{dict(failure_categories)}",
        )
        self._dispatch_runtime_alerts()
        return publish_result

    def build_digest(
        self,
        *,
        region: str = "all",
        article_ids: Optional[Iterable[int]] = None,
        since_hours: Optional[int] = None,
        limit: int = 50,
        use_llm: bool = True,
        persist: bool = False,
    ) -> Dict[str, object]:
        lookback = since_hours or self.settings.default_lookback_hours
        digest_article_ids = [int(article_id) for article_id in (article_ids or []) if article_id is not None]
        operation = self.telemetry.start(
            "digest",
            context={
                "region": region,
                "article_ids": digest_article_ids,
                "since_hours": lookback,
                "limit": limit,
                "use_llm": use_llm,
                "persist": persist,
            },
        )
        articles = self.repository.list_articles(
            region=region,
            article_ids=digest_article_ids or None,
            since_hours=None if digest_article_ids else lookback,
            limit=limit,
            include_hidden=False,
        )

        if use_llm and self.llm_client.is_configured():
            missing_ids = [
                int(article["id"]) for article in articles if self._needs_enrichment(article)
            ]
            if missing_ids:
                self.enrich_articles(
                    article_ids=missing_ids,
                    limit=len(missing_ids),
                    force=False,
                )
                articles = self.repository.list_articles(
                    region=region,
                    article_ids=digest_article_ids or None,
                    since_hours=None if digest_article_ids else lookback,
                    limit=limit,
                    include_hidden=False,
                )

        presented_articles = [self._present_article(article) for article in articles]
        selection = self._build_digest_selection(presented_articles)
        digest_articles = selection["selected_articles"]
        editor_snapshot = self._build_editor_snapshot(
            presented_articles,
            selection,
            snapshot_status="draft" if persist else "preview",
        )
        if persist:
            editor_snapshot["frozen_at"] = utc_now().isoformat()
            editor_snapshot["version"] = 1
            editor_snapshot["created_by"] = "system"
            editor_snapshot["updated_by"] = "system"
            editor_snapshot["change_summary"] = "generated digest snapshot"

        generation_mode = "fallback"
        if use_llm and self.llm_client.is_configured() and digest_articles:
            try:
                digest = self.llm_client.generate_digest(
                    digest_articles,
                    region=region,
                    since_hours=lookback,
                )
                if digest.title and digest.sections:
                    generation_mode = "llm"
                else:
                    digest = self._build_fallback_digest(
                        digest_articles, region=region, since_hours=lookback
                    )
            except Exception:
                digest = self._build_fallback_digest(
                    digest_articles, region=region, since_hours=lookback
                )
        else:
            digest = self._build_fallback_digest(
                digest_articles, region=region, since_hours=lookback
            )

        body_markdown = self._render_digest_markdown(digest)
        payload = {
            "schema_version": EXPORT_SCHEMA_VERSION,
            "region": region,
            "since_hours": lookback,
            "total_articles": len(presented_articles),
            "counts_by_region": dict(Counter(article["region"] for article in presented_articles)),
            "articles": presented_articles,
            "selection_preview": selection["selection_preview"],
            "selection_decisions": selection["selection_decisions"],
            "selection_summary": selection["summary"],
            "editor_snapshot": editor_snapshot,
            "digest": digest.to_dict(),
            "body_markdown": body_markdown,
            "generation_mode": generation_mode,
        }

        if persist:
            payload["stored_digest"] = self.repository.save_digest(
                region=region,
                since_hours=lookback,
                digest=digest,
                body_markdown=body_markdown,
                article_count=len(presented_articles),
                source_count=len({article["source_id"] for article in presented_articles}),
                payload=payload,
                created_by="system",
                updated_by="system",
                change_summary="generated digest snapshot",
            )

        operation_record = self.telemetry.finish(
            operation,
            status="ok",
            metrics={
                "region": region,
                "since_hours": lookback,
                "total_articles": len(presented_articles),
                "stored": 1 if payload.get("stored_digest") else 0,
                "generation_mode": generation_mode,
                "digest_id": int(payload.get("stored_digest", {}).get("id") or 0),
            },
        )
        payload["operation"] = operation_record
        logger.info(
            "built digest",
            extra={
                "event": "digest.finish",
                "operation_id": operation.operation_id,
                "region": region,
                "since_hours": lookback,
                "limit": limit,
                "generation_mode": generation_mode,
                "schema_version": EXPORT_SCHEMA_VERSION,
                "duration_ms": operation_record["duration_ms"],
            },
        )
        return payload

    @staticmethod
    def _filter_articles(
        include_keywords: Iterable[str],
        exclude_keywords: Iterable[str],
        articles: List[ArticleRecord],
    ) -> List[ArticleRecord]:
        results = []
        for article in articles:
            haystack = " ".join([article.title, article.summary])
            if include_keywords and not matches_keywords(haystack, include_keywords):
                continue
            if exclude_keywords and matches_keywords(haystack, exclude_keywords):
                continue
            results.append(article)
        return results

    @staticmethod
    def _needs_enrichment(article: dict) -> bool:
        return (
            not str(article.get("language", "")).startswith("zh")
            and not article.get("is_hidden")
            and not article.get("is_suppressed")
            and (
                article.get("llm_status") != "ready"
                or not clean_text(str(article.get("llm_title_zh", "")))
                or not clean_text(str(article.get("llm_summary_zh", "")))
                or not clean_text(str(article.get("llm_brief_zh", "")))
            )
        )

    def _maybe_extract_article_for_enrichment(self, article: dict) -> dict:
        if clean_text(str(article.get("extracted_text", ""))):
            return article
        if not self._should_attempt_inline_extraction(article):
            return article
        try:
            extracted = self.content_extractor.fetch_and_extract(str(article["url"]))
            updated = self._store_extracted_article(article, extracted)
            return updated or article
        except Exception as exc:
            logger.exception(
                "best-effort extraction for enrichment failed",
                extra={
                    "event": "enrich.extract_error",
                    "article_id": int(article["id"]),
                    "error_category": self._classify_extraction_failure(
                        exc,
                        attempts=int(article.get("extraction_attempts") or 0),
                    )["error_category"],
                },
            )
            failure = self._classify_extraction_failure(
                exc,
                attempts=int(article.get("extraction_attempts") or 0),
            )
            self.repository.mark_article_extraction_failure(
                int(article["id"]),
                error=self._public_error_message(exc),
                status=str(failure["status"]),
                error_category=str(failure["error_category"]),
                http_status=int(failure["http_status"]),
                next_retry_at=str(failure["next_retry_at"]),
            )
            return article

    @staticmethod
    def _should_attempt_inline_extraction(article: dict) -> bool:
        status = clean_text(str(article.get("extraction_status", ""))) or "pending"
        if status in {"blocked", "permanent_error", "skipped", "ready"}:
            return False
        retry_at = clean_text(str(article.get("extraction_next_retry_at", "")))
        if retry_at and retry_at > utc_now().isoformat():
            return False
        return True

    def _store_extracted_article(self, article: dict, extracted: object) -> Optional[dict]:
        article_id = int(article["id"])
        extracted_text = str(getattr(extracted, "text", ""))
        updated = self.repository.save_article_extraction(
            article_id,
            extracted_text=extracted_text,
        )
        resolved_url = clean_text(str(getattr(extracted, "resolved_url", "")))
        current_url = clean_text(str(article.get("url", "")))
        current_canonical_url = clean_text(str(article.get("canonical_url", "")))
        if resolved_url and resolved_url != current_url:
            updated = self.repository.update_article_urls(
                article_id,
                url=resolved_url,
                canonical_url=resolved_url
                if resolved_url != current_canonical_url
                else None,
            )
        return updated

    def _resolve_ingested_article(
        self,
        article: ArticleRecord,
        *,
        cache: Dict[str, Optional[str]],
    ) -> tuple[ArticleRecord, str]:
        original_url = clean_text(article.url)
        if not is_google_news_url(original_url):
            return article, "unchanged"
        resolved_url = self._resolve_google_news_url(original_url, cache=cache)
        if not resolved_url or resolved_url == original_url:
            return article, "error"
        return (
            replace_article_url(
                article,
                url=resolved_url,
                canonical_url=resolved_url,
                original_url=original_url,
                resolution="google_news",
            ),
            "resolved",
        )

    def _resolve_google_news_url(
        self,
        url: str,
        *,
        cache: Optional[Dict[str, Optional[str]]] = None,
    ) -> Optional[str]:
        normalized_url = clean_text(url)
        if not is_google_news_url(normalized_url):
            return normalized_url
        if cache is not None and normalized_url in cache:
            return cache[normalized_url]
        try:
            resolved_url = self.google_news_resolver.resolve(normalized_url)
        except Exception:
            if cache is not None:
                cache[normalized_url] = None
            raise
        resolved_url = clean_text(resolved_url)
        if cache is not None:
            cache[normalized_url] = resolved_url or None
        return resolved_url or None

    @staticmethod
    def _present_article(article: Optional[dict]) -> Optional[dict]:
        if article is None:
            return None

        title = clean_text(str(article.get("title", "")))
        summary = clean_text(str(article.get("summary", "")))
        llm_title_zh = clean_text(str(article.get("llm_title_zh", "")))
        llm_summary_zh = clean_text(str(article.get("llm_summary_zh", "")))
        llm_brief_zh = clean_text(str(article.get("llm_brief_zh", "")))
        is_chinese = str(article.get("language", "")).startswith("zh")

        payload = dict(article)
        payload["display_title_zh"] = title if is_chinese else (llm_title_zh or title)
        payload["display_summary_zh"] = summary if is_chinese else (llm_summary_zh or summary)
        payload["display_brief_zh"] = llm_brief_zh
        payload["compact_summary_zh"] = truncate_text(payload["display_summary_zh"], 260)
        payload["is_translated"] = bool(llm_title_zh and llm_summary_zh)
        payload["content_available"] = bool(clean_text(str(article.get("extracted_text", ""))))
        payload["must_include"] = bool(article.get("must_include"))
        payload["is_suppressed"] = bool(article.get("is_suppressed"))
        payload["duplicate_group"] = clean_text(str(article.get("duplicate_group", "")))
        payload["duplicate_of"] = article.get("duplicate_of")
        payload["duplicate_count"] = int(article.get("duplicate_count") or 1)
        payload["is_duplicate_primary"] = bool(article.get("is_duplicate_primary", payload["duplicate_of"] is None))
        payload["duplicate_primary_id"] = int(article.get("duplicate_primary_id") or article.get("id") or 0)
        payload["duplicate_primary_title"] = clean_text(
            str(article.get("duplicate_primary_title", title))
        ) or title
        payload["duplicate_primary_source_name"] = clean_text(
            str(article.get("duplicate_primary_source_name", article.get("source_name", "")))
        )
        return payload

    def _build_digest_selection(self, articles: List[dict]) -> Dict[str, object]:
        ranked: List[dict] = []
        duplicates_suppressed = 0
        editorially_suppressed = 0
        ranked_out = 0
        prefiltered_decisions: List[dict] = []
        for article in articles:
            if not article.get("is_duplicate_primary", article.get("duplicate_of") is None):
                duplicates_suppressed += 1
                prefiltered_decisions.append(
                    self._selection_decision_payload(
                        article,
                        decision="duplicate_secondary",
                        reasons=["duplicate_secondary"],
                    )
                )
                continue
            score, reasons = self._digest_rank(article)
            enriched = dict(article)
            enriched["rank_score"] = score
            enriched["selection_reasons"] = reasons
            if article.get("is_suppressed"):
                editorially_suppressed += 1
                prefiltered_decisions.append(
                    self._selection_decision_payload(
                        enriched,
                        decision="suppressed",
                        reasons=["suppressed", *reasons],
                    )
                )
                continue
            ranked.append(enriched)

        ranked.sort(
            key=lambda item: (
                float(item.get("rank_score") or 0.0),
                clean_text(str(item.get("published_at", ""))),
            ),
            reverse=True,
        )

        forced = [item for item in ranked if item.get("must_include") or item.get("is_pinned")]
        selected: List[dict] = []
        seen_ids = set()
        for item in forced + ranked:
            article_id = int(item.get("id") or 0)
            if article_id in seen_ids:
                continue
            if len(selected) >= self.settings.llm_digest_max_articles and not (
                item.get("must_include") or item.get("is_pinned")
            ):
                ranked_out += 1
                continue
            seen_ids.add(article_id)
            selected.append(item)

        selection_preview = [
            self._selection_decision_payload(
                item,
                decision="selected",
                reasons=list(item.get("selection_reasons", [])),
            )
            for item in selected
        ]
        selected_ids = {int(item["article_id"]) for item in selection_preview}
        ranked_out_preview = [
            self._selection_decision_payload(
                item,
                decision="ranked_out",
                reasons=["ranked_out", *list(item.get("selection_reasons", []))],
            )
            for item in ranked
            if int(item.get("id") or 0) not in selected_ids
        ]
        selection_decisions = [
            *selection_preview,
            *prefiltered_decisions,
            *ranked_out_preview,
        ]
        return {
            "selected_articles": selected,
            "selection_preview": selection_preview,
            "selection_decisions": selection_decisions,
            "summary": {
                "candidate_articles": len(articles),
                "unique_candidates": len(ranked),
                "selected_count": len(selected),
                "duplicates_suppressed": duplicates_suppressed,
                "editorially_suppressed": editorially_suppressed,
                "ranked_out": ranked_out,
                "pinned_selected": sum(1 for item in selected if item.get("is_pinned")),
                "must_include_selected": sum(1 for item in selected if item.get("must_include")),
            },
        }

    @staticmethod
    def _selection_decision_payload(
        article: dict,
        *,
        decision: str,
        reasons: List[str],
    ) -> dict:
        return {
            "article_id": article["id"],
            "title": article["display_title_zh"],
            "source_name": article["source_name"],
            "published_at": article["published_at"],
            "rank_score": float(article.get("rank_score") or 0.0),
            "selection_reasons": reasons,
            "decision": decision,
            "duplicate_count": int(article.get("duplicate_count") or 1),
            "is_pinned": bool(article.get("is_pinned")),
            "must_include": bool(article.get("must_include")),
            "is_suppressed": bool(article.get("is_suppressed")),
        }

    @staticmethod
    def _default_digest_section_title(article: dict) -> str:
        return "国内动态" if str(article.get("region", "international")) == "domestic" else "国际动态"

    @staticmethod
    def _editor_actor(actor: str) -> str:
        return clean_text(actor) or "admin"

    @staticmethod
    def _editor_change_summary(change_summary: str, *, fallback: str) -> str:
        return clean_text(change_summary) or fallback

    def _build_editor_snapshot(
        self,
        articles: List[dict],
        selection: Dict[str, object],
        *,
        snapshot_status: str,
    ) -> Dict[str, object]:
        article_map = {int(article["id"]): article for article in articles if article.get("id") is not None}
        selected_ids = {
            int(item["article_id"]) for item in list(selection.get("selection_preview") or [])
        }
        manual_rank = 1
        items: List[dict] = []
        for index, decision_item in enumerate(list(selection.get("selection_decisions") or [])):
            article_id = int(decision_item["article_id"])
            article = article_map.get(article_id)
            if article is None:
                continue
            summary = clean_text(
                str(
                    article.get("display_brief_zh")
                    or article.get("compact_summary_zh")
                    or article.get("display_summary_zh")
                    or article.get("summary")
                    or ""
                )
            )
            item = self._coerce_editor_snapshot_item(
                {
                    "article_id": article_id,
                    "selected": article_id in selected_ids,
                    "base_decision": clean_text(str(decision_item.get("decision") or "")) or "selected",
                    "manual_rank": manual_rank if article_id in selected_ids else None,
                    "section_override": "",
                    "default_section": self._default_digest_section_title(article),
                    "publish_title_override": "",
                    "publish_summary_override": "",
                    "original_title": clean_text(str(article.get("display_title_zh") or article.get("title") or "")),
                    "original_summary": summary,
                    "selection_reasons": list(decision_item.get("selection_reasons") or []),
                    "rank_score": float(decision_item.get("rank_score") or 0.0),
                    "source_name": clean_text(str(article.get("source_name") or "")),
                    "published_at": clean_text(str(article.get("published_at") or "")),
                    "duplicate_count": int(article.get("duplicate_count") or 1),
                    "is_pinned": bool(article.get("is_pinned")),
                    "must_include": bool(article.get("must_include")),
                    "is_suppressed": bool(article.get("is_suppressed")),
                    "sort_index": index,
                },
                default_index=index,
            )
            if item["selected"]:
                manual_rank += 1
            items.append(item)
        return {
            "version": 0,
            "created_by": "",
            "updated_by": "",
            "change_summary": "",
            "snapshot_status": snapshot_status,
            "frozen_at": "",
            "updated_at": utc_now().isoformat(),
            "last_published_at": "",
            "items": items,
        }

    def _merge_editor_snapshot_items(
        self,
        editor_snapshot_payload: object,
        editor_items: Optional[List[dict]],
    ) -> Dict[str, object]:
        base_snapshot = dict(editor_snapshot_payload) if isinstance(editor_snapshot_payload, dict) else {}
        base_items = [
            self._coerce_editor_snapshot_item(item, default_index=index)
            for index, item in enumerate(list(base_snapshot.get("items") or []))
            if isinstance(item, dict)
        ]
        if not editor_items:
            base_snapshot["items"] = base_items
            return base_snapshot

        overrides = {
            int(item["article_id"]): self._coerce_editor_snapshot_item(item, default_index=index)
            for index, item in enumerate(editor_items)
            if isinstance(item, dict) and item.get("article_id") is not None
        }
        merged_items: List[dict] = []
        for index, item in enumerate(base_items):
            merged = dict(item)
            override = overrides.get(int(item["article_id"]))
            if override:
                for key in (
                    "selected",
                    "manual_rank",
                    "section_override",
                    "publish_title_override",
                    "publish_summary_override",
                ):
                    merged[key] = override.get(key)
            merged["sort_index"] = index
            merged_items.append(self._coerce_editor_snapshot_item(merged, default_index=index))

        base_snapshot["items"] = merged_items
        return base_snapshot

    @staticmethod
    def _coerce_editor_snapshot_item(item: dict, *, default_index: int) -> dict:
        manual_rank = item.get("manual_rank")
        try:
            manual_rank_value = int(manual_rank) if manual_rank not in (None, "", False) else None
        except (TypeError, ValueError):
            manual_rank_value = None
        if manual_rank_value is not None and manual_rank_value < 1:
            manual_rank_value = None
        return {
            "article_id": int(item["article_id"]),
            "selected": bool(item.get("selected")),
            "base_decision": clean_text(str(item.get("base_decision") or "")) or "selected",
            "manual_rank": manual_rank_value,
            "section_override": clean_text(str(item.get("section_override") or "")),
            "default_section": clean_text(str(item.get("default_section") or "")),
            "publish_title_override": clean_text(str(item.get("publish_title_override") or "")),
            "publish_summary_override": clean_text(str(item.get("publish_summary_override") or "")),
            "original_title": clean_text(str(item.get("original_title") or "")),
            "original_summary": clean_text(str(item.get("original_summary") or "")),
            "selection_reasons": [clean_text(str(reason)) for reason in list(item.get("selection_reasons") or []) if clean_text(str(reason))],
            "rank_score": float(item.get("rank_score") or 0.0),
            "source_name": clean_text(str(item.get("source_name") or "")),
            "published_at": clean_text(str(item.get("published_at") or "")),
            "duplicate_count": int(item.get("duplicate_count") or 1),
            "is_pinned": bool(item.get("is_pinned")),
            "must_include": bool(item.get("must_include")),
            "is_suppressed": bool(item.get("is_suppressed")),
            "sort_index": int(item.get("sort_index") or default_index),
        }

    def _apply_editor_snapshot_to_payload(
        self,
        payload: Dict[str, object],
        editor_snapshot: Dict[str, object],
        *,
        snapshot_status: str,
        version: Optional[int] = None,
        created_by: str = "",
        updated_by: str = "",
        change_summary: str = "",
        frozen_at: str = "",
        last_published_at: str = "",
    ) -> Dict[str, object]:
        snapshot = self._merge_editor_snapshot_items(editor_snapshot, None)
        snapshot["version"] = int(version or snapshot.get("version") or 1)
        snapshot["created_by"] = clean_text(created_by) or clean_text(str(snapshot.get("created_by") or "")) or "admin"
        snapshot["updated_by"] = clean_text(updated_by) or clean_text(str(snapshot.get("updated_by") or "")) or snapshot["created_by"]
        snapshot["change_summary"] = clean_text(change_summary) or clean_text(
            str(snapshot.get("change_summary") or "")
        )
        snapshot["snapshot_status"] = snapshot_status
        snapshot["frozen_at"] = clean_text(frozen_at) or clean_text(str(snapshot.get("frozen_at") or ""))
        snapshot["last_published_at"] = clean_text(last_published_at) or clean_text(
            str(snapshot.get("last_published_at") or "")
        )
        snapshot["updated_at"] = utc_now().isoformat()

        articles = [dict(article) for article in list(payload.get("articles") or [])]
        selection = self._editor_snapshot_to_selection(articles, snapshot)
        digest = self._build_snapshot_digest(
            selection["selected_articles"],
            region=str(payload.get("region") or "all"),
            since_hours=int(payload.get("since_hours") or self.settings.default_lookback_hours),
        )

        updated_payload = dict(payload)
        updated_payload["selection_preview"] = selection["selection_preview"]
        updated_payload["selection_decisions"] = selection["selection_decisions"]
        updated_payload["selection_summary"] = selection["summary"]
        updated_payload["editor_snapshot"] = snapshot
        updated_payload["digest"] = digest.to_dict()
        updated_payload["body_markdown"] = self._render_digest_markdown(digest)
        updated_payload["generation_mode"] = "editor"
        return updated_payload

    def _editor_snapshot_to_selection(
        self,
        articles: List[dict],
        editor_snapshot: Dict[str, object],
    ) -> Dict[str, object]:
        article_map = {int(article["id"]): article for article in articles if article.get("id") is not None}
        snapshot_items = [
            self._coerce_editor_snapshot_item(item, default_index=index)
            for index, item in enumerate(list(editor_snapshot.get("items") or []))
            if isinstance(item, dict)
        ]
        selected_articles: List[dict] = []
        selection_preview: List[dict] = []
        selection_decisions: List[dict] = []
        duplicates_suppressed = 0
        editorially_suppressed = 0
        ranked_out = 0

        for item in snapshot_items:
            article = article_map.get(int(item["article_id"]))
            if article is None:
                continue
            title = clean_text(item.get("publish_title_override")) or clean_text(item.get("original_title")) or clean_text(
                str(article.get("display_title_zh") or article.get("title") or "")
            )
            summary = clean_text(item.get("publish_summary_override")) or clean_text(item.get("original_summary")) or clean_text(
                str(article.get("compact_summary_zh") or article.get("display_summary_zh") or article.get("summary") or "")
            )
            section_title = clean_text(item.get("section_override")) or clean_text(item.get("default_section")) or self._default_digest_section_title(article)
            reasons = list(item.get("selection_reasons") or [])
            base_decision = clean_text(item.get("base_decision")) or "selected"
            selected = bool(item.get("selected"))
            decision = "selected" if selected else (base_decision if base_decision != "selected" else "editor_excluded")
            if selected and base_decision != "selected":
                reasons = ["manual_restore", base_decision, *reasons]
            elif not selected and base_decision == "selected":
                reasons = ["editor_excluded", *reasons]

            decision_payload = {
                "article_id": int(item["article_id"]),
                "title": title,
                "source_name": clean_text(item.get("source_name")) or clean_text(str(article.get("source_name") or "")),
                "published_at": clean_text(item.get("published_at")) or clean_text(str(article.get("published_at") or "")),
                "rank_score": float(item.get("rank_score") or article.get("rank_score") or 0.0),
                "selection_reasons": reasons,
                "decision": decision,
                "duplicate_count": int(item.get("duplicate_count") or article.get("duplicate_count") or 1),
                "is_pinned": bool(item.get("is_pinned") or article.get("is_pinned")),
                "must_include": bool(item.get("must_include") or article.get("must_include")),
                "is_suppressed": bool(item.get("is_suppressed") or article.get("is_suppressed")),
                "manual_rank": item.get("manual_rank"),
                "section": section_title,
                "publish_summary": summary,
            }
            selection_decisions.append(decision_payload)
            if selected:
                selected_article = dict(article)
                selected_article["display_title_zh"] = title
                selected_article["display_summary_zh"] = summary
                selected_article["compact_summary_zh"] = summary
                selected_article["display_brief_zh"] = summary
                selected_article["section_override"] = section_title
                selected_article["manual_rank"] = item.get("manual_rank")
                selected_article["rank_score"] = float(item.get("rank_score") or article.get("rank_score") or 0.0)
                selected_articles.append(selected_article)
                selection_preview.append(decision_payload)
            elif decision == "duplicate_secondary":
                duplicates_suppressed += 1
            elif decision == "suppressed":
                editorially_suppressed += 1
            else:
                ranked_out += 1

        selected_articles.sort(
            key=lambda article: (
                int(article.get("manual_rank") or 10_000),
                -float(article.get("rank_score") or 0.0),
                -(
                    parse_datetime(clean_text(str(article.get("published_at") or ""))).timestamp()
                    if parse_datetime(clean_text(str(article.get("published_at") or "")))
                    else 0.0
                ),
            )
        )
        selection_preview.sort(
            key=lambda item: (
                int(item.get("manual_rank") or 10_000),
                -float(item.get("rank_score") or 0.0),
            )
        )
        selection_decisions.sort(
            key=lambda item: (
                0 if item.get("decision") == "selected" else 1,
                int(item.get("manual_rank") or 10_000),
                -float(item.get("rank_score") or 0.0),
                clean_text(str(item.get("published_at") or "")),
            )
        )
        return {
            "selected_articles": selected_articles,
            "selection_preview": selection_preview,
            "selection_decisions": selection_decisions,
            "summary": {
                "candidate_articles": len(snapshot_items),
                "unique_candidates": len(snapshot_items) - duplicates_suppressed,
                "selected_count": len(selected_articles),
                "duplicates_suppressed": duplicates_suppressed,
                "editorially_suppressed": editorially_suppressed,
                "ranked_out": ranked_out,
                "pinned_selected": sum(1 for item in selected_articles if item.get("is_pinned")),
                "must_include_selected": sum(1 for item in selected_articles if item.get("must_include")),
            },
        }

    def _build_snapshot_digest(
        self,
        articles: List[dict],
        *,
        region: str,
        since_hours: int,
    ) -> DailyDigest:
        region_names = {
            "all": "全网",
            "domestic": "国内",
            "international": "国际",
        }
        highlights = [
            f"{article['display_title_zh']} | {article['source_name']}" for article in articles[:4]
        ]
        sections: List[Dict[str, object]] = []
        section_index: Dict[str, int] = {}
        for article in articles:
            section_title = clean_text(str(article.get("section_override") or "")) or self._default_digest_section_title(article)
            brief = clean_text(str(article.get("display_brief_zh", "")))
            summary = clean_text(str(article.get("compact_summary_zh", "")))
            line = f"{article['display_title_zh']}。{brief or summary}"
            if section_title not in section_index:
                section_index[section_title] = len(sections)
                sections.append({"title": section_title, "items": []})
            sections[section_index[section_title]]["items"].append(line)

        return DailyDigest(
            title=f"{format_local_date()} {region_names.get(region, '全网')} AI 新闻日报",
            overview=f"最近 {since_hours} 小时已冻结 {len(articles)} 条 AI 新闻用于本次发布。",
            highlights=highlights,
            sections=sections,
            closing="以上内容基于已确认的编辑稿生成，发布前仍可继续复核。",
        )

    def _mark_editor_snapshot_published(self, payload: Dict[str, object]) -> Dict[str, object]:
        snapshot = dict(payload.get("editor_snapshot") or {})
        snapshot["snapshot_status"] = "published"
        snapshot["last_published_at"] = utc_now().isoformat()
        snapshot["updated_at"] = utc_now().isoformat()
        updated_payload = dict(payload)
        updated_payload["editor_snapshot"] = snapshot
        return updated_payload

    @staticmethod
    def _digest_rank(article: dict) -> tuple[float, List[str]]:
        score = 0.0
        reasons: List[str] = []
        if article.get("must_include"):
            score += 1000.0
            reasons.append("must_include")
        if article.get("is_pinned"):
            score += 800.0
            reasons.append("pinned")
        if article.get("editorial_note"):
            score += 60.0
            reasons.append("editorial_note")
        if article.get("region") == "international":
            score += 40.0
            reasons.append("international")
        if article.get("is_translated"):
            score += 30.0
            reasons.append("translated")
        if article.get("content_available"):
            score += 35.0
            reasons.append("full_text")
        if int(article.get("duplicate_count") or 1) > 1:
            score += 45.0
            reasons.append("primary_of_duplicate_cluster")
        if clean_text(str(article.get("display_brief_zh", ""))):
            score += 25.0
            reasons.append("llm_importance")
        host = url_host(str(article.get("canonical_url") or article.get("url") or ""))
        if host and host not in DIGEST_SYNDICATION_HOSTS:
            score += 20.0
            reasons.append("direct_source")
        published_at = clean_text(str(article.get("published_at", "")))
        if published_at:
            age_hours = max(
                0.0,
                (utc_now() - parse_datetime(published_at)).total_seconds() / 3600.0,
            )
            if age_hours <= 6:
                score += 120.0
                reasons.append("fresh_6h")
            elif age_hours <= 24:
                score += 85.0
                reasons.append("fresh_24h")
            elif age_hours <= 48:
                score += 45.0
                reasons.append("fresh_48h")
            else:
                score += 10.0
        score += min(25.0, len(clean_text(str(article.get("display_summary_zh", "")))) / 24.0)
        return round(score, 2), reasons

    @staticmethod
    def _present_source(
        source: dict,
        source_state: Optional[dict] = None,
        source_summary: Optional[dict] = None,
    ) -> dict:
        payload = dict(source)
        runtime = dict(source_state or {})
        summary = dict(source_summary or {})
        cooldown_until = clean_text(str(runtime.get("cooldown_until", "")))
        payload["cooldown_status"] = clean_text(str(runtime.get("cooldown_status", "")))
        payload["cooldown_until"] = cooldown_until
        payload["cooldown_active"] = bool(cooldown_until and cooldown_until > utc_now().isoformat())
        payload["consecutive_failures"] = int(runtime.get("consecutive_failures") or 0)
        payload["consecutive_successes"] = int(runtime.get("consecutive_successes") or 0)
        payload["last_error_category"] = clean_text(str(runtime.get("last_error_category", "")))
        payload["last_http_status"] = int(runtime.get("last_http_status") or 0)
        payload["last_error_at"] = clean_text(str(runtime.get("last_error_at", "")))
        payload["last_success_at"] = clean_text(str(runtime.get("last_success_at", "")))
        payload["last_recovered_at"] = clean_text(str(runtime.get("last_recovered_at", "")))
        payload["silenced_until"] = clean_text(str(runtime.get("silenced_until", "")))
        payload["silenced_active"] = bool(runtime.get("silenced_active"))
        payload["maintenance_mode"] = bool(runtime.get("maintenance_mode"))
        payload["acknowledged_at"] = clean_text(str(runtime.get("acknowledged_at", "")))
        payload["ack_note"] = clean_text(str(runtime.get("ack_note", "")))
        payload["recent_success_rate"] = summary.get("recent_success_rate")
        payload["recent_failure_categories"] = dict(summary.get("recent_failure_categories", {}))
        payload["recent_operations"] = list(summary.get("recent_operations", []))
        if not payload["last_error_at"]:
            payload["last_error_at"] = clean_text(str(summary.get("last_failure_at", "")))
        if not payload["last_success_at"]:
            payload["last_success_at"] = clean_text(str(summary.get("last_success_at", "")))
        return payload

    @staticmethod
    def _publication_record_status(item: dict) -> str:
        target = clean_text(str(item.get("target", ""))).lower()
        status = clean_text(str(item.get("status", ""))) or "ok"
        response = item.get("response")
        if target != "wechat" or not isinstance(response, dict):
            return status
        publish_payload = response.get("publish")
        if isinstance(publish_payload, dict) and clean_text(
            str(publish_payload.get("publish_id", ""))
        ):
            return "pending"
        return status

    @staticmethod
    def _merge_publication_response(
        current: object,
        updates: object,
    ) -> Dict[str, object]:
        merged: Dict[str, object] = {}
        if isinstance(current, dict):
            merged.update(current)
        if isinstance(updates, dict):
            merged.update(updates)
        return merged

    @staticmethod
    def _publication_needs_refresh(publication: dict) -> bool:
        if clean_text(str(publication.get("target", ""))).lower() != "wechat":
            return False
        response_payload = publication.get("response_payload")
        if not isinstance(response_payload, dict):
            return publication.get("status") == "pending"

        status_query = response_payload.get("status_query")
        if isinstance(status_query, dict):
            try:
                return int(status_query.get("publish_status")) == 1
            except (TypeError, ValueError):
                return True

        publish_payload = response_payload.get("publish")
        if isinstance(publish_payload, dict) and clean_text(
            str(publish_payload.get("publish_id", ""))
        ):
            return True
        return publication.get("status") == "pending"

    @staticmethod
    def _source_cooldown_active(source_state: Optional[dict]) -> bool:
        if not isinstance(source_state, dict):
            return False
        cooldown_until = clean_text(str(source_state.get("cooldown_until", "")))
        return bool(cooldown_until and cooldown_until > utc_now().isoformat())

    @staticmethod
    def _source_alerts_muted(source_state: Optional[dict]) -> bool:
        if not isinstance(source_state, dict):
            return False
        if bool(source_state.get("maintenance_mode")):
            return True
        silenced_until = clean_text(str(source_state.get("silenced_until", "")))
        return bool(silenced_until and silenced_until > utc_now().isoformat())

    @staticmethod
    def _source_alerts_acknowledged(source_state: Optional[dict]) -> bool:
        if not isinstance(source_state, dict):
            return False
        return bool(clean_text(str(source_state.get("acknowledged_at", ""))))

    @staticmethod
    def _source_recovery_pending(source_state: Optional[dict]) -> bool:
        if not isinstance(source_state, dict):
            return False
        return bool(
            clean_text(str(source_state.get("cooldown_status", "")))
            or clean_text(str(source_state.get("acknowledged_at", "")))
            or clean_text(str(source_state.get("ack_note", "")))
        )

    @classmethod
    def _source_just_recovered(cls, previous: Optional[dict], current: Optional[dict]) -> bool:
        if not cls._source_recovery_pending(previous):
            return False
        if not isinstance(current, dict):
            return False
        previous_recovered = clean_text(str((previous or {}).get("last_recovered_at", "")))
        current_recovered = clean_text(str(current.get("last_recovered_at", "")))
        return bool(current_recovered and current_recovered != previous_recovered)

    @staticmethod
    def _source_cooldown_message(source_state: Optional[dict]) -> str:
        if not isinstance(source_state, dict):
            return "source cooldown is active"
        status = clean_text(str(source_state.get("cooldown_status", ""))) or "cooldown"
        until = clean_text(str(source_state.get("cooldown_until", "")))
        if until:
            return f"source {status} cooldown active until {until}"
        return f"source {status} cooldown is active"

    def _record_source_failure(
        self,
        *,
        source_id: str,
        source_name: str,
        failure: Dict[str, object],
        error: str,
    ) -> Optional[dict]:
        category = clean_text(str(failure.get("error_category", "")))
        http_status = int(failure.get("http_status") or 0)
        previous = self.repository.get_source_state(source_id) or {}
        previous_active = self._source_cooldown_active(previous)
        if category in SOURCE_COOLDOWN_CATEGORIES:
            consecutive_failures = int(previous.get("consecutive_failures") or 0) + 1
            cooldown_until = ""
            cooldown_status = ""
            if consecutive_failures >= self.settings.source_cooldown_failure_threshold:
                cooldown_until = self._next_source_cooldown_at(
                    category,
                    consecutive_failures=consecutive_failures,
                )
                cooldown_status = category
        else:
            consecutive_failures = 0
            cooldown_until = ""
            cooldown_status = ""

        state = self.repository.upsert_source_state(
            source_id=source_id,
            source_name=source_name,
            cooldown_status=cooldown_status,
            cooldown_until=cooldown_until,
            consecutive_failures=consecutive_failures,
            consecutive_successes=0,
            last_error_category=category,
            last_http_status=http_status,
            last_error=error,
            last_error_at=utc_now().isoformat(),
            acknowledged_at="" if (not previous_active and category in SOURCE_COOLDOWN_CATEGORIES) else None,
            ack_note="" if (not previous_active and category in SOURCE_COOLDOWN_CATEGORIES) else None,
        )
        if state and self._source_cooldown_active(state) and not previous_active:
            self.repository.record_source_event(
                source_id=source_id,
                source_name=source_name,
                event_type="cooldown",
                status="active",
                error_category=category,
                http_status=http_status,
                message=self._source_cooldown_message(state),
            )
        return state

    def _dispatch_runtime_alerts(self) -> None:
        health = self.get_health()
        health_status = clean_text(str(health.get("status", "ok")))
        degraded_reasons = list(health.get("degraded_reasons", []))
        cooldowns = list(health.get("source_cooldowns", []))
        alertable_cooldowns = [
            item
            for item in cooldowns
            if not self._source_alerts_muted(item) and not self._source_alerts_acknowledged(item)
        ]
        alertable_degraded_reasons = [
            item
            for item in degraded_reasons
            if item != "source_cooldowns_active" or alertable_cooldowns
        ]
        self.alert_notifier.notify_rule(
            "health_status",
            active=health_status == "error" or (
                health_status == "degraded" and bool(alertable_degraded_reasons)
            ),
            title=f"service health is {health_status or 'unknown'}",
            message=(
                f"status={health_status}; degraded_reasons={', '.join(alertable_degraded_reasons) or 'none'}; "
                f"request ready={health.get('ready')}"
            ),
            fingerprint=f"{health_status}|{'|'.join(sorted(str(item) for item in alertable_degraded_reasons))}",
            severity="warning",
            recovery_title="service health recovered",
            recovery_message="service health returned to ok",
        )
        cooldown_fingerprint = "|".join(
            sorted(
                f"{item.get('source_id')}:{item.get('cooldown_status')}:{item.get('cooldown_until')}"
                for item in alertable_cooldowns
            )
        )
        self.alert_notifier.notify_rule(
            "source_cooldowns_active",
            active=bool(alertable_cooldowns),
            title="source cooldowns are active",
            message=self._source_cooldown_alert_message(alertable_cooldowns),
            fingerprint=cooldown_fingerprint,
            severity="warning",
            recovery_title="source cooldowns cleared",
            recovery_message="all source cooldowns have been cleared",
        )
        self._dispatch_source_cooldown_alerts(cooldowns)

    def _dispatch_operation_alert(self, rule_key: str, *, active: bool, title: str, message: str, fingerprint: str) -> None:
        self.alert_notifier.notify_rule(
            rule_key,
            active=active,
            title=title,
            message=message,
            fingerprint=fingerprint,
            severity="critical" if active else "info",
            recovery_title=f"{title} recovered",
            recovery_message=f"{title} returned to ok",
        )

    def _dispatch_source_cooldown_alerts(self, cooldowns: List[dict]) -> None:
        active_by_source: Dict[str, dict] = {}
        for item in cooldowns:
            source_id = clean_text(str(item.get("source_id", "")))
            if not source_id:
                continue
            active_by_source[source_id] = item
            if self._source_alerts_muted(item):
                self._deactivate_source_cooldown_alert_state(source_id, last_status="suppressed")
                continue
            if self._source_alerts_acknowledged(item):
                continue
            source_name = clean_text(str(item.get("source_name", ""))) or source_id
            alert_key = f"{SOURCE_COOLDOWN_ALERT_KEY_PREFIX}{source_id}"
            message = self._source_cooldown_recovery_message(item, recovering=False)
            fingerprint = "|".join(
                [
                    clean_text(str(item.get("cooldown_status", ""))),
                    clean_text(str(item.get("cooldown_until", ""))),
                    str(int(item.get("consecutive_failures") or 0)),
                    str(int(item.get("last_http_status") or 0)),
                ]
            )
            result = self.alert_notifier.notify_rule(
                alert_key,
                active=True,
                title=f"source cooldown active: {source_name}",
                message=message,
                fingerprint=fingerprint,
                severity="warning",
                recovery_title=f"source cooldown cleared: {source_name}",
                recovery_message=self._source_cooldown_recovery_message(item, recovering=True),
            )
            self._record_source_alert_history(
                source_id=source_id,
                source_name=source_name,
                alert_key=alert_key,
                alert_status=str(result.get("status", "")),
                severity="warning",
                title=f"source cooldown active: {source_name}",
                message=message,
                fingerprint=fingerprint,
                targets=result.get("targets"),
            )

        for alert_state in self.repository.list_alert_states(
            prefix=SOURCE_COOLDOWN_ALERT_KEY_PREFIX,
            active_only=True,
            limit=200,
        ):
            alert_key = clean_text(str(alert_state.get("alert_key", "")))
            if not alert_key.startswith(SOURCE_COOLDOWN_ALERT_KEY_PREFIX):
                continue
            source_id = alert_key[len(SOURCE_COOLDOWN_ALERT_KEY_PREFIX) :]
            if not source_id or source_id in active_by_source:
                continue
            source_state = self.repository.get_source_state(source_id) or {}
            if self._source_alerts_muted(source_state):
                self._deactivate_source_cooldown_alert_state(source_id, last_status="suppressed")
                continue
            source_name = clean_text(str(source_state.get("source_name", ""))) or source_id
            message = self._source_cooldown_recovery_message(source_state, recovering=True)
            result = self.alert_notifier.notify_rule(
                alert_key,
                active=False,
                title=f"source cooldown cleared: {source_name}",
                message=message,
                severity="info",
                recovery_title=f"source cooldown cleared: {source_name}",
                recovery_message=message,
            )
            self._record_source_alert_history(
                source_id=source_id,
                source_name=source_name,
                alert_key=alert_key,
                alert_status=str(result.get("status", "")),
                severity="info",
                title=f"source cooldown cleared: {source_name}",
                message=message,
                targets=result.get("targets"),
            )

    @staticmethod
    def _source_cooldown_alert_message(cooldowns: List[dict]) -> str:
        if not cooldowns:
            return "no active source cooldowns"
        lines = [
            f"{item.get('source_id')} status={item.get('cooldown_status')} until={item.get('cooldown_until')}"
            for item in cooldowns[:6]
        ]
        remaining = len(cooldowns) - len(lines)
        if remaining > 0:
            lines.append(f"+{remaining} more source cooldown(s)")
        return "\n".join(lines)

    @staticmethod
    def _source_cooldown_recovery_message(
        source_state: Optional[dict],
        *,
        recovering: bool,
    ) -> str:
        if not isinstance(source_state, dict):
            return "source cooldown state updated"
        source_name = clean_text(str(source_state.get("source_name", "")))
        source_id = clean_text(str(source_state.get("source_id", "")))
        source_label = source_name or source_id or "unknown source"
        if recovering:
            last_success_at = clean_text(str(source_state.get("last_success_at", "")))
            if last_success_at:
                return f"{source_label} recovered from cooldown at {last_success_at}"
            return f"{source_label} recovered from cooldown"
        status = clean_text(str(source_state.get("cooldown_status", ""))) or "cooldown"
        until = clean_text(str(source_state.get("cooldown_until", "")))
        attempts = int(source_state.get("consecutive_failures") or 0)
        http_status = int(source_state.get("last_http_status") or 0)
        parts = [f"{source_label} entered {status} cooldown"]
        if until:
            parts.append(f"until {until}")
        if attempts:
            parts.append(f"after {attempts} consecutive failures")
        if http_status:
            parts.append(f"http={http_status}")
        return "; ".join(parts)

    @staticmethod
    def _source_recovery_event_message(source_state: Optional[dict]) -> str:
        if not isinstance(source_state, dict):
            return "source recovered after consecutive successful extractions"
        source_name = clean_text(str(source_state.get("source_name", "")))
        source_id = clean_text(str(source_state.get("source_id", "")))
        source_label = source_name or source_id or "unknown source"
        successes = max(1, int(source_state.get("consecutive_successes") or 0))
        recovered_at = clean_text(str(source_state.get("last_recovered_at", "")))
        if recovered_at:
            return (
                f"{source_label} recovered after {successes} consecutive successful extractions "
                f"at {recovered_at}"
            )
        return f"{source_label} recovered after {successes} consecutive successful extractions"

    def _source_name_for_id(self, source_id: str) -> str:
        source_list = self.source_registry.list_sources(source_ids=[source_id])
        if source_list:
            return clean_text(str(source_list[0].name)) or source_id
        source_state = self.repository.get_source_state(source_id) or {}
        return clean_text(str(source_state.get("source_name", ""))) or source_id

    def _deactivate_source_cooldown_alert_state(self, source_id: str, *, last_status: str) -> None:
        alert_key = f"{SOURCE_COOLDOWN_ALERT_KEY_PREFIX}{source_id}"
        state = self.repository.get_alert_state(alert_key)
        if not state or not bool(state.get("is_active")):
            return
        self.repository.save_alert_state(
            alert_key=alert_key,
            is_active=False,
            fingerprint="",
            last_status=last_status,
            last_title=str(state.get("last_title", "")),
            last_message=str(state.get("last_message", "")),
        )

    def _record_source_alert_history(
        self,
        *,
        source_id: str,
        source_name: str,
        alert_key: str,
        alert_status: str,
        severity: str,
        title: str,
        message: str,
        fingerprint: str = "",
        targets: Optional[object] = None,
    ) -> None:
        if alert_status not in {
            "sent",
            "delivery_error",
            "recovered",
            "recovery_delivery_error",
        }:
            return
        self.repository.record_source_alert(
            source_id=source_id,
            source_name=source_name,
            alert_key=alert_key,
            alert_status=alert_status,
            severity=severity,
            title=title,
            message=message,
            fingerprint=fingerprint,
            targets=targets if isinstance(targets, list) else None,
        )

    @classmethod
    def _classify_error(cls, exc: Exception) -> str:
        return cls._classify_error_message(str(exc))

    @classmethod
    def _classify_extraction_failure(cls, exc: Exception, *, attempts: int) -> Dict[str, object]:
        http_status = cls._http_status_from_exception(exc)
        message = clean_text(str(exc)).lower()

        if isinstance(exc, ExtractionBlockedError):
            category = "blocked"
        elif http_status == 429 or "too many requests" in message or "rate limit" in message:
            category = "throttled"
        elif http_status in {401, 403}:
            category = "blocked"
        elif isinstance(exc, (TimeoutError, URLError)) or (500 <= http_status < 600):
            category = "temporary_error"
        elif http_status in {404, 410, 451}:
            category = "permanent_error"
        elif "captcha" in message or "challenge" in message or "verify you are human" in message:
            category = "blocked"
        elif "too short" in message or "unsupported" in message or "invalid" in message:
            category = "permanent_error"
        else:
            category = "temporary_error"

        next_retry_at = cls._next_extraction_retry_at(category, attempts=attempts)
        return {
            "status": category,
            "error_category": category,
            "http_status": http_status,
            "next_retry_at": next_retry_at,
        }

    @staticmethod
    def _public_error_message(exc: Exception) -> str:
        return PUBLIC_ERROR_MESSAGE

    @staticmethod
    def _http_status_from_exception(exc: Exception) -> int:
        if isinstance(exc, HTTPError):
            try:
                return int(exc.code)
            except (TypeError, ValueError):
                return 0
        return 0

    @staticmethod
    def _next_extraction_retry_at(category: str, *, attempts: int) -> str:
        if category == "throttled":
            delay_minutes = min(24 * 60, 30 * (2 ** min(attempts, 4)))
            return (utc_now() + timedelta(minutes=delay_minutes)).isoformat()
        if category == "blocked":
            delay_hours = min(72, 24 * max(1, attempts + 1))
            return (utc_now() + timedelta(hours=delay_hours)).isoformat()
        if category == "temporary_error":
            delay_minutes = min(12 * 60, 15 * (2 ** min(attempts, 4)))
            return (utc_now() + timedelta(minutes=delay_minutes)).isoformat()
        return ""

    def _next_source_cooldown_at(self, category: str, *, consecutive_failures: int) -> str:
        threshold = max(1, int(self.settings.source_cooldown_failure_threshold))
        escalation = max(0, consecutive_failures - threshold)
        if category == "blocked":
            delay_minutes = min(
                72 * 60,
                int(self.settings.source_blocked_cooldown_minutes) * (2 ** min(escalation, 3)),
            )
            return (utc_now() + timedelta(minutes=delay_minutes)).isoformat()
        delay_minutes = min(
            24 * 60,
            int(self.settings.source_throttle_cooldown_minutes) * (2 ** min(escalation, 3)),
        )
        return (utc_now() + timedelta(minutes=delay_minutes)).isoformat()

    @staticmethod
    def _classify_error_message(message: str) -> str:
        value = clean_text(message).lower()
        if not value:
            return "unexpected"
        if "429" in value or "rate limit" in value or "too many requests" in value:
            return "rate_limited"
        if "401" in value or "403" in value or "unauthorized" in value or "forbidden" in value:
            return "auth"
        if "timeout" in value or "timed out" in value:
            return "timeout"
        if (
            "connection" in value
            or "network" in value
            or "dns" in value
            or "temporarily unavailable" in value
            or "ssl" in value
        ):
            return "network"
        if (
            "validation" in value
            or "invalid" in value
            or "missing" in value
            or "unsupported" in value
        ):
            return "validation"
        return "unexpected"

    @staticmethod
    def _top_failure_category(categories: Counter[str]) -> str:
        if not categories:
            return ""
        return categories.most_common(1)[0][0]

    @staticmethod
    def _build_fallback_digest(
        articles: List[dict],
        *,
        region: str,
        since_hours: int,
    ) -> DailyDigest:
        region_names = {
            "all": "全网",
            "domestic": "国内",
            "international": "国际",
        }
        grouped: Dict[str, List[dict]] = {"domestic": [], "international": []}
        for article in articles:
            grouped.setdefault(str(article.get("region", "international")), []).append(article)

        highlights = [
            f"{article['display_title_zh']} | {article['source_name']}" for article in articles[:4]
        ]
        sections = []
        for section_key in ["domestic", "international"]:
            items = []
            for article in grouped.get(section_key, [])[:6]:
                brief = clean_text(str(article.get("display_brief_zh", "")))
                summary = clean_text(str(article.get("compact_summary_zh", "")))
                line = f"{article['display_title_zh']}。{brief or summary}"
                items.append(line)
            if items:
                sections.append(
                    {
                        "title": "国内动态" if section_key == "domestic" else "国际动态",
                        "items": items,
                    }
                )

        return DailyDigest(
            title=f"{format_local_date()} {region_names.get(region, '全网')} AI 新闻日报",
            overview=f"最近 {since_hours} 小时共收录 {len(articles)} 条 AI 相关新闻，以下为自动整理结果。",
            highlights=highlights,
            sections=sections,
            closing="以上内容由系统自动整理，建议在对外发布前进行人工复核。",
        )

    @staticmethod
    def _render_digest_markdown(digest: DailyDigest) -> str:
        lines = [f"# {digest.title}", ""]
        if digest.overview:
            lines.extend([digest.overview, ""])
        if digest.highlights:
            lines.append("## 今日要点")
            lines.extend([f"- {item}" for item in digest.highlights])
            lines.append("")
        for section in digest.sections:
            lines.append(f"## {section['title']}")
            lines.extend([f"- {item}" for item in section["items"]])
            lines.append("")
        if digest.closing:
            lines.extend([digest.closing, ""])
        return "\n".join(lines).strip()

    def _payload_from_stored_digest(self, stored_digest: Dict[str, object]) -> Dict[str, object]:
        stored_payload = stored_digest.get("payload")
        if isinstance(stored_payload, dict) and stored_payload.get("digest"):
            payload = dict(stored_payload)
            if not isinstance(payload.get("editor_snapshot"), dict):
                articles = [dict(article) for article in list(payload.get("articles") or [])]
                selection = self._build_digest_selection(articles)
                payload["editor_snapshot"] = self._build_editor_snapshot(
                    articles,
                    selection,
                    snapshot_status="draft",
                )
            payload["editor_snapshot"] = self._apply_editor_snapshot_metadata_from_store(
                payload.get("editor_snapshot"),
                stored_digest,
            )
            payload["stored_digest"] = stored_digest
            payload["generation_mode"] = "stored"
            return payload
        region = str(stored_digest.get("region", "all"))
        since_hours = int(stored_digest.get("since_hours") or self.settings.default_lookback_hours)
        limit = max(
            int(stored_digest.get("article_count") or 0), self.settings.llm_digest_max_articles
        )
        articles = self.repository.list_articles(
            region=region,
            since_hours=since_hours,
            limit=limit or 50,
            include_hidden=False,
        )
        presented_articles = [self._present_article(article) for article in articles]
        return {
            "schema_version": EXPORT_SCHEMA_VERSION,
            "region": region,
            "since_hours": since_hours,
            "total_articles": len(presented_articles),
            "counts_by_region": dict(Counter(article["region"] for article in presented_articles)),
            "articles": presented_articles,
            "selection_preview": [],
            "selection_decisions": [],
            "selection_summary": {
                "candidate_articles": len(presented_articles),
                "unique_candidates": len(presented_articles),
                "selected_count": 0,
                "duplicates_suppressed": 0,
                "editorially_suppressed": 0,
                "ranked_out": 0,
                "pinned_selected": 0,
                "must_include_selected": 0,
            },
            "editor_snapshot": {
                "version": int(stored_digest.get("current_version") or 1),
                "created_by": clean_text(str(stored_digest.get("created_by") or "")) or "system",
                "updated_by": clean_text(str(stored_digest.get("updated_by") or "")) or "system",
                "change_summary": clean_text(str(stored_digest.get("change_summary") or "")),
                "snapshot_status": "draft",
                "frozen_at": "",
                "updated_at": clean_text(str(stored_digest.get("updated_at") or "")),
                "last_published_at": "",
                "items": [],
            },
            "digest": dict(stored_digest.get("payload", {})),
            "body_markdown": str(stored_digest.get("body_markdown", "")),
            "generation_mode": "stored",
            "stored_digest": stored_digest,
        }

    @staticmethod
    def _payload_for_storage(payload: Dict[str, object]) -> Dict[str, object]:
        stored_payload = dict(payload)
        stored_payload.pop("stored_digest", None)
        stored_payload.pop("operation", None)
        return stored_payload

    @staticmethod
    def _apply_editor_snapshot_metadata_from_store(
        editor_snapshot: object,
        stored_digest: Dict[str, object],
    ) -> Dict[str, object]:
        snapshot = dict(editor_snapshot) if isinstance(editor_snapshot, dict) else {}
        snapshot["version"] = int(snapshot.get("version") or stored_digest.get("current_version") or 1)
        snapshot["created_by"] = clean_text(str(snapshot.get("created_by") or stored_digest.get("created_by") or "")) or "system"
        snapshot["updated_by"] = clean_text(str(snapshot.get("updated_by") or stored_digest.get("updated_by") or "")) or snapshot["created_by"]
        snapshot["change_summary"] = clean_text(
            str(snapshot.get("change_summary") or stored_digest.get("change_summary") or "")
        )
        snapshot["updated_at"] = clean_text(str(snapshot.get("updated_at") or stored_digest.get("updated_at") or ""))
        return snapshot

    def _export_digest_payload(self, payload: Dict[str, object]) -> List[str]:
        date_prefix = format_local_date().replace("-", "")
        region = str(payload.get("region", "all"))
        stem = f"{date_prefix}-{region}-ai-digest"
        markdown_path = self.settings.output_dir / f"{stem}.md"
        json_path = self.settings.output_dir / f"{stem}.json"

        markdown_path.write_text(str(payload["body_markdown"]), encoding="utf-8")
        json_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return [str(markdown_path), str(json_path)]
