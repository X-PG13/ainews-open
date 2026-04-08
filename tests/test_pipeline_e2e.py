import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ainews.config import Settings
from ainews.content_extractor import ArticleContentExtractor
from ainews.models import ArticleEnrichment, DailyDigest, SourceDefinition
from ainews.repository import ArticleRepository
from ainews.service import NewsService
from ainews.source_registry import SourceRegistry

FIXTURE_ROOT = Path(__file__).parent / "fixtures"


class FixtureRegistry(SourceRegistry):
    def __init__(self, sources):
        self._sources = sources

    def list_sources(self, *, enabled_only=True, source_ids=None):
        if not source_ids:
            return self._sources
        return [source for source in self._sources if source.id in set(source_ids)]


class StubLLMClient:
    def is_configured(self):
        return True

    def enrich_article(self, article):
        return ArticleEnrichment(
            title_zh=f"中文：{article['title']}",
            summary_zh="这是自动翻译后的摘要。",
            importance_zh="这条新闻对企业部署很重要。",
            provider="stub",
            model="stub-model",
        )

    def generate_digest(self, article_briefs, *, region, since_hours):
        return DailyDigest(
            title="中文 AI 日报",
            overview=f"最近 {since_hours} 小时的 AI 新闻。",
            highlights=[brief["display_title_zh"] for brief in article_briefs[:2]],
            sections=[
                {
                    "title": "国际动态",
                    "items": [brief["display_summary_zh"] for brief in article_briefs[:2]],
                }
            ],
            closing="完。",
            provider="stub",
            model="stub-model",
        )


class StubGoogleNewsResolver:
    def __init__(self, mapping):
        self.mapping = dict(mapping)

    def resolve(self, url):
        return self.mapping[url]


