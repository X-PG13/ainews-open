import json
import tempfile
import unittest
from pathlib import Path

from ainews.config import Settings
from ainews.content_extractor import ExtractedContent
from ainews.models import ArticleEnrichment, ArticleRecord, DailyDigest, SourceDefinition
from ainews.publisher import PublicationResult
from ainews.repository import ArticleRepository
from ainews.service import PUBLIC_ERROR_MESSAGE, NewsService
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


class LeakyExtractor:
    def fetch_and_extract(self, url):
        raise RuntimeError("internal extractor path leaked: /srv/private")


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
                source_registry=StubRegistry([]),
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
            self.assertEqual(result["failure_categories"]["timeout"], 1)
            self.assertEqual(health["status"], "degraded")
            self.assertTrue(health["ready"])
            self.assertIn("article_extraction_errors", health["degraded_reasons"])
            self.assertIn("extract", health["operations"])

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


if __name__ == "__main__":
    unittest.main()
