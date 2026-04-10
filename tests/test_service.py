import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError

from ainews.config import Settings
from ainews.content_extractor import ExtractedContent, ExtractionSkippedError
from ainews.models import ArticleEnrichment, ArticleRecord, DailyDigest, SourceDefinition
from ainews.publisher import PublicationResult
from ainews.repository import ArticleRepository
from ainews.service import PUBLIC_ERROR_MESSAGE, PUBLIC_SKIPPED_MESSAGE, NewsService
from ainews.source_registry import SourceRegistry
from ainews.utils import make_content_hash, make_dedup_key, utc_now


class StubRegistry(SourceRegistry):
    def __init__(self, sources):
        self._sources = sources

    def list_sources(self, *, enabled_only=True, source_ids=None):
        if not source_ids:
            return self._sources
        return [source for source in self._sources if source.id in set(source_ids)]


class StubLLMClient:
    def __init__(self):
        self.enrich_calls = 0
        self.digest_calls = 0

    def is_configured(self):
        return True

    def enrich_article(self, article):
        self.enrich_calls += 1
        return ArticleEnrichment(
            title_zh=f"中文：{article['title']}",
            summary_zh="中文摘要",
            importance_zh="这条新闻值得关注。",
            provider="stub",
            model="stub-model",
        )

    def generate_digest(self, article_briefs, *, region, since_hours):
        self.digest_calls += 1
        return DailyDigest(
            title="中文 AI 日报",
            overview=f"最近 {since_hours} 小时的摘要",
            highlights=[brief["display_title_zh"] for brief in article_briefs[:2]],
            sections=[
                {
                    "title": "重点新闻",
                    "items": [brief["display_summary_zh"] for brief in article_briefs[:2]],
                }
            ],
            closing="完。",
            provider="stub",
            model="stub-model",
        )


class StubExtractor:
    def fetch_and_extract(self, url):
        return ExtractedContent(
            text=(
                "OpenAI released a new model for enterprise deployment. "
                "The update includes improved reasoning, safety work, and platform tooling. "
                "This longer body gives the LLM better context than the original feed summary."
            ),
            title="stub title",
        )


class FailingExtractor:
    def fetch_and_extract(self, url):
        raise TimeoutError("request timed out while fetching article")


class ThrottledExtractor:
    def fetch_and_extract(self, url):
        raise HTTPError(url, 429, "Too Many Requests", hdrs=None, fp=None)


class ForbiddenExtractor:
    def fetch_and_extract(self, url):
        raise HTTPError(url, 403, "Forbidden", hdrs=None, fp=None)


class LeakyExtractor:
    def fetch_and_extract(self, url):
        raise RuntimeError("internal extractor path leaked: /srv/private")


class AggregateSkipExtractor:
    def fetch_and_extract(self, url):
        raise ExtractionSkippedError(
            "skipped aggregated Google News shell page; direct article URL required"
        )


class StubGoogleNewsResolver:
    def __init__(self, mapping):
        self.mapping = dict(mapping)
        self.calls = []

    def resolve(self, url):
        self.calls.append(url)
        if url not in self.mapping:
            raise RuntimeError(f"missing mapping for {url}")
        return self.mapping[url]


class ResolvedUrlExtractor:
    def __init__(self, resolved_url):
        self.resolved_url = resolved_url

    def fetch_and_extract(self, url):
        return ExtractedContent(
            text=(
                "Arcee is trying to build a credible open source model company. "
                "Infrastructure buyers still want more optionality around deployment and cost control. "
                "The article body includes enough detail to verify the extractor stored the resolved URL."
            ),
            title="resolved title",
            resolved_url=self.resolved_url,
        )


class StubPublisher:
    def __init__(self):
        self.publish_calls = 0

    @staticmethod
    def normalize_targets(targets):
        normalized = []
        for target in list(targets or []):
            value = str(target).strip().lower().replace("-", "_")
            if value and value not in normalized:
                normalized.append(value)
        return normalized

    def publish(self, payload, *, targets=None, wechat_submit=None):
        self.publish_calls += 1
        return {
            "status": "ok",
            "targets": [
                {
                    "target": str(list(targets or ["static_site"])[0]),
                    "status": "ok",
                    "message": "published",
                    "external_id": "static:index",
                    "response": {"ok": True},
                }
            ],
            "published": 1,
            "errors": 0,
        }

    def can_refresh_publication(self, publication):
        return publication.get("target") == "wechat"

    def refresh_publication(self, publication):
        return PublicationResult(
            target="wechat",
            status="ok",
            message="wechat publish succeeded",
            external_id=str(publication.get("external_id") or "PUBLISH123"),
            response={
                "status_query": {
                    "publish_id": str(publication.get("external_id") or "PUBLISH123"),
                    "publish_status": 0,
                    "article_detail": {
                        "count": 1,
                        "item": [{"idx": 1, "article_url": "https://mp.weixin.qq.com/s/demo"}],
                    },
                }
            },
        )


class RecordingAlertNotifier:
    def __init__(self, repository=None):
        self.calls = []
        self.repository = repository

    def notify_rule(self, alert_key, **kwargs):
        self.calls.append((alert_key, kwargs))
        active = bool(kwargs.get("active"))
        if self.repository is not None:
            self.repository.save_alert_state(
                alert_key=alert_key,
                is_active=active,
                fingerprint=str(kwargs.get("fingerprint") or ""),
                last_status="active" if active else "recovered",
                last_title=str(kwargs.get("title") or ""),
                last_message=str(kwargs.get("message") or ""),
                sent_at=utc_now().isoformat() if active else "",
                recovered_at=utc_now().isoformat() if not active else "",
                increment_delivery=True,
            )
        return {
            "status": "sent" if active else "recovered",
            "alert_key": alert_key,
            "sent": True,
            "targets": [{"target": "telegram", "status": "ok"}],
        }