class PipelineE2ETestCase(unittest.TestCase):
    def _make_settings(self, temp_dir: str) -> Settings:
        settings = Settings(
            database_path=Path(temp_dir) / "ainews.db",
            sources_file=Path(temp_dir) / "sources.json",
            output_dir=Path(temp_dir) / "output",
            static_site_dir=Path(temp_dir) / "site",
            llm_base_url="https://example.com/v1",
            llm_api_key="token",
            llm_model="stub-model",
        )
        settings.output_dir.mkdir(parents=True, exist_ok=True)
        settings.static_site_dir.mkdir(parents=True, exist_ok=True)
        return settings

    def test_pipeline_runs_from_feed_fixture_to_static_publish(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = self._make_settings(temp_dir)

            source = SourceDefinition(
                id="openai-news",
                name="OpenAI News",
                url="https://example.com/feed/openai.xml",
                region="international",
                language="en",
                country="US",
                topic="company",
            )
            repository = ArticleRepository(settings.database_path)
            extractor = ArticleContentExtractor(
                timeout=10,
                user_agent="test-agent",
                text_limit=5000,
            )
            service = NewsService(
                settings,
                repository=repository,
                source_registry=FixtureRegistry([source]),
                llm_client=StubLLMClient(),
                content_extractor=extractor,
            )

            feed_xml = (FIXTURE_ROOT / "feed" / "openai.xml").read_text(encoding="utf-8")
            article_html = (
                FIXTURE_ROOT / "extraction" / "openai-article.html"
            ).read_text(encoding="utf-8")

            def fake_service_fetch(url, **kwargs):
                if url == source.url:
                    return feed_xml
                raise AssertionError(f"unexpected service fetch url: {url}")

            def fake_extractor_fetch(url, **kwargs):
                if url.startswith("https://example.com/news/openai-enterprise"):
                    return article_html
                raise AssertionError(f"unexpected extractor fetch url: {url}")

            with patch("ainews.service.fetch_text", side_effect=fake_service_fetch), patch(
                "ainews.content_extractor.fetch_text", side_effect=fake_extractor_fetch
            ):
                result = service.run_pipeline(
                    region="all",
                    since_hours=72,
                    limit=5,
                    use_llm=True,
                    persist=True,
                    export=False,
                    publish=True,
                    publish_targets=["static_site"],
                )

            self.assertEqual(result["status"], "ok")
            self.assertEqual(result["ingest"]["inserted_total"], 1)
            self.assertEqual(result["extract"]["updated"], 1)
            self.assertEqual(result["enrich"]["updated"], 1)
            self.assertEqual(result["digest"]["generation_mode"], "llm")
            self.assertEqual(result["publish"]["published"], 1)
            self.assertTrue(result["publish"]["publication_records"])

    def test_pipeline_resolves_google_news_wrapper_before_extract(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = self._make_settings(temp_dir)

            source = SourceDefinition(
                id="google-news-global-ai",
                name="Google News Global AI",
                url="https://example.com/feed/google-news-openai.xml",
                region="international",
                language="en",
                country="US",
                topic="news",
            )
            repository = ArticleRepository(settings.database_path)
            extractor = ArticleContentExtractor(
                timeout=10,
                user_agent="test-agent",
                text_limit=5000,
            )
            service = NewsService(
                settings,
                repository=repository,
                source_registry=FixtureRegistry([source]),
                llm_client=StubLLMClient(),
                content_extractor=extractor,
                google_news_resolver=StubGoogleNewsResolver(
                    {
                        "https://news.google.com/rss/articles/demo-openai?oc=5": "https://example.com/news/openai-enterprise?utm_source=google-news",
                    }
                ),
            )

            feed_xml = (
                FIXTURE_ROOT / "feed" / "google-news-openai.xml"
            ).read_text(encoding="utf-8")
            article_html = (
                FIXTURE_ROOT / "extraction" / "openai-article.html"
            ).read_text(encoding="utf-8")

            def fake_service_fetch(url, **kwargs):
                if url == source.url:
                    return feed_xml
                raise AssertionError(f"unexpected service fetch url: {url}")

            def fake_extractor_fetch(url, **kwargs):
                if url.startswith("https://example.com/news/openai-enterprise"):
                    return article_html
                raise AssertionError(f"unexpected extractor fetch url: {url}")

            with patch("ainews.service.fetch_text", side_effect=fake_service_fetch), patch(
                "ainews.content_extractor.fetch_text", side_effect=fake_extractor_fetch
            ):
                result = service.run_pipeline(
                    region="all",
                    since_hours=72,
                    limit=5,
                    use_llm=True,
                    persist=True,
                    export=True,
                    publish=False,
                )

            article = repository.list_articles(limit=10, include_hidden=True)[0]
            self.assertEqual(result["status"], "ok")
            self.assertEqual(result["ingest"]["resolved_total"], 1)
            self.assertEqual(article["url"], "https://example.com/news/openai-enterprise?utm_source=google-news")
            self.assertEqual(article["canonical_url"], "https://example.com/news/openai-enterprise")
            self.assertEqual(result["extract"]["updated"], 1)
            self.assertEqual(result["enrich"]["updated"], 1)

    def test_pipeline_runs_from_multi_source_feed_fixtures(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = self._make_settings(temp_dir)

            sources = [
                SourceDefinition(
                    id="jiqizhixin-ai",
                    name="机器之心",
                    url="https://example.com/feed/jiqizhixin.xml",
                    region="domestic",
                    language="zh",
                    country="CN",
                    topic="news",
                ),
                SourceDefinition(
                    id="ars-ai",
                    name="Ars Technica AI",
                    url="https://example.com/feed/arstechnica.xml",
                    region="international",
                    language="en",
                    country="US",
                    topic="news",
                ),
                SourceDefinition(
                    id="latent-ops",
                    name="Latent Ops",
                    url="https://example.com/feed/substack.xml",
                    region="international",
                    language="en",
                    country="US",
                    topic="blog",
                ),
                SourceDefinition(
                    id="yahoo-finance-ai",
                    name="Yahoo Finance AI",
                    url="https://example.com/feed/yahoo.xml",
                    region="international",
                    language="en",
                    country="US",
                    topic="news",
                ),
            ]
            repository = ArticleRepository(settings.database_path)
            service = NewsService(
                settings,
                repository=repository,
                source_registry=FixtureRegistry(sources),
                llm_client=StubLLMClient(),
                content_extractor=ArticleContentExtractor(
                    timeout=10,
                    user_agent="test-agent",
                    text_limit=5000,
                ),
            )

            feed_map = {
                sources[0].url: (FIXTURE_ROOT / "feed" / "jiqizhixin.xml").read_text(encoding="utf-8"),
                sources[1].url: (FIXTURE_ROOT / "feed" / "arstechnica.xml").read_text(encoding="utf-8"),
                sources[2].url: (FIXTURE_ROOT / "feed" / "substack.xml").read_text(encoding="utf-8"),
                sources[3].url: (FIXTURE_ROOT / "feed" / "yahoo.xml").read_text(encoding="utf-8"),
            }
            article_map = {
                "https://www.jiqizhixin.com/articles/2026-04-09-ops-stack?utm_source=rss": (
                    FIXTURE_ROOT / "extraction" / "jiqizhixin.html"
                ).read_text(encoding="utf-8"),
                "https://arstechnica.com/ai/2026/04/why-ai-teams-are-rebuilding-their-observability-stacks/?utm_source=rss": (
                    FIXTURE_ROOT / "extraction" / "arstechnica-article.html"
                ).read_text(encoding="utf-8"),
                "https://latentops.substack.com/p/managed-ai-operations?utm_medium=rss": (
                    FIXTURE_ROOT / "extraction" / "substack-article.html"
                ).read_text(encoding="utf-8"),
                "https://finance.yahoo.com/news/ai-deployment-discipline-board-level-topic-090000123.html?guccounter=1": (
                    FIXTURE_ROOT / "extraction" / "yahoo-syndication.html"
                ).read_text(encoding="utf-8"),
            }

            def fake_service_fetch(url, **kwargs):
                if url in feed_map:
                    return feed_map[url]
                raise AssertionError(f"unexpected service fetch url: {url}")

            def fake_extractor_fetch(url, **kwargs):
                if url in article_map:
                    return article_map[url]
                raise AssertionError(f"unexpected extractor fetch url: {url}")

            with patch("ainews.service.fetch_text", side_effect=fake_service_fetch), patch(
                "ainews.content_extractor.fetch_text", side_effect=fake_extractor_fetch
            ):
                result = service.run_pipeline(
                    region="all",
                    since_hours=72,
                    limit=10,
                    use_llm=True,
                    persist=True,
                    export=False,
                    publish=True,
                    publish_targets=["static_site"],
                )

            articles = repository.list_articles(limit=10, include_hidden=True)
            self.assertEqual(result["status"], "ok")
            self.assertEqual(result["ingest"]["inserted_total"], 4)
            self.assertEqual(result["extract"]["updated"], 4)
            self.assertEqual(result["enrich"]["updated"], 3)
            self.assertEqual(result["digest"]["total_articles"], 4)
            self.assertEqual(result["publish"]["published"], 1)
            self.assertEqual({article["source_id"] for article in articles}, {source.id for source in sources})

    def test_pipeline_reports_partial_error_for_multi_source_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = self._make_settings(temp_dir)

            sources = [
                SourceDefinition(
                    id="jiqizhixin-ai",
                    name="机器之心",
                    url="https://example.com/feed/jiqizhixin.xml",
                    region="domestic",
                    language="zh",
                    country="CN",
                    topic="news",
                ),
                SourceDefinition(
                    id="ars-ai",
                    name="Ars Technica AI",
                    url="https://example.com/feed/arstechnica.xml",
                    region="international",
                    language="en",
                    country="US",
                    topic="news",
                ),
            ]
            repository = ArticleRepository(settings.database_path)
            service = NewsService(
                settings,
                repository=repository,
                source_registry=FixtureRegistry(sources),
                llm_client=StubLLMClient(),
                content_extractor=ArticleContentExtractor(
                    timeout=10,
                    user_agent="test-agent",
                    text_limit=5000,
                ),
            )

            feed_map = {
                sources[0].url: (FIXTURE_ROOT / "feed" / "jiqizhixin.xml").read_text(encoding="utf-8"),
                sources[1].url: (FIXTURE_ROOT / "feed" / "arstechnica.xml").read_text(encoding="utf-8"),
            }
            article_map = {
                "https://www.jiqizhixin.com/articles/2026-04-09-ops-stack?utm_source=rss": (
                    FIXTURE_ROOT / "extraction" / "jiqizhixin.html"
                ).read_text(encoding="utf-8"),
            }

            def fake_service_fetch(url, **kwargs):
                if url in feed_map:
                    return feed_map[url]
                raise AssertionError(f"unexpected service fetch url: {url}")

            def fake_extractor_fetch(url, **kwargs):
                if url in article_map:
                    return article_map[url]
                if url == "https://arstechnica.com/ai/2026/04/why-ai-teams-are-rebuilding-their-observability-stacks/?utm_source=rss":
                    raise TimeoutError("fixture timeout")
                raise AssertionError(f"unexpected extractor fetch url: {url}")

            with patch("ainews.service.fetch_text", side_effect=fake_service_fetch), patch(
                "ainews.content_extractor.fetch_text", side_effect=fake_extractor_fetch
            ):
                result = service.run_pipeline(
                    region="all",
                    since_hours=72,
                    limit=10,
                    use_llm=True,
                    persist=True,
                    export=False,
                    publish=False,
                )

            articles = repository.list_articles(limit=10, include_hidden=True)
            failed_article = next(article for article in articles if article["source_id"] == "ars-ai")
            successful_article = next(article for article in articles if article["source_id"] == "jiqizhixin-ai")

            self.assertEqual(result["status"], "partial_error")
            self.assertEqual(result["extract"]["status"], "partial_error")
            self.assertEqual(result["extract"]["updated"], 1)
            self.assertEqual(result["extract"]["errors"], 1)
            self.assertEqual(result["failure_categories"], {"temporary_error": 1})
            self.assertEqual(failed_article["extraction_status"], "temporary_error")
            self.assertEqual(failed_article["extraction_error_category"], "temporary_error")
            self.assertTrue(successful_article["extracted_text"])


if __name__ == "__main__":
    unittest.main()
