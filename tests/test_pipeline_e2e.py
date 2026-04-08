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


class PipelineE2ETestCase(unittest.TestCase):
    def test_pipeline_runs_from_feed_fixture_to_static_publish(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
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


if __name__ == "__main__":
    unittest.main()
