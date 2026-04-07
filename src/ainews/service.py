from __future__ import annotations

import json
import logging
from collections import Counter
from typing import Dict, Iterable, List, Optional

from .config import Settings, load_settings
from .content_extractor import ArticleContentExtractor
from .feed_parser import parse_feed_document
from .http import fetch_text
from .llm import LLMClient, OpenAICompatibleLLMClient
from .models import ArticleRecord, DailyDigest
from .publisher import DigestPublisher
from .repository import ArticleRepository
from .source_registry import SourceRegistry
from .utils import clean_text, format_local_date, matches_keywords, truncate_text

EXPORT_SCHEMA_VERSION = "1.0"
logger = logging.getLogger("ainews.service")


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
    ):
        self.settings = settings or load_settings()
        self.repository = repository or ArticleRepository(self.settings.database_path)
        self.source_registry = source_registry or SourceRegistry(self.settings.sources_file)
        self.llm_client = llm_client or OpenAICompatibleLLMClient(self.settings)
        self.content_extractor = content_extractor or ArticleContentExtractor(
            timeout=self.settings.request_timeout,
            user_agent=self.settings.user_agent,
            text_limit=self.settings.extraction_text_limit,
        )
        self.publisher = publisher or DigestPublisher(self.settings)

    def list_sources(self) -> List[dict]:
        return [source.to_dict() for source in self.source_registry.list_sources()]

    def get_stats(self) -> Dict[str, object]:
        payload = self.repository.get_stats()
        payload["llm_configured"] = self.llm_client.is_configured()
        payload["llm_provider"] = self.settings.llm_provider
        payload["llm_model"] = self.settings.llm_model
        return payload

    def get_health(self) -> Dict[str, object]:
        schema_version = self.repository.get_schema_version()
        return {
            "status": "ok",
            "checks": {
                "database": "ok",
            },
            "schema_version": schema_version,
        }

    def ingest(
        self,
        *,
        source_ids: Optional[Iterable[str]] = None,
        max_items_per_source: Optional[int] = None,
    ) -> Dict[str, object]:
        logger.info(
            "starting ingest",
            extra={
                "event": "ingest.start",
            },
        )
        results = []
        inserted_total = 0
        fetched_total = 0

        for source in self.source_registry.list_sources(source_ids=source_ids):
            status = {
                "source_id": source.id,
                "source_name": source.name,
                "fetched": 0,
                "inserted": 0,
                "skipped": 0,
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
                status["fetched"] = len(filtered_articles)
                fetched_total += len(filtered_articles)

                for article in filtered_articles:
                    if self.repository.insert_if_new(article):
                        status["inserted"] += 1
                    else:
                        status["skipped"] += 1
                inserted_total += status["inserted"]
            except Exception as exc:  # pragma: no cover
                status["status"] = "error"
                status["error"] = str(exc)
                logger.warning(
                    "ingest source failed",
                    extra={
                        "event": "ingest.source_error",
                        "target": source.id,
                    },
                )
            results.append(status)

        payload = {
            "sources": results,
            "fetched_total": fetched_total,
            "inserted_total": inserted_total,
            "stored_total": self.repository.count_articles(),
        }
        logger.info(
            "completed ingest",
            extra={
                "event": "ingest.finish",
                "requested": len(results),
                "stored_total": payload["stored_total"],
            },
        )
        return payload

    def list_articles(
        self,
        *,
        region: Optional[str] = None,
        language: Optional[str] = None,
        source_id: Optional[str] = None,
        since_hours: Optional[int] = None,
        limit: int = 50,
        include_hidden: bool = False,
    ) -> List[dict]:
        rows = self.repository.list_articles(
            region=region,
            language=language,
            source_id=source_id,
            since_hours=since_hours,
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
        if not self.llm_client.is_configured():
            return {
                "status": "skipped",
                "reason": "llm_not_configured",
                "updated": 0,
                "errors": 0,
                "articles": [],
            }

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
                self.repository.mark_article_enrichment_error(
                    int(article["id"]),
                    provider=self.settings.llm_provider,
                    model=self.settings.llm_model,
                    error=str(exc),
                )
                results.append(
                    {
                        "article_id": article["id"],
                        "status": "error",
                        "title": article["title"],
                        "error": str(exc),
                    }
                )
                errors += 1

        payload = {
            "status": "ok",
            "requested": len(candidates),
            "updated": updated,
            "errors": errors,
            "articles": results,
        }
        logger.info(
            "completed enrichment",
            extra={
                "event": "enrich.finish",
                "requested": len(candidates),
                "updated": updated,
                "errors": errors,
            },
        )
        return payload

    def extract_articles(
        self,
        *,
        source_ids: Optional[Iterable[str]] = None,
        article_ids: Optional[Iterable[int]] = None,
        since_hours: Optional[int] = None,
        limit: int = 20,
        force: bool = False,
    ) -> Dict[str, object]:
        candidates = self.repository.list_articles_for_extraction(
            source_ids=source_ids,
            article_ids=article_ids,
            since_hours=since_hours,
            limit=limit,
            force=force,
        )
        results = []
        updated = 0
        errors = 0

        for article in candidates:
            try:
                extracted = self.content_extractor.fetch_and_extract(str(article["url"]))
                self.repository.save_article_extraction(
                    int(article["id"]),
                    extracted_text=extracted.text,
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
            except Exception as exc:
                self.repository.mark_article_extraction_error(
                    int(article["id"]),
                    error=str(exc),
                )
                results.append(
                    {
                        "article_id": article["id"],
                        "status": "error",
                        "title": article["title"],
                        "error": str(exc),
                    }
                )
                errors += 1

        payload = {
            "status": "ok",
            "requested": len(candidates),
            "updated": updated,
            "errors": errors,
            "articles": results,
        }
        logger.info(
            "completed extraction",
            extra={
                "event": "extract.finish",
                "requested": len(candidates),
                "updated": updated,
                "errors": errors,
            },
        )
        return payload

    def curate_article(
        self,
        article_id: int,
        *,
        is_hidden: Optional[bool] = None,
        is_pinned: Optional[bool] = None,
        editorial_note: Optional[str] = None,
    ) -> Optional[dict]:
        article = self.repository.update_article_curation(
            article_id,
            is_hidden=is_hidden,
            is_pinned=is_pinned,
            editorial_note=editorial_note,
        )
        return self._present_article(article) if article else None

    def list_digests(self, *, region: Optional[str] = None, limit: int = 20) -> List[dict]:
        return self.repository.list_digests(region=region, limit=limit)

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
                stored = self.repository.update_publication(
                    int(publication["id"]),
                    status="error",
                    message=str(exc),
                    response_payload=self._merge_publication_response(
                        publication.get("response_payload"),
                        {"status_query_error": {"message": str(exc)}},
                    ),
                )
                results.append(
                    {
                        "publication_id": publication["id"],
                        "target": publication["target"],
                        "status": "error",
                        "message": str(exc),
                        "publication": stored or publication,
                    }
                )
                errors += 1

        payload = {
            "status": "ok" if errors == 0 else "partial_error",
            "requested": len(publications),
            "refreshed": refreshed,
            "skipped": skipped,
            "errors": errors,
            "publications": results,
        }
        logger.info(
            "completed publication refresh",
            extra={
                "event": "publish.refresh_finish",
                "requested": len(publications),
                "updated": refreshed,
                "errors": errors,
            },
        )
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
        logger.info(
            "starting pipeline",
            extra={
                "event": "pipeline.start",
                "region": region,
                "since_hours": lookback,
                "limit": limit,
            },
        )
        ingest_result = self.ingest(max_items_per_source=max_items_per_source)
        extract_result = self.extract_articles(since_hours=lookback, limit=limit, force=False)
        enrich_result = self.enrich_articles(since_hours=lookback, limit=limit, force=False)
        digest_result = self.build_digest(
            region=region,
            since_hours=lookback,
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
        logger.info(
            "completed pipeline",
            extra={
                "event": "pipeline.finish",
                "region": region,
                "since_hours": lookback,
                "limit": limit,
                "generation_mode": digest_result.get("generation_mode"),
            },
        )
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
        digest_id = None
        stored_digest = payload.get("stored_digest")
        if isinstance(stored_digest, dict) and stored_digest.get("id") is not None:
            digest_id = int(stored_digest["id"])

        requested_targets = self.publisher.normalize_targets(targets)
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
            merged_targets.append(item)
            record = self.repository.save_publication(
                digest_id=digest_id,
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
        if publish_result.get("errors", 0):
            publish_result["status"] = "partial_error"
        else:
            publish_result["status"] = "ok"
        publish_result["publication_records"] = records
        logger.info(
            "completed publish",
            extra={
                "event": "publish.finish",
                "published": publish_result.get("published", 0),
                "errors": publish_result.get("errors", 0),
                "requested": len(requested_targets),
            },
        )
        return publish_result

    def build_digest(
        self,
        *,
        region: str = "all",
        since_hours: Optional[int] = None,
        limit: int = 50,
        use_llm: bool = True,
        persist: bool = False,
    ) -> Dict[str, object]:
        lookback = since_hours or self.settings.default_lookback_hours
        articles = self.repository.list_articles(
            region=region,
            since_hours=lookback,
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
                    since_hours=lookback,
                    limit=limit,
                    include_hidden=False,
                )

        presented_articles = [self._present_article(article) for article in articles]
        digest_articles = presented_articles[: self.settings.llm_digest_max_articles]

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
            )

        logger.info(
            "built digest",
            extra={
                "event": "digest.finish",
                "region": region,
                "since_hours": lookback,
                "limit": limit,
                "generation_mode": generation_mode,
                "schema_version": EXPORT_SCHEMA_VERSION,
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
        try:
            extracted = self.content_extractor.fetch_and_extract(str(article["url"]))
            updated = self.repository.save_article_extraction(
                int(article["id"]),
                extracted_text=extracted.text,
            )
            return updated or article
        except Exception as exc:
            self.repository.mark_article_extraction_error(
                int(article["id"]),
                error=str(exc),
            )
            return article

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
            "digest": dict(stored_digest.get("payload", {})),
            "body_markdown": str(stored_digest.get("body_markdown", "")),
            "generation_mode": "stored",
            "stored_digest": stored_digest,
        }

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