class ServiceFilterTestCase(unittest.TestCase):
    def test_include_keywords_filter_non_ai_items(self) -> None:
        source = SourceDefinition(
            id="36kr-ai",
            name="36Kr AI Filtered",
            url="https://36kr.com/feed",
            region="domestic",
            language="zh-CN",
            country="CN",
            topic="news",
            include_keywords=["人工智能", "AI", "大模型"],
        )
        article_keep = ArticleRecord(
            source_id=source.id,
            source_name=source.name,
            title="36Kr：大模型创业公司完成新一轮融资",
            url="https://example.com/keep",
            canonical_url="https://example.com/keep",
            summary="聚焦人工智能基础设施",
            published_at=utc_now(),
            discovered_at=utc_now(),
            language="zh-CN",
            region="domestic",
            country="CN",
            topic="news",
            content_hash=make_content_hash(
                "36Kr：大模型创业公司完成新一轮融资", "聚焦人工智能基础设施"
            ),
            dedup_key=make_dedup_key("36Kr：大模型创业公司完成新一轮融资"),
            raw_payload={},
        )
        article_skip = ArticleRecord(
            source_id=source.id,
            source_name=source.name,
            title="36Kr：消费品牌发布春季新品",
            url="https://example.com/skip",
            canonical_url="https://example.com/skip",
            summary="面向春夏市场的新品发布",
            published_at=utc_now(),
            discovered_at=utc_now(),
            language="zh-CN",
            region="domestic",
            country="CN",
            topic="news",
            content_hash=make_content_hash("36Kr：消费品牌发布春季新品", "面向春夏市场的新品发布"),
            dedup_key=make_dedup_key("36Kr：消费品牌发布春季新品"),
            raw_payload={},
        )

        filtered = NewsService._filter_articles(
            source.include_keywords,
            source.exclude_keywords,
            [article_keep, article_skip],
        )

        self.assertEqual([item.title for item in filtered], [article_keep.title])

    def test_digest_counts_articles(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = Settings(
                database_path=Path(temp_dir) / "ainews.db",
                sources_file=Path(temp_dir) / "sources.json",
            )
            repository = ArticleRepository(settings.database_path)
            source = SourceDefinition(
                id="openai-news",
                name="OpenAI News",
                url="https://openai.com/news/rss.xml",
                region="international",
                language="en",
                country="US",
                topic="company",
            )
            now = utc_now()
            repository.insert_if_new(
                ArticleRecord(
                    source_id=source.id,
                    source_name=source.name,
                    title="OpenAI launches a new model",
                    url="https://example.com/openai-model",
                    canonical_url="https://example.com/openai-model",
                    summary="A release update",
                    published_at=now,
                    discovered_at=now,
                    language="en",
                    region="international",
                    country="US",
                    topic="company",
                    content_hash=make_content_hash(
                        "OpenAI launches a new model", "A release update"
                    ),
                    dedup_key=make_dedup_key("OpenAI launches a new model"),
                    raw_payload={},
                )
            )
            service = NewsService(
                settings,
                repository=repository,
                source_registry=StubRegistry([source]),
            )

            digest = service.build_digest(region="all", since_hours=24, limit=10)

            self.assertEqual(digest["total_articles"], 1)
            self.assertEqual(digest["counts_by_region"]["international"], 1)

    def test_digest_selection_prefers_duplicate_primary_and_must_include(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = Settings(
                database_path=Path(temp_dir) / "ainews.db",
                sources_file=Path(temp_dir) / "sources.json",
            )
            repository = ArticleRepository(settings.database_path)
            source = SourceDefinition(
                id="openai-news",
                name="OpenAI News",
                url="https://openai.com/news/rss.xml",
                region="international",
                language="en",
                country="US",
                topic="company",
            )
            now = utc_now()
            repository.insert_if_new(
                ArticleRecord(
                    source_id=source.id,
                    source_name=source.name,
                    title="OpenAI launches enterprise governance controls",
                    url="https://openai.com/index/enterprise-governance",
                    canonical_url="https://openai.com/index/enterprise-governance",
                    summary="Direct release coverage.",
                    published_at=now,
                    discovered_at=now,
                    language="en",
                    region="international",
                    country="US",
                    topic="company",
                    content_hash=make_content_hash(
                        "OpenAI launches enterprise governance controls",
                        "Direct release coverage.",
                    ),
                    dedup_key=make_dedup_key("OpenAI launches enterprise governance controls"),
                    raw_payload={},
                )
            )
            repository.insert_if_new(
                ArticleRecord(
                    source_id="yahoo-ai",
                    source_name="Yahoo AI",
                    title="OpenAI launches enterprise governance controls",
                    url="https://www.yahoo.com/tech/openai-enterprise-governance-123.html",
                    canonical_url="https://www.yahoo.com/tech/openai-enterprise-governance-123.html",
                    summary="Syndicated coverage with alternative framing.",
                    published_at=now,
                    discovered_at=now,
                    language="en",
                    region="international",
                    country="US",
                    topic="company",
                    content_hash=make_content_hash(
                        "OpenAI launches enterprise governance controls",
                        "Syndicated coverage with alternative framing.",
                    ),
                    dedup_key=make_dedup_key("OpenAI launches enterprise governance controls"),
                    raw_payload={},
                )
            )
            repository.insert_if_new(
                ArticleRecord(
                    source_id="anthropic-news",
                    source_name="Anthropic News",
                    title="Anthropic documents new rollback controls",
                    url="https://anthropic.com/news/rollback-controls",
                    canonical_url="https://anthropic.com/news/rollback-controls",
                    summary="Another strong enterprise AI story.",
                    published_at=now,
                    discovered_at=now,
                    language="en",
                    region="international",
                    country="US",
                    topic="company",
                    content_hash=make_content_hash(
                        "Anthropic documents new rollback controls",
                        "Another strong enterprise AI story.",
                    ),
                    dedup_key=make_dedup_key("Anthropic documents new rollback controls"),
                    raw_payload={},
                )
            )
            anthropic = next(
                row
                for row in repository.list_articles(limit=10, include_hidden=True)
                if row["source_id"] == "anthropic-news"
            )
            repository.update_article_curation(int(anthropic["id"]), must_include=True)

            service = NewsService(
                settings,
                repository=repository,
                source_registry=StubRegistry([source]),
            )

            digest = service.build_digest(region="all", since_hours=24, limit=10, use_llm=False)

            self.assertEqual(digest["selection_summary"]["duplicates_suppressed"], 1)
            self.assertEqual(digest["selection_summary"]["must_include_selected"], 1)
            selected_ids = [item["article_id"] for item in digest["selection_preview"]]
            self.assertEqual(len(selected_ids), 2)
            self.assertIn(int(anthropic["id"]), selected_ids)
            preview_titles = [item["title"] for item in digest["selection_preview"]]
            self.assertIn("Anthropic documents new rollback controls", preview_titles[0])

    def test_enrich_and_digest_with_llm_client(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = Settings(
                database_path=Path(temp_dir) / "ainews.db",
                sources_file=Path(temp_dir) / "sources.json",
                output_dir=Path(temp_dir) / "output",
                llm_base_url="https://example.com/v1",
                llm_api_key="token",
                llm_model="stub-model",
            )
            repository = ArticleRepository(settings.database_path)
            source = SourceDefinition(
                id="openai-news",
                name="OpenAI News",
                url="https://openai.com/news/rss.xml",
                region="international",
                language="en",
                country="US",
                topic="company",
            )
            now = utc_now()
            repository.insert_if_new(
                ArticleRecord(
                    source_id=source.id,
                    source_name=source.name,
                    title="OpenAI launches a new model",
                    url="https://example.com/openai-model",
                    canonical_url="https://example.com/openai-model",
                    summary="A release update",
                    published_at=now,
                    discovered_at=now,
                    language="en",
                    region="international",
                    country="US",
                    topic="company",
                    content_hash=make_content_hash(
                        "OpenAI launches a new model", "A release update"
                    ),
                    dedup_key=make_dedup_key("OpenAI launches a new model"),
                    raw_payload={},
                )
            )
            llm_client = StubLLMClient()
            service = NewsService(
                settings,
                repository=repository,
                source_registry=StubRegistry([source]),
                llm_client=llm_client,
                content_extractor=StubExtractor(),
            )

            enrich_result = service.enrich_articles(limit=5)
            self.assertEqual(enrich_result["updated"], 1)

            digest_result = service.build_digest(
                region="all",
                since_hours=24,
                limit=10,
                use_llm=True,
                persist=True,
            )
            article = digest_result["articles"][0]
            self.assertEqual(article["display_title_zh"], "中文：OpenAI launches a new model")
            self.assertEqual(digest_result["generation_mode"], "llm")
            self.assertEqual(digest_result["stored_digest"]["title"], "中文 AI 日报")
            self.assertEqual(llm_client.enrich_calls, 1)
            self.assertEqual(llm_client.digest_calls, 1)

    def test_pipeline_exports_digest_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = Settings(
                database_path=Path(temp_dir) / "ainews.db",
                sources_file=Path(temp_dir) / "sources.json",
                output_dir=Path(temp_dir) / "output",
                llm_base_url="https://example.com/v1",
                llm_api_key="token",
                llm_model="stub-model",
            )
            settings.output_dir.mkdir(parents=True, exist_ok=True)
            repository = ArticleRepository(settings.database_path)
            source = SourceDefinition(
                id="openai-news",
                name="OpenAI News",
                url="https://openai.com/news/rss.xml",
                region="international",
                language="en",
                country="US",
                topic="company",
            )
            now = utc_now()
            repository.insert_if_new(
                ArticleRecord(
                    source_id=source.id,
                    source_name=source.name,
                    title="OpenAI launches a new model",
                    url="https://example.com/openai-model",
                    canonical_url="https://example.com/openai-model",
                    summary="A release update",
                    published_at=now,
                    discovered_at=now,
                    language="en",
                    region="international",
                    country="US",
                    topic="company",
                    content_hash=make_content_hash(
                        "OpenAI launches a new model", "A release update"
                    ),
                    dedup_key=make_dedup_key("OpenAI launches a new model"),
                    raw_payload={},
                )
            )
            service = NewsService(
                settings,
                repository=repository,
                source_registry=StubRegistry(
                    [
                        SourceDefinition(
                            id="venturebeat",
                            name="VentureBeat",
                            url="https://venturebeat.com/feed",
                            region="international",
                            language="en",
                            country="US",
                            topic="news",
                        )
                    ]
                ),
                llm_client=StubLLMClient(),
                content_extractor=StubExtractor(),
            )

            result = service.run_pipeline(
                region="all",
                since_hours=24,
                limit=10,
                use_llm=True,
                persist=True,
                export=True,
            )

            self.assertEqual(result["digest"]["schema_version"], "1.0")
            self.assertEqual(len(result["exported_files"]), 2)
            for file_path in result["exported_files"]:
                self.assertTrue(Path(file_path).exists())

    def test_publish_digest_records_publication(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = Settings(
                database_path=Path(temp_dir) / "ainews.db",
                sources_file=Path(temp_dir) / "sources.json",
                output_dir=Path(temp_dir) / "output",
                static_site_dir=Path(temp_dir) / "site",
            )
            repository = ArticleRepository(settings.database_path)
            source = SourceDefinition(
                id="openai-news",
                name="OpenAI News",
                url="https://openai.com/news/rss.xml",
                region="international",
                language="en",
                country="US",
                topic="company",
            )
            now = utc_now()
            repository.insert_if_new(
                ArticleRecord(
                    source_id=source.id,
                    source_name=source.name,
                    title="OpenAI launches a new model",
                    url="https://example.com/openai-model",
                    canonical_url="https://example.com/openai-model",
                    summary="A release update",
                    published_at=now,
                    discovered_at=now,
                    language="en",
                    region="international",
                    country="US",
                    topic="company",
                    content_hash=make_content_hash(
                        "OpenAI launches a new model", "A release update"
                    ),
                    dedup_key=make_dedup_key("OpenAI launches a new model"),
                    raw_payload={},
                )
            )
            publisher = StubPublisher()
            service = NewsService(
                settings,
                repository=repository,
                source_registry=StubRegistry([source]),
                llm_client=StubLLMClient(),
                content_extractor=StubExtractor(),
                publisher=publisher,
            )

            result = service.publish_digest(
                region="all",
                since_hours=24,
                limit=10,
                use_llm=True,
                persist=True,
                targets=["static_site"],
            )

            self.assertEqual(result["status"], "ok")
            self.assertEqual(len(result["publication_records"]), 1)
            self.assertEqual(repository.list_publications(limit=10)[0]["target"], "static_site")
            self.assertEqual(publisher.publish_calls, 1)

    def test_run_pipeline_forces_persist_when_publish_is_enabled(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = Settings(
                database_path=Path(temp_dir) / "ainews.db",
                sources_file=Path(temp_dir) / "sources.json",
                output_dir=Path(temp_dir) / "output",
                static_site_dir=Path(temp_dir) / "site",
            )
            repository = ArticleRepository(settings.database_path)
            source = SourceDefinition(
                id="openai-news",
                name="OpenAI News",
                url="https://openai.com/news/rss.xml",
                region="international",
                language="en",
                country="US",
                topic="company",
            )
            now = utc_now()
            repository.insert_if_new(
                ArticleRecord(
                    source_id=source.id,
                    source_name=source.name,
                    title="OpenAI launches a new model",
                    url="https://example.com/openai-model",
                    canonical_url="https://example.com/openai-model",
                    summary="A release update",
                    published_at=now,
                    discovered_at=now,
                    language="en",
                    region="international",
                    country="US",
                    topic="company",
                    content_hash=make_content_hash(
                        "OpenAI launches a new model", "A release update"
                    ),
                    dedup_key=make_dedup_key("OpenAI launches a new model"),
                    raw_payload={},
                )
            )
            publisher = StubPublisher()
            service = NewsService(
                settings,
                repository=repository,
                source_registry=StubRegistry([]),
                llm_client=StubLLMClient(),
                content_extractor=StubExtractor(),
                publisher=publisher,
            )

            result = service.run_pipeline(
                region="all",
                since_hours=24,
                limit=10,
                use_llm=True,
                persist=False,
                publish=True,
                publish_targets=["static_site"],
            )

            self.assertIn("stored_digest", result["digest"])
            self.assertEqual(len(result["publish"]["publication_records"]), 1)

    def test_publish_digest_skips_duplicate_target_for_stored_digest(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = Settings(
                database_path=Path(temp_dir) / "ainews.db",
                sources_file=Path(temp_dir) / "sources.json",
                output_dir=Path(temp_dir) / "output",
                static_site_dir=Path(temp_dir) / "site",
            )
            repository = ArticleRepository(settings.database_path)
            source = SourceDefinition(
                id="openai-news",
                name="OpenAI News",
                url="https://openai.com/news/rss.xml",
                region="international",
                language="en",
                country="US",
                topic="company",
            )
            now = utc_now()
            repository.insert_if_new(
                ArticleRecord(
                    source_id=source.id,
                    source_name=source.name,
                    title="OpenAI launches a new model",
                    url="https://example.com/openai-model",
                    canonical_url="https://example.com/openai-model",
                    summary="A release update",
                    published_at=now,
                    discovered_at=now,
                    language="en",
                    region="international",
                    country="US",
                    topic="company",
                    content_hash=make_content_hash(
                        "OpenAI launches a new model", "A release update"
                    ),
                    dedup_key=make_dedup_key("OpenAI launches a new model"),
                    raw_payload={},
                )
            )
            publisher = StubPublisher()
            service = NewsService(
                settings,
                repository=repository,
                source_registry=StubRegistry([source]),
                llm_client=StubLLMClient(),
                content_extractor=StubExtractor(),
                publisher=publisher,
            )

            first = service.publish_digest(
                region="all",
                since_hours=24,
                limit=10,
                use_llm=True,
                persist=True,
                targets=["static_site"],
            )
            stored_digest = first["digest"]["stored_digest"]

            second = service.publish_digest(
                digest_id=int(stored_digest["id"]),
                targets=["static_site"],
            )

            self.assertEqual(first["status"], "ok")
            self.assertEqual(second["status"], "ok")
            self.assertEqual(second["skipped"], 1)
            self.assertEqual(second["published"], 0)
            self.assertEqual(second["targets"][0]["status"], "skipped")
            self.assertEqual(len(second["publication_records"]), 0)
            self.assertEqual(len(repository.list_publications(limit=10)), 1)
            self.assertEqual(publisher.publish_calls, 1)

    def test_force_republish_allows_existing_digest_target(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = Settings(
                database_path=Path(temp_dir) / "ainews.db",
                sources_file=Path(temp_dir) / "sources.json",
                output_dir=Path(temp_dir) / "output",
                static_site_dir=Path(temp_dir) / "site",
            )
            repository = ArticleRepository(settings.database_path)
            source = SourceDefinition(
                id="openai-news",
                name="OpenAI News",
                url="https://openai.com/news/rss.xml",
                region="international",
                language="en",
                country="US",
                topic="company",
            )
            now = utc_now()
            repository.insert_if_new(
                ArticleRecord(
                    source_id=source.id,
                    source_name=source.name,
                    title="OpenAI launches a new model",
                    url="https://example.com/openai-model",
                    canonical_url="https://example.com/openai-model",
                    summary="A release update",
                    published_at=now,
                    discovered_at=now,
                    language="en",
                    region="international",
                    country="US",
                    topic="company",
                    content_hash=make_content_hash(
                        "OpenAI launches a new model", "A release update"
                    ),
                    dedup_key=make_dedup_key("OpenAI launches a new model"),
                    raw_payload={},
                )
            )
            publisher = StubPublisher()
            service = NewsService(
                settings,
                repository=repository,
                source_registry=StubRegistry([source]),
                llm_client=StubLLMClient(),
                content_extractor=StubExtractor(),
                publisher=publisher,
            )

            first = service.publish_digest(
                region="all",
                since_hours=24,
                limit=10,
                use_llm=True,
                persist=True,
                targets=["static_site"],
            )
            stored_digest = first["digest"]["stored_digest"]

            second = service.publish_digest(
                digest_id=int(stored_digest["id"]),
                targets=["static_site"],
                force_republish=True,
            )

            self.assertEqual(second["published"], 1)
            self.assertEqual(second["skipped"], 0)
            self.assertEqual(len(second["publication_records"]), 1)
            self.assertEqual(len(repository.list_publications(limit=10)), 2)
            self.assertEqual(publisher.publish_calls, 2)

    def test_refresh_publications_updates_wechat_status(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = Settings(
                database_path=Path(temp_dir) / "ainews.db",
                sources_file=Path(temp_dir) / "sources.json",
            )
            repository = ArticleRepository(settings.database_path)
            publication = repository.save_publication(
                digest_id=None,
                target="wechat",
                status="pending",
                external_id="PUBLISH123",
                message="wechat draft created and publish submitted",
                response_payload={"publish": {"publish_id": "PUBLISH123"}},
            )
            service = NewsService(
                settings,
                repository=repository,
                source_registry=StubRegistry([]),
                llm_client=StubLLMClient(),
                publisher=StubPublisher(),
            )

            result = service.refresh_publications(
                publication_ids=[int(publication["id"])],
                target="wechat",
                only_pending=True,
            )

            self.assertEqual(result["status"], "ok")
            self.assertEqual(result["refreshed"], 1)
            refreshed = repository.get_publication(int(publication["id"]))
            self.assertEqual(refreshed["status"], "ok")
            self.assertIn("status_query", refreshed["response_payload"])

    def test_health_degrades_after_operational_errors(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = Settings(
                database_path=Path(temp_dir) / "ainews.db",
                sources_file=Path(temp_dir) / "sources.json",
            )
            repository = ArticleRepository(settings.database_path)
            now = utc_now()
            repository.insert_if_new(
                ArticleRecord(
                    source_id="openai-news",
                    source_name="OpenAI News",
                    title="OpenAI launches a new model",
                    url="https://example.com/openai-model",
                    canonical_url="https://example.com/openai-model",
                    summary="A release update",
                    published_at=now,
                    discovered_at=now,
                    language="en",
                    region="international",
                    country="US",
                    topic="company",
                    content_hash=make_content_hash(
                        "OpenAI launches a new model", "A release update"
                    ),
                    dedup_key=make_dedup_key("OpenAI launches a new model"),
                    raw_payload={},
                )
            )
            service = NewsService(
                settings,
                repository=repository,
                source_registry=StubRegistry(
                    [
                        SourceDefinition(
                            id="openai-news",
                            name="OpenAI News",
                            url="https://openai.com/news/rss.xml",
                            region="international",
                            language="en",
                            country="US",
                            topic="company",
                        )
                    ]
                ),
                llm_client=StubLLMClient(),
                content_extractor=FailingExtractor(),
            )

            result = service.extract_articles(limit=5)
            health = service.get_health()

            self.assertEqual(result["status"], "partial_error")
            self.assertEqual(result["failure_categories"]["temporary_error"], 1)
            self.assertEqual(health["status"], "degraded")
            self.assertTrue(health["ready"])
            self.assertIn("article_extraction_errors", health["degraded_reasons"])
            self.assertIn("extract", health["operations"])

    def test_extract_articles_classifies_http_429_as_throttled_and_defers_retry(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = Settings(
                database_path=Path(temp_dir) / "ainews.db",
                sources_file=Path(temp_dir) / "sources.json",
            )
            repository = ArticleRepository(settings.database_path)
            now = utc_now()
            repository.insert_if_new(
                ArticleRecord(
                    source_id="venturebeat",
                    source_name="VentureBeat",
                    title="AI infrastructure story",
                    url="https://venturebeat.com/ai/story",
                    canonical_url="https://venturebeat.com/ai/story",
                    summary="A release update",
                    published_at=now,
                    discovered_at=now,
                    language="en",
                    region="international",
                    country="US",
                    topic="news",
                    content_hash=make_content_hash("AI infrastructure story", "A release update"),
                    dedup_key=make_dedup_key("AI infrastructure story"),
                    raw_payload={},
                )
            )
            service = NewsService(
                settings,
                repository=repository,
                source_registry=StubRegistry([]),
                llm_client=StubLLMClient(),
                content_extractor=ThrottledExtractor(),
            )

            result = service.extract_articles(limit=5)
            article = service.list_articles(limit=5)[0]
            queued = repository.list_articles_for_extraction(limit=10, force=False)
            health = service.get_health()
            stats = service.get_stats()

            self.assertEqual(result["status"], "partial_error")
            self.assertEqual(result["articles"][0]["status"], "throttled")
            self.assertEqual(result["articles"][0]["error_category"], "throttled")
            self.assertEqual(result["articles"][0]["http_status"], 429)
            self.assertTrue(result["articles"][0]["next_retry_at"])
            self.assertEqual(article["extraction_status"], "throttled")
            self.assertEqual(article["extraction_error_category"], "throttled")
            self.assertEqual(article["extraction_last_http_status"], 429)
            self.assertEqual(article["extraction_attempts"], 1)
            self.assertEqual(queued, [])
            self.assertIn("article_extraction_throttled", health["degraded_reasons"])
            self.assertEqual(health["stats"]["throttled_extractions"], 1)
            self.assertEqual(stats["extraction_error_categories"]["throttled"], 1)

    def test_extract_articles_classifies_http_403_as_blocked_without_requeue(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = Settings(
                database_path=Path(temp_dir) / "ainews.db",
                sources_file=Path(temp_dir) / "sources.json",
            )
            repository = ArticleRepository(settings.database_path)
            now = utc_now()
            repository.insert_if_new(
                ArticleRecord(
                    source_id="venturebeat",
                    source_name="VentureBeat",
                    title="Blocked AI story",
                    url="https://venturebeat.com/ai/blocked-story",
                    canonical_url="https://venturebeat.com/ai/blocked-story",
                    summary="A release update",
                    published_at=now,
                    discovered_at=now,
                    language="en",
                    region="international",
                    country="US",
                    topic="news",
                    content_hash=make_content_hash("Blocked AI story", "A release update"),
                    dedup_key=make_dedup_key("Blocked AI story"),
                    raw_payload={},
                )
            )
            service = NewsService(
                settings,
                repository=repository,
                source_registry=StubRegistry([]),
                llm_client=StubLLMClient(),
                content_extractor=ForbiddenExtractor(),
            )

            result = service.extract_articles(limit=5)
            article = service.list_articles(limit=5)[0]
            queued = repository.list_articles_for_extraction(limit=10, force=False)
            health = service.get_health()
            stats = service.get_stats()

            self.assertEqual(result["articles"][0]["status"], "blocked")
            self.assertEqual(result["articles"][0]["error_category"], "blocked")
            self.assertEqual(result["articles"][0]["http_status"], 403)
            self.assertEqual(article["extraction_status"], "blocked")
            self.assertEqual(article["extraction_error_category"], "blocked")
            self.assertEqual(article["extraction_last_http_status"], 403)
            self.assertEqual(article["extraction_attempts"], 1)
            self.assertEqual(queued, [])
            self.assertIn("article_extraction_blocked", health["degraded_reasons"])
            self.assertEqual(health["stats"]["blocked_extractions"], 1)
            self.assertEqual(stats["extraction_error_categories"]["blocked"], 1)

    def test_consecutive_source_failures_trigger_runtime_cooldown(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = Settings(
                database_path=Path(temp_dir) / "ainews.db",
                sources_file=Path(temp_dir) / "sources.json",
                source_cooldown_failure_threshold=2,
                source_blocked_cooldown_minutes=720,
            )
            repository = ArticleRepository(settings.database_path)
            now = utc_now()
            for index in range(2):
                repository.insert_if_new(
                    ArticleRecord(
                        source_id="venturebeat",
                        source_name="VentureBeat",
                        title=f"Blocked source story {index}",
                        url=f"https://venturebeat.com/ai/blocked-{index}",
                        canonical_url=f"https://venturebeat.com/ai/blocked-{index}",
                        summary="A release update",
                        published_at=now,
                        discovered_at=now,
                        language="en",
                        region="international",
                        country="US",
                        topic="news",
                        content_hash=make_content_hash(
                            f"Blocked source story {index}", "A release update"
                        ),
                        dedup_key=make_dedup_key(f"Blocked source story {index}"),
                        raw_payload={},
                    )
                )
            service = NewsService(
                settings,
                repository=repository,
                source_registry=StubRegistry(
                    [
                        SourceDefinition(
                            id="venturebeat",
                            name="VentureBeat",
                            url="https://venturebeat.com/feed",
                            region="international",
                            language="en",
                            country="US",
                            topic="news",
                        )
                    ]
                ),
                llm_client=StubLLMClient(),
                content_extractor=ForbiddenExtractor(),
            )

            result = service.extract_articles(limit=10)
            state = repository.get_source_state("venturebeat")
            health = service.get_health()
            sources = service.list_sources(include_runtime=True)

            self.assertEqual(result["errors"], 2)
            self.assertEqual(state["consecutive_failures"], 2)
            self.assertEqual(state["cooldown_status"], "blocked")
            self.assertTrue(state["cooldown_until"])
            self.assertEqual(health["stats"]["active_source_cooldowns"], 1)
            self.assertIn("source_cooldowns_active", health["degraded_reasons"])
            self.assertTrue(sources[0]["cooldown_active"])
            self.assertEqual(sources[0]["cooldown_status"], "blocked")

    def test_source_cooldown_dispatches_runtime_alerts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = Settings(
                database_path=Path(temp_dir) / "ainews.db",
                sources_file=Path(temp_dir) / "sources.json",
                source_cooldown_failure_threshold=2,
            )
            repository = ArticleRepository(settings.database_path)
            alert_notifier = RecordingAlertNotifier(repository)
            now = utc_now()
            for index in range(2):
                repository.insert_if_new(
                    ArticleRecord(
                        source_id="venturebeat",
                        source_name="VentureBeat",
                        title=f"Alert cooldown story {index}",
                        url=f"https://venturebeat.com/ai/alert-{index}",
                        canonical_url=f"https://venturebeat.com/ai/alert-{index}",
                        summary="A release update",
                        published_at=now,
                        discovered_at=now,
                        language="en",
                        region="international",
                        country="US",
                        topic="news",
                        content_hash=make_content_hash(
                            f"Alert cooldown story {index}", "A release update"
                        ),
                        dedup_key=make_dedup_key(f"Alert cooldown story {index}"),
                        raw_payload={},
                    )
                )
            service = NewsService(
                settings,
                repository=repository,
                source_registry=StubRegistry([]),
                llm_client=StubLLMClient(),
                content_extractor=ForbiddenExtractor(),
                alert_notifier=alert_notifier,
            )

            service.extract_articles(limit=10)

            keys = [item[0] for item in alert_notifier.calls]
            self.assertIn("health_status", keys)
            self.assertIn("source_cooldowns_active", keys)

    def test_source_cooldown_skips_remaining_articles_in_batch(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = Settings(
                database_path=Path(temp_dir) / "ainews.db",
                sources_file=Path(temp_dir) / "sources.json",
                source_cooldown_failure_threshold=2,
            )
            repository = ArticleRepository(settings.database_path)
            now = utc_now()
            for index in range(3):
                repository.insert_if_new(
                    ArticleRecord(
                        source_id="venturebeat",
                        source_name="VentureBeat",
                        title=f"Cooldown batch story {index}",
                        url=f"https://venturebeat.com/ai/cooldown-{index}",
                        canonical_url=f"https://venturebeat.com/ai/cooldown-{index}",
                        summary="A release update",
                        published_at=now,
                        discovered_at=now,
                        language="en",
                        region="international",
                        country="US",
                        topic="news",
                        content_hash=make_content_hash(
                            f"Cooldown batch story {index}", "A release update"
                        ),
                        dedup_key=make_dedup_key(f"Cooldown batch story {index}"),
                        raw_payload={},
                    )
                )
            service = NewsService(
                settings,
                repository=repository,
                source_registry=StubRegistry([]),
                llm_client=StubLLMClient(),
                content_extractor=ForbiddenExtractor(),
            )

            result = service.extract_articles(limit=10)

            self.assertEqual(result["articles"][2]["status"], "skipped")
            self.assertIn("cooldown", result["articles"][2]["message"])

    def test_source_maintenance_blocks_extraction_queue(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = Settings(
                database_path=Path(temp_dir) / "ainews.db",
                sources_file=Path(temp_dir) / "sources.json",
            )
            repository = ArticleRepository(settings.database_path)
            now = utc_now()
            repository.insert_if_new(
                ArticleRecord(
                    source_id="venturebeat",
                    source_name="VentureBeat",
                    title="Maintenance article",
                    url="https://venturebeat.com/ai/maintenance",
                    canonical_url="https://venturebeat.com/ai/maintenance",
                    summary="A release update",
                    published_at=now,
                    discovered_at=now,
                    language="en",
                    region="international",
                    country="US",
                    topic="news",
                    content_hash=make_content_hash("Maintenance article", "A release update"),
                    dedup_key=make_dedup_key("Maintenance article"),
                    raw_payload={},
                )
            )
            repository.update_source_runtime_controls(
                source_id="venturebeat",
                source_name="VentureBeat",
                maintenance_mode=True,
            )
            service = NewsService(
                settings,
                repository=repository,
                source_registry=StubRegistry(
                    [
                        SourceDefinition(
                            id="venturebeat",
                            name="VentureBeat",
                            url="https://venturebeat.com/feed",
                            region="international",
                            language="en",
                            country="US",
                            topic="news",
                        )
                    ]
                ),
                llm_client=StubLLMClient(),
                content_extractor=StubExtractor(),
            )

            result = service.extract_articles(limit=10)
            source = service.list_sources(include_runtime=True)

            self.assertEqual(result["requested"], 0)
            self.assertTrue(source[0]["maintenance_mode"])

    def test_snoozed_or_acknowledged_source_suppresses_active_source_alert(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = Settings(
                database_path=Path(temp_dir) / "ainews.db",
                sources_file=Path(temp_dir) / "sources.json",
            )
            repository = ArticleRepository(settings.database_path)
            alert_notifier = RecordingAlertNotifier(repository)
            repository.upsert_source_state(
                source_id="venturebeat",
                source_name="VentureBeat",
                cooldown_status="blocked",
                cooldown_until="2999-01-01T00:00:00+00:00",
                consecutive_failures=2,
                last_error_category="blocked",
                last_http_status=403,
                last_error=PUBLIC_ERROR_MESSAGE,
                last_error_at=utc_now().isoformat(),
                silenced_until="2999-01-01T00:00:00+00:00",
                acknowledged_at=utc_now().isoformat(),
                ack_note="known issue",
            )
            service = NewsService(
                settings,
                repository=repository,
                source_registry=StubRegistry([]),
                alert_notifier=alert_notifier,
            )

            service._dispatch_runtime_alerts()

            keys = [item[0] for item in alert_notifier.calls]
            aggregate_call = next(
                item for item in alert_notifier.calls if item[0] == "source_cooldowns_active"
            )
            self.assertFalse(bool(aggregate_call[1].get("active")))
            self.assertFalse(any(key.startswith("source_cooldown:") for key in keys))

    def test_reset_source_cooldowns_clears_runtime_block(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = Settings(
                database_path=Path(temp_dir) / "ainews.db",
                sources_file=Path(temp_dir) / "sources.json",
            )
            repository = ArticleRepository(settings.database_path)
            repository.upsert_source_state(
                source_id="venturebeat",
                source_name="VentureBeat",
                cooldown_status="blocked",
                cooldown_until="2999-01-01T00:00:00+00:00",
                consecutive_failures=2,
                last_error_category="blocked",
                last_http_status=403,
                last_error=PUBLIC_ERROR_MESSAGE,
                last_error_at=utc_now().isoformat(),
            )
            service = NewsService(
                settings,
                repository=repository,
                source_registry=StubRegistry([]),
            )

            result = service.reset_source_cooldowns(source_ids=["venturebeat"], active_only=False)
            state = repository.get_source_state("venturebeat")

            self.assertEqual(result["cleared"], 1)
            self.assertEqual(state["cooldown_status"], "")
            self.assertEqual(state["cooldown_until"], "")
            self.assertEqual(state["acknowledged_at"], "")
            self.assertEqual(state["ack_note"], "")

    def test_source_cooldown_alert_history_closes_on_recovery(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = Settings(
                database_path=Path(temp_dir) / "ainews.db",
                sources_file=Path(temp_dir) / "sources.json",
                source_cooldown_failure_threshold=2,
            )
            repository = ArticleRepository(settings.database_path)
            alert_notifier = RecordingAlertNotifier(repository)
            now = utc_now()
            for index in range(2):
                repository.insert_if_new(
                    ArticleRecord(
                        source_id="venturebeat",
                        source_name="VentureBeat",
                        title=f"Cooldown alert story {index}",
                        url=f"https://venturebeat.com/ai/alert-history-{index}",
                        canonical_url=f"https://venturebeat.com/ai/alert-history-{index}",
                        summary="A release update",
                        published_at=now,
                        discovered_at=now,
                        language="en",
                        region="international",
                        country="US",
                        topic="news",
                        content_hash=make_content_hash(
                            f"Cooldown alert story {index}", "A release update"
                        ),
                        dedup_key=make_dedup_key(f"Cooldown alert story {index}"),
                        raw_payload={},
                    )
                )
            service = NewsService(
                settings,
                repository=repository,
                source_registry=StubRegistry([]),
                llm_client=StubLLMClient(),
                content_extractor=ForbiddenExtractor(),
                alert_notifier=alert_notifier,
            )

            service.extract_articles(limit=10)
            active_alerts = service.list_source_alerts(limit=10)

            self.assertEqual(len(active_alerts), 1)
            self.assertEqual(active_alerts[0]["source_id"], "venturebeat")
            self.assertEqual(active_alerts[0]["alert_status"], "sent")

            service.reset_source_cooldowns(source_ids=["venturebeat"], active_only=False)
            alert_history = service.list_source_alerts(limit=10)

            self.assertEqual(len(alert_history), 2)
            self.assertEqual(alert_history[0]["alert_status"], "recovered")
            self.assertEqual(alert_history[0]["targets"][0]["target"], "telegram")
            self.assertEqual(alert_history[1]["alert_status"], "sent")

    def test_source_control_methods_update_runtime_state(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = Settings(
                database_path=Path(temp_dir) / "ainews.db",
                sources_file=Path(temp_dir) / "sources.json",
            )
            repository = ArticleRepository(settings.database_path)
            service = NewsService(
                settings,
                repository=repository,
                source_registry=StubRegistry(
                    [
                        SourceDefinition(
                            id="venturebeat",
                            name="VentureBeat",
                            url="https://venturebeat.com/feed",
                            region="international",
                            language="en",
                            country="US",
                            topic="news",
                        )
                    ]
                ),
            )

            acknowledge = service.acknowledge_source_alerts(
                source_ids=["venturebeat"],
                note="known cooldown",
            )
            snooze = service.snooze_source_alerts(source_ids=["venturebeat"], minutes=30)
            maintenance = service.set_source_maintenance(source_ids=["venturebeat"], enabled=True)
            source = service.list_sources(include_runtime=True)[0]

            self.assertEqual(acknowledge["acknowledged"], 1)
            self.assertEqual(snooze["updated"], 1)
            self.assertEqual(maintenance["updated"], 1)
            self.assertEqual(source["ack_note"], "known cooldown")
            self.assertTrue(source["silenced_active"])
            self.assertTrue(source["maintenance_mode"])

    def test_source_auto_recovery_requires_consecutive_successes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = Settings(
                database_path=Path(temp_dir) / "ainews.db",
                sources_file=Path(temp_dir) / "sources.json",
                source_recovery_success_threshold=2,
            )
            repository = ArticleRepository(settings.database_path)
            published = utc_now()
            for index in range(2):
                repository.insert_if_new(
                    ArticleRecord(
                        source_id="venturebeat",
                        source_name="VentureBeat",
                        title=f"Recovery story {index}",
                        url=f"https://venturebeat.com/ai/recovery-{index}",
                        canonical_url=f"https://venturebeat.com/ai/recovery-{index}",
                        summary="Recovery validation story",
                        published_at=published,
                        discovered_at=published,
                        language="en",
                        region="international",
                        country="US",
                        topic="news",
                        content_hash=make_content_hash(
                            f"Recovery story {index}", "Recovery validation story"
                        ),
                        dedup_key=make_dedup_key(f"Recovery story {index}"),
                        raw_payload={},
                    )
                )
            repository.upsert_source_state(
                source_id="venturebeat",
                source_name="VentureBeat",
                cooldown_status="blocked",
                cooldown_until="2000-01-01T00:00:00+00:00",
                consecutive_failures=2,
                last_error_category="blocked",
                last_http_status=403,
                last_error=PUBLIC_ERROR_MESSAGE,
                last_error_at=utc_now().isoformat(),
                acknowledged_at="2026-04-08T00:00:00+00:00",
                ack_note="owned by on-call",
            )
            service = NewsService(
                settings,
                repository=repository,
                source_registry=StubRegistry([]),
                llm_client=StubLLMClient(),
                content_extractor=StubExtractor(),
            )

            result = service.extract_articles(limit=10)
            state = repository.get_source_state("venturebeat")
            events = repository.list_source_events(source_id="venturebeat", limit=10)
            recovered_event = next(
                event for event in events if event["event_type"] == "cooldown" and event["status"] == "recovered"
            )

            self.assertEqual(result["updated"], 2)
            self.assertEqual(state["cooldown_status"], "")
            self.assertEqual(state["acknowledged_at"], "")
            self.assertEqual(state["ack_note"], "")
            self.assertEqual(state["consecutive_successes"], 2)
            self.assertTrue(state["last_recovered_at"])
            self.assertIn("recovered after 2 consecutive successful extractions", recovered_event["message"])

    def test_source_alert_reactivates_after_snooze_expires(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = Settings(
                database_path=Path(temp_dir) / "ainews.db",
                sources_file=Path(temp_dir) / "sources.json",
            )
            repository = ArticleRepository(settings.database_path)
            alert_notifier = RecordingAlertNotifier(repository)
            repository.upsert_source_state(
                source_id="venturebeat",
                source_name="VentureBeat",
                cooldown_status="blocked",
                cooldown_until="2999-01-01T00:00:00+00:00",
                consecutive_failures=2,
                last_error_category="blocked",
                last_http_status=403,
                last_error=PUBLIC_ERROR_MESSAGE,
                last_error_at=utc_now().isoformat(),
            )
            service = NewsService(
                settings,
                repository=repository,
                source_registry=StubRegistry([]),
                alert_notifier=alert_notifier,
            )

            service._dispatch_runtime_alerts()
            service.snooze_source_alerts(source_ids=["venturebeat"], minutes=60)
            repository.update_source_runtime_controls(
                source_id="venturebeat",
                source_name="VentureBeat",
                silenced_until="2000-01-01T00:00:00+00:00",
            )

            service._dispatch_runtime_alerts()
            alert_history = service.list_source_alerts(source_id="venturebeat", limit=10)
            source_alert_calls = [
                item for item in alert_notifier.calls if item[0] == "source_cooldown:venturebeat"
            ]

            self.assertEqual(len(source_alert_calls), 2)
            self.assertEqual(len(alert_history), 2)
            self.assertEqual(alert_history[0]["alert_status"], "sent")
            self.assertEqual(alert_history[1]["alert_status"], "sent")

    def test_prune_source_runtime_history_uses_default_retention(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = Settings(
                database_path=Path(temp_dir) / "ainews.db",
                sources_file=Path(temp_dir) / "sources.json",
                source_runtime_retention_days=21,
            )
            repository = ArticleRepository(settings.database_path)
            repository.record_source_event(
                source_id="venturebeat",
                source_name="VentureBeat",
                event_type="extract",
                status="blocked",
                error_category="blocked",
                http_status=403,
                message="old event",
            )
            service = NewsService(
                settings,
                repository=repository,
                source_registry=StubRegistry([]),
            )

            with patch.object(repository, "prune_source_runtime_history", wraps=repository.prune_source_runtime_history) as prune_runtime:
                result = service.prune_source_runtime_history()

            prune_runtime.assert_called_once_with(retention_days=21, archive=True)
            self.assertEqual(result["status"], "ok")
            self.assertEqual(result["retention_days"], 21)
            self.assertIn("operation", result)

    def test_pipeline_partial_error_dispatches_pipeline_alert(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = Settings(
                database_path=Path(temp_dir) / "ainews.db",
                sources_file=Path(temp_dir) / "sources.json",
            )
            repository = ArticleRepository(settings.database_path)
            alert_notifier = RecordingAlertNotifier()
            now = utc_now()
            repository.insert_if_new(
                ArticleRecord(
                    source_id="openai-news",
                    source_name="OpenAI News",
                    title="Pipeline alert article",
                    url="https://example.com/pipeline-alert",
                    canonical_url="https://example.com/pipeline-alert",
                    summary="A release update",
                    published_at=now,
                    discovered_at=now,
                    language="en",
                    region="international",
                    country="US",
                    topic="company",
                    content_hash=make_content_hash("Pipeline alert article", "A release update"),
                    dedup_key=make_dedup_key("Pipeline alert article"),
                    raw_payload={},
                )
            )
            service = NewsService(
                settings,
                repository=repository,
                source_registry=StubRegistry([]),
                llm_client=StubLLMClient(),
                content_extractor=FailingExtractor(),
                alert_notifier=alert_notifier,
            )

            service.run_pipeline(region="all", since_hours=24, limit=10, use_llm=True, persist=True)

            keys = [item[0] for item in alert_notifier.calls]
            self.assertIn("pipeline_status", keys)

    def test_publish_partial_error_dispatches_publish_alert(self) -> None:
        class FailingPublisher(StubPublisher):
            def publish(self, payload, *, targets=None, wechat_submit=None):
                return {
                    "status": "partial_error",
                    "targets": [
                        {
                            "target": "feishu",
                            "status": "error",
                            "message": "feishu webhook failed",
                            "external_id": "",
                            "response": {},
                        }
                    ],
                    "published": 0,
                    "errors": 1,
                }

        with tempfile.TemporaryDirectory() as temp_dir:
            settings = Settings(
                database_path=Path(temp_dir) / "ainews.db",
                sources_file=Path(temp_dir) / "sources.json",
            )
            repository = ArticleRepository(settings.database_path)
            alert_notifier = RecordingAlertNotifier()
            now = utc_now()
            repository.insert_if_new(
                ArticleRecord(
                    source_id="openai-news",
                    source_name="OpenAI News",
                    title="Publish alert article",
                    url="https://example.com/publish-alert",
                    canonical_url="https://example.com/publish-alert",
                    summary="A release update",
                    published_at=now,
                    discovered_at=now,
                    language="en",
                    region="international",
                    country="US",
                    topic="company",
                    content_hash=make_content_hash("Publish alert article", "A release update"),
                    dedup_key=make_dedup_key("Publish alert article"),
                    raw_payload={},
                )
            )
            service = NewsService(
                settings,
                repository=repository,
                source_registry=StubRegistry([]),
                llm_client=StubLLMClient(),
                content_extractor=StubExtractor(),
                publisher=FailingPublisher(),
                alert_notifier=alert_notifier,
            )

            service.publish_digest(region="all", since_hours=24, limit=10, use_llm=True, persist=True, targets=["feishu"])

            keys = [item[0] for item in alert_notifier.calls]
            self.assertIn("publish_status", keys)

    def test_extract_articles_marks_short_body_as_permanent_error(self) -> None:
        class ShortBodyExtractor:
            def fetch_and_extract(self, url):
                raise ValueError("extracted article text is too short")

        with tempfile.TemporaryDirectory() as temp_dir:
            settings = Settings(
                database_path=Path(temp_dir) / "ainews.db",
                sources_file=Path(temp_dir) / "sources.json",
            )
            repository = ArticleRepository(settings.database_path)
            now = utc_now()
            repository.insert_if_new(
                ArticleRecord(
                    source_id="openai-news",
                    source_name="OpenAI News",
                    title="Short article",
                    url="https://example.com/short",
                    canonical_url="https://example.com/short",
                    summary="A release update",
                    published_at=now,
                    discovered_at=now,
                    language="en",
                    region="international",
                    country="US",
                    topic="company",
                    content_hash=make_content_hash("Short article", "A release update"),
                    dedup_key=make_dedup_key("Short article"),
                    raw_payload={},
                )
            )
            service = NewsService(
                settings,
                repository=repository,
                source_registry=StubRegistry([]),
                llm_client=StubLLMClient(),
                content_extractor=ShortBodyExtractor(),
            )

            result = service.extract_articles(limit=5)
            article = service.list_articles(limit=5)[0]

            self.assertEqual(result["articles"][0]["status"], "permanent_error")
            self.assertEqual(article["extraction_status"], "permanent_error")
            self.assertEqual(article["extraction_error_category"], "permanent_error")
            self.assertEqual(repository.list_articles_for_extraction(limit=10, force=False), [])

    def test_retry_window_requeues_temporary_errors_after_deadline(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = Settings(
                database_path=Path(temp_dir) / "ainews.db",
                sources_file=Path(temp_dir) / "sources.json",
            )
            repository = ArticleRepository(settings.database_path)
            now = utc_now()
            repository.insert_if_new(
                ArticleRecord(
                    source_id="openai-news",
                    source_name="OpenAI News",
                    title="Retry article",
                    url="https://example.com/retry",
                    canonical_url="https://example.com/retry",
                    summary="A release update",
                    published_at=now,
                    discovered_at=now,
                    language="en",
                    region="international",
                    country="US",
                    topic="company",
                    content_hash=make_content_hash("Retry article", "A release update"),
                    dedup_key=make_dedup_key("Retry article"),
                    raw_payload={},
                )
            )
            stored = repository.list_articles(limit=5, include_hidden=True)[0]
            repository.mark_article_extraction_failure(
                int(stored["id"]),
                error=PUBLIC_ERROR_MESSAGE,
                status="temporary_error",
                error_category="temporary_error",
                next_retry_at="2999-01-01T00:00:00+00:00",
            )

            self.assertEqual(repository.list_articles_for_extraction(limit=10, force=False), [])

            with repository._connect() as connection:
                connection.execute(
                    """
                    UPDATE articles
                    SET extraction_next_retry_at = '2000-01-01T00:00:00+00:00'
                    WHERE id = ?
                    """,
                    (int(stored["id"]),),
                )

            queued = repository.list_articles_for_extraction(limit=10, force=False)
            self.assertEqual(len(queued), 1)

    def test_retry_extractions_can_target_blocked_articles_manually(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = Settings(
                database_path=Path(temp_dir) / "ainews.db",
                sources_file=Path(temp_dir) / "sources.json",
            )
            repository = ArticleRepository(settings.database_path)
            now = utc_now()
            repository.insert_if_new(
                ArticleRecord(
                    source_id="venturebeat",
                    source_name="VentureBeat",
                    title="Retry blocked article",
                    url="https://venturebeat.com/ai/retry-blocked",
                    canonical_url="https://venturebeat.com/ai/retry-blocked",
                    summary="Blocked before",
                    published_at=now,
                    discovered_at=now,
                    language="en",
                    region="international",
                    country="US",
                    topic="news",
                    content_hash=make_content_hash("Retry blocked article", "Blocked before"),
                    dedup_key=make_dedup_key("Retry blocked article"),
                    raw_payload={},
                )
            )
            stored = repository.list_articles(limit=5, include_hidden=True)[0]
            repository.mark_article_extraction_failure(
                int(stored["id"]),
                error=PUBLIC_ERROR_MESSAGE,
                status="blocked",
                error_category="blocked",
                http_status=403,
                next_retry_at="2999-01-01T00:00:00+00:00",
            )
            service = NewsService(
                settings,
                repository=repository,
                source_registry=StubRegistry([]),
                llm_client=StubLLMClient(),
                content_extractor=StubExtractor(),
            )

            result = service.retry_extractions(
                extraction_status="blocked",
                due_only=False,
                limit=5,
            )
            article = service.list_articles(limit=5)[0]

            self.assertEqual(result["retry_mode"], "manual")
            self.assertEqual(result["updated"], 1)
            self.assertEqual(result["requested_filters"]["extraction_status"], "blocked")
            self.assertEqual(article["extraction_status"], "ready")

    def test_extract_articles_masks_internal_error_details(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = Settings(
                database_path=Path(temp_dir) / "ainews.db",
                sources_file=Path(temp_dir) / "sources.json",
            )
            repository = ArticleRepository(settings.database_path)
            now = utc_now()
            repository.insert_if_new(
                ArticleRecord(
                    source_id="openai-news",
                    source_name="OpenAI News",
                    title="OpenAI launches a new model",
                    url="https://example.com/openai-model",
                    canonical_url="https://example.com/openai-model",
                    summary="A release update",
                    published_at=now,
                    discovered_at=now,
                    language="en",
                    region="international",
                    country="US",
                    topic="company",
                    content_hash=make_content_hash(
                        "OpenAI launches a new model", "A release update"
                    ),
                    dedup_key=make_dedup_key("OpenAI launches a new model"),
                    raw_payload={},
                )
            )
            service = NewsService(
                settings,
                repository=repository,
                source_registry=StubRegistry([]),
                llm_client=StubLLMClient(),
                content_extractor=LeakyExtractor(),
            )

            result = service.extract_articles(limit=5)
            article = service.list_articles(limit=5)[0]

            self.assertEqual(result["articles"][0]["error"], PUBLIC_ERROR_MESSAGE)
            self.assertEqual(article["extraction_error"], PUBLIC_ERROR_MESSAGE)
            self.assertNotIn("/srv/private", json.dumps(result))

    def test_extract_articles_skips_aggregate_shell_without_degrading_health(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = Settings(
                database_path=Path(temp_dir) / "ainews.db",
                sources_file=Path(temp_dir) / "sources.json",
            )
            repository = ArticleRepository(settings.database_path)
            now = utc_now()
            repository.insert_if_new(
                ArticleRecord(
                    source_id="google-news-global-ai",
                    source_name="Google News Global AI",
                    title="Anthropic security story",
                    url="https://news.google.com/rss/articles/demo?oc=5",
                    canonical_url="https://news.google.com/rss/articles/demo?oc=5",
                    summary="A release update",
                    published_at=now,
                    discovered_at=now,
                    language="en",
                    region="international",
                    country="US",
                    topic="news",
                    content_hash=make_content_hash(
                        "Anthropic security story", "A release update"
                    ),
                    dedup_key=make_dedup_key("Anthropic security story"),
                    raw_payload={},
                )
            )
            service = NewsService(
                settings,
                repository=repository,
                source_registry=StubRegistry(
                    [
                        SourceDefinition(
                            id="google-news-global-ai",
                            name="Google News Global AI",
                            url="https://news.google.com/rss/search?q=ai",
                            region="international",
                            language="en",
                            country="US",
                            topic="news",
                        )
                    ]
                ),
                llm_client=StubLLMClient(),
                content_extractor=AggregateSkipExtractor(),
            )

            result = service.extract_articles(limit=5)
            article = service.list_articles(limit=5)[0]
            health = service.get_health()
            stats = service.get_stats()

            self.assertEqual(result["status"], "ok")
            self.assertEqual(result["skipped"], 1)
            self.assertEqual(result["errors"], 0)
            self.assertEqual(result["articles"][0]["status"], "skipped")
            self.assertEqual(result["articles"][0]["message"], PUBLIC_SKIPPED_MESSAGE)
            self.assertEqual(article["extraction_status"], "skipped")
            self.assertEqual(article["extraction_error"], PUBLIC_SKIPPED_MESSAGE)
            self.assertEqual(health["status"], "ok")
            self.assertNotIn("article_extraction_errors", health["degraded_reasons"])
            self.assertEqual(stats["skipped_extractions"], 1)
            self.assertNotIn("direct article URL required", json.dumps(result))

    def test_extract_articles_persists_resolved_google_news_target_url(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = Settings(
                database_path=Path(temp_dir) / "ainews.db",
                sources_file=Path(temp_dir) / "sources.json",
            )
            repository = ArticleRepository(settings.database_path)
            now = utc_now()
            repository.insert_if_new(
                ArticleRecord(
                    source_id="google-news-global-ai",
                    source_name="Google News Global AI",
                    title="Arcee story",
                    url="https://news.google.com/rss/articles/demo?oc=5",
                    canonical_url="https://news.google.com/rss/articles/demo?oc=5",
                    summary="A release update",
                    published_at=now,
                    discovered_at=now,
                    language="en",
                    region="international",
                    country="US",
                    topic="news",
                    content_hash=make_content_hash("Arcee story", "A release update"),
                    dedup_key=make_dedup_key("Arcee story"),
                    raw_payload={},
                )
            )
            service = NewsService(
                settings,
                repository=repository,
                source_registry=StubRegistry([]),
                llm_client=StubLLMClient(),
                content_extractor=ResolvedUrlExtractor(
                    "https://techcrunch.com/2026/04/07/arcee/"
                ),
            )

            result = service.extract_articles(limit=5)
            article = service.list_articles(limit=5)[0]

            self.assertEqual(result["updated"], 1)
            self.assertEqual(article["url"], "https://techcrunch.com/2026/04/07/arcee/")
            self.assertEqual(article["canonical_url"], "https://techcrunch.com/2026/04/07/arcee/")

    def test_ingest_resolves_google_news_urls_before_insert_and_dedupes(self) -> None:
        feed_xml = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Google News AI</title>
    <item>
      <title>OpenAI launches a new reasoning model</title>
      <link>https://news.google.com/rss/articles/demo-one?oc=5</link>
      <description><![CDATA[<p>First summary.</p>]]></description>
      <pubDate>Tue, 08 Apr 2026 08:00:00 GMT</pubDate>
    </item>
    <item>
      <title>Why OpenAI's new reasoning model matters</title>
      <link>https://news.google.com/rss/articles/demo-two?oc=5</link>
      <description><![CDATA[<p>Second summary.</p>]]></description>
      <pubDate>Tue, 08 Apr 2026 08:05:00 GMT</pubDate>
    </item>
  </channel>
</rss>
"""
        resolver = StubGoogleNewsResolver(
            {
                "https://news.google.com/rss/articles/demo-one?oc=5": "https://openai.com/index/new-model/",
                "https://news.google.com/rss/articles/demo-two?oc=5": "https://openai.com/index/new-model/",
            }
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            settings = Settings(
                database_path=Path(temp_dir) / "ainews.db",
                sources_file=Path(temp_dir) / "sources.json",
            )
            source = SourceDefinition(
                id="google-news-global-ai",
                name="Google News Global AI",
                url="https://example.com/feed/google-news.xml",
                region="international",
                language="en",
                country="US",
                topic="news",
            )
            service = NewsService(
                settings,
                repository=ArticleRepository(settings.database_path),
                source_registry=StubRegistry([source]),
                google_news_resolver=resolver,
            )

            with patch("ainews.service.fetch_text", return_value=feed_xml):
                result = service.ingest(source_ids=[source.id], max_items_per_source=10)

            articles = service.list_articles(limit=10)
            self.assertEqual(result["inserted_total"], 1)
            self.assertEqual(result["resolved_total"], 2)
            self.assertEqual(result["resolution_errors"], 0)
            self.assertEqual(articles[0]["url"], "https://openai.com/index/new-model/")
            self.assertEqual(articles[0]["canonical_url"], "https://openai.com/index/new-model")

    def test_resolve_google_news_urls_merges_existing_direct_article(self) -> None:
        resolver = StubGoogleNewsResolver(
            {
                "https://news.google.com/rss/articles/demo?oc=5": "https://openai.com/index/new-model/",
            }
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            settings = Settings(
                database_path=Path(temp_dir) / "ainews.db",
                sources_file=Path(temp_dir) / "sources.json",
            )
            repository = ArticleRepository(settings.database_path)
            now = utc_now()
            repository.insert_if_new(
                ArticleRecord(
                    source_id="direct",
                    source_name="OpenAI News",
                    title="OpenAI model story",
                    url="https://openai.com/index/new-model/",
                    canonical_url="https://openai.com/index/new-model",
                    summary="Short direct summary",
                    published_at=now,
                    discovered_at=now,
                    language="en",
                    region="international",
                    country="US",
                    topic="news",
                    content_hash=make_content_hash("OpenAI model story", "Short direct summary"),
                    dedup_key=make_dedup_key("OpenAI model story"),
                    raw_payload={"link": "https://openai.com/index/new-model/"},
                )
            )
            repository.insert_if_new(
                ArticleRecord(
                    source_id="google-news",
                    source_name="Google News",
                    title="OpenAI model story",
                    url="https://news.google.com/rss/articles/demo?oc=5",
                    canonical_url="https://news.google.com/rss/articles/demo?oc=5",
                    summary="Longer wrapper summary with more context",
                    published_at=now,
                    discovered_at=now,
                    language="en",
                    region="international",
                    country="US",
                    topic="news",
                    content_hash=make_content_hash("OpenAI model story wrapper", "Longer wrapper summary with more context"),
                    dedup_key=make_dedup_key("OpenAI model story wrapper"),
                    raw_payload={"link": "https://news.google.com/rss/articles/demo?oc=5"},
                )
            )
            wrapped_article = next(
                article
                for article in repository.list_google_news_articles(limit=10)
                if article["source_id"] == "google-news"
            )
            repository.save_article_extraction(
                int(wrapped_article["id"]),
                extracted_text="A long extracted body from the wrapped article that should survive merge.",
            )
            service = NewsService(
                settings,
                repository=repository,
                source_registry=StubRegistry([]),
                google_news_resolver=resolver,
            )

            result = service.resolve_google_news_urls(limit=10)

            self.assertEqual(result["updated"], 0)
            self.assertEqual(result["merged"], 1)
            self.assertEqual(repository.count_articles(), 1)
            article = repository.list_articles(limit=10, include_hidden=True)[0]
            self.assertEqual(article["url"], "https://openai.com/index/new-model/")
            self.assertIn("wrapped article", article["extracted_text"])

    def test_enrich_articles_masks_internal_error_details(self) -> None:
        class FailingLLMClient(StubLLMClient):
            def enrich_article(self, article):
                raise RuntimeError("llm secret leaked: sk-test")

        with tempfile.TemporaryDirectory() as temp_dir:
            settings = Settings(
                database_path=Path(temp_dir) / "ainews.db",
                sources_file=Path(temp_dir) / "sources.json",
                llm_base_url="https://example.com/v1",
                llm_api_key="token",
                llm_model="stub-model",
            )
            repository = ArticleRepository(settings.database_path)
            now = utc_now()
            repository.insert_if_new(
                ArticleRecord(
                    source_id="openai-news",
                    source_name="OpenAI News",
                    title="OpenAI launches a new model",
                    url="https://example.com/openai-model",
                    canonical_url="https://example.com/openai-model",
                    summary="A release update",
                    published_at=now,
                    discovered_at=now,
                    language="en",
                    region="international",
                    country="US",
                    topic="company",
                    content_hash=make_content_hash(
                        "OpenAI launches a new model", "A release update"
                    ),
                    dedup_key=make_dedup_key("OpenAI launches a new model"),
                    raw_payload={},
                )
            )
            service = NewsService(
                settings,
                repository=repository,
                source_registry=StubRegistry([]),
                llm_client=FailingLLMClient(),
                content_extractor=StubExtractor(),
            )

            result = service.enrich_articles(limit=5)
            article = service.list_articles(limit=5)[0]

            self.assertEqual(result["articles"][0]["error"], PUBLIC_ERROR_MESSAGE)
            self.assertEqual(article["llm_error"], PUBLIC_ERROR_MESSAGE)
            self.assertNotIn("sk-test", json.dumps(result))

    def test_refresh_publications_masks_internal_error_details(self) -> None:
        class FailingRefreshPublisher(StubPublisher):
            def refresh_publication(self, publication):
                raise RuntimeError("wechat token leaked: abc123")

        with tempfile.TemporaryDirectory() as temp_dir:
            settings = Settings(
                database_path=Path(temp_dir) / "ainews.db",
                sources_file=Path(temp_dir) / "sources.json",
            )
            repository = ArticleRepository(settings.database_path)
            publication = repository.save_publication(
                digest_id=None,
                target="wechat",
                status="pending",
                external_id="PUBLISH123",
                message="wechat draft created and publish submitted",
                response_payload={"publish": {"publish_id": "PUBLISH123"}},
            )
            service = NewsService(
                settings,
                repository=repository,
                source_registry=StubRegistry([]),
                llm_client=StubLLMClient(),
                publisher=FailingRefreshPublisher(),
            )

            result = service.refresh_publications(
                publication_ids=[int(publication["id"])],
                target="wechat",
                only_pending=True,
            )
            refreshed = repository.get_publication(int(publication["id"]))

            self.assertEqual(result["publications"][0]["message"], PUBLIC_ERROR_MESSAGE)
            self.assertEqual(refreshed["message"], PUBLIC_ERROR_MESSAGE)
            self.assertEqual(
                refreshed["response_payload"]["status_query_error"]["message"],
                PUBLIC_ERROR_MESSAGE,
            )
            self.assertNotIn("abc123", json.dumps(result))

    def test_stats_include_operation_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = Settings(
                database_path=Path(temp_dir) / "ainews.db",
                sources_file=Path(temp_dir) / "sources.json",
            )
            repository = ArticleRepository(settings.database_path)
            service = NewsService(
                settings,
                repository=repository,
                source_registry=StubRegistry([]),
                llm_client=StubLLMClient(),
            )

            service.build_digest(region="all", since_hours=24, limit=10, use_llm=False, persist=False)
            stats = service.get_stats()

            self.assertIn("operations", stats)
            self.assertIn("digest", stats["operations"])
            self.assertIn("configured_publish_targets", stats)

    def test_get_operations_aggregates_runtime_context(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = Settings(
                database_path=Path(temp_dir) / "ainews.db",
                sources_file=Path(temp_dir) / "sources.json",
            )
            repository = ArticleRepository(settings.database_path)
            source = SourceDefinition(
                id="openai-news",
                name="OpenAI News",
                url="https://openai.com/news/rss",
                region="international",
                language="en",
                country="US",
                topic="company",
            )
            service = NewsService(
                settings,
                repository=repository,
                source_registry=StubRegistry([source]),
                llm_client=StubLLMClient(),
            )

            pipeline_token = service.telemetry.start("pipeline", context={"region": "all"})
            service.telemetry.finish(
                pipeline_token,
                status="partial_error",
                metrics={"published": 0},
                error_category="publication_error",
            )
            repository.upsert_source_state(
                source_id="openai-news",
                source_name="OpenAI News",
                cooldown_status="blocked",
                cooldown_until="2999-01-01T00:00:00+00:00",
                consecutive_failures=2,
                last_error_category="blocked",
                last_http_status=403,
                last_error="blocked by site",
                last_error_at=utc_now().isoformat(),
            )
            repository.record_source_event(
                source_id="openai-news",
                source_name="OpenAI News",
                event_type="extract",
                status="blocked",
                error_category="blocked",
                http_status=403,
                message="blocked extraction",
            )
            repository.record_source_alert(
                source_id="openai-news",
                source_name="OpenAI News",
                alert_key="source_cooldown:openai-news",
                alert_status="sent",
                severity="warning",
                title="source cooldown active: OpenAI News",
                message="OpenAI News entered blocked cooldown",
                fingerprint="blocked|2999-01-01T00:00:00+00:00|2|403",
                targets=[{"target": "telegram", "status": "ok"}],
            )
            repository.save_publication(
                digest_id=1,
                target="wechat",
                status="error",
                external_id="PUBLISH123",
                message="publish failed",
                response_payload={"status_query_error": {"message": PUBLIC_ERROR_MESSAGE}},
            )

            payload = service.get_operations()

            self.assertEqual(payload["health"]["status"], "degraded")
            self.assertEqual(payload["pipeline_runs"][0]["name"], "pipeline")
            self.assertEqual(payload["pipeline_runs"][0]["status"], "partial_error")
            self.assertEqual(payload["source_runtime"][0]["id"], "openai-news")
            self.assertEqual(payload["source_alerts"][0]["source_id"], "openai-news")
            self.assertEqual(payload["publication_failures"][0]["status"], "error")
            self.assertIn("publication_error", payload["failure_categories"])
            self.assertIn("pipeline", payload["operation_totals"])


if __name__ == "__main__":
    unittest.main()
