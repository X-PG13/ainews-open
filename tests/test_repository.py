import sqlite3
import tempfile
import unittest
from pathlib import Path

from ainews.models import ArticleRecord, DailyDigest
from ainews.repository import CURRENT_SCHEMA_VERSION, ArticleRepository
from ainews.utils import make_content_hash, make_dedup_key, utc_now


class RepositoryTestCase(unittest.TestCase):
    def test_repository_deduplicates_by_title_and_content(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repository = ArticleRepository(Path(temp_dir) / "ainews.db")
            published = utc_now()

            first = ArticleRecord(
                source_id="a",
                source_name="Source A",
                title="AI startup raises new funding",
                url="https://example.com/a",
                canonical_url="https://example.com/a",
                summary="A short summary",
                published_at=published,
                discovered_at=published,
                language="en",
                region="international",
                country="US",
                topic="news",
                content_hash=make_content_hash("AI startup raises new funding", "A short summary"),
                dedup_key=make_dedup_key("AI startup raises new funding"),
                raw_payload={},
            )
            duplicate = ArticleRecord(
                source_id="b",
                source_name="Source B",
                title="AI startup raises new funding",
                url="https://another.example.com/story",
                canonical_url="https://another.example.com/story",
                summary="A short summary",
                published_at=published,
                discovered_at=published,
                language="en",
                region="international",
                country="US",
                topic="news",
                content_hash=make_content_hash("AI startup raises new funding", "A short summary"),
                dedup_key=make_dedup_key("AI startup raises new funding"),
                raw_payload={},
            )

            self.assertTrue(repository.insert_if_new(first))
            self.assertFalse(repository.insert_if_new(duplicate))
            self.assertEqual(repository.count_articles(), 1)

    def test_repository_updates_curation_and_stores_digest(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repository = ArticleRepository(Path(temp_dir) / "ainews.db")
            published = utc_now()
            article = ArticleRecord(
                source_id="a",
                source_name="Source A",
                title="AI startup raises new funding",
                url="https://example.com/a",
                canonical_url="https://example.com/a",
                summary="A short summary",
                published_at=published,
                discovered_at=published,
                language="en",
                region="international",
                country="US",
                topic="news",
                content_hash=make_content_hash("AI startup raises new funding", "A short summary"),
                dedup_key=make_dedup_key("AI startup raises new funding"),
                raw_payload={},
            )
            repository.insert_if_new(article)
            stored = repository.list_articles(limit=1, include_hidden=True)[0]

            curated = repository.update_article_curation(
                int(stored["id"]),
                is_pinned=True,
                editorial_note="keep on top",
            )
            self.assertTrue(curated["is_pinned"])
            self.assertEqual(curated["editorial_note"], "keep on top")

            digest = repository.save_digest(
                region="all",
                since_hours=24,
                digest=DailyDigest(
                    title="AI 新闻日报",
                    overview="overview",
                    highlights=["item"],
                    sections=[{"title": "国际动态", "items": ["bullet"]}],
                    closing="done",
                ),
                body_markdown="# AI 新闻日报",
                article_count=1,
                source_count=1,
            )
            self.assertEqual(digest["title"], "AI 新闻日报")
            self.assertEqual(repository.get_stats()["total_digests"], 1)

    def test_repository_updates_and_filters_publications(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repository = ArticleRepository(Path(temp_dir) / "ainews.db")

            first = repository.save_publication(
                digest_id=1,
                target="wechat",
                status="pending",
                external_id="PUBLISH123",
                message="pending",
                response_payload={"publish": {"publish_id": "PUBLISH123"}},
            )
            repository.save_publication(
                digest_id=1,
                target="static_site",
                status="ok",
                external_id="site:index",
                message="done",
                response_payload={"base_url": "https://example.com/site"},
            )

            updated = repository.update_publication(
                int(first["id"]),
                status="ok",
                message="wechat publish succeeded",
                response_payload={"status_query": {"publish_status": 0}},
            )

            self.assertEqual(updated["status"], "ok")
            self.assertTrue(updated["updated_at"])
            filtered = repository.list_publications(
                digest_id=1, target="wechat", status="ok", limit=10
            )
            self.assertEqual(len(filtered), 1)
            self.assertEqual(filtered[0]["external_id"], "PUBLISH123")
            stats = repository.get_stats()
            self.assertEqual(stats["publication_status_counts"]["ok"], 2)
            self.assertEqual(stats["pending_publications"], 0)

    def test_repository_skipped_extraction_is_not_requeued_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repository = ArticleRepository(Path(temp_dir) / "ainews.db")
            published = utc_now()
            article = ArticleRecord(
                source_id="google-news-global-ai",
                source_name="Google News Global AI",
                title="Anthropic security story",
                url="https://news.google.com/rss/articles/demo?oc=5",
                canonical_url="https://news.google.com/rss/articles/demo?oc=5",
                summary="A short summary",
                published_at=published,
                discovered_at=published,
                language="en",
                region="international",
                country="US",
                topic="news",
                content_hash=make_content_hash("Anthropic security story", "A short summary"),
                dedup_key=make_dedup_key("Anthropic security story"),
                raw_payload={},
            )
            repository.insert_if_new(article)
            stored = repository.list_articles(limit=1, include_hidden=True)[0]

            updated = repository.mark_article_extraction_skipped(
                int(stored["id"]),
                error="skipped aggregated Google News shell page; direct article URL required",
            )

            self.assertEqual(updated["extraction_status"], "skipped")
            queued = repository.list_articles_for_extraction(limit=10, force=False)
            self.assertEqual(queued, [])
            forced = repository.list_articles_for_extraction(limit=10, force=True)
            self.assertEqual(len(forced), 1)
            self.assertEqual(repository.get_stats()["skipped_extractions"], 1)

    def test_repository_filters_articles_by_extraction_status_category_and_due_window(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repository = ArticleRepository(Path(temp_dir) / "ainews.db")
            published = utc_now()

            throttled = ArticleRecord(
                source_id="venturebeat",
                source_name="VentureBeat",
                title="Throttled article",
                url="https://venturebeat.com/ai/throttled",
                canonical_url="https://venturebeat.com/ai/throttled",
                summary="Retry later",
                published_at=published,
                discovered_at=published,
                language="en",
                region="international",
                country="US",
                topic="news",
                content_hash=make_content_hash("Throttled article", "Retry later"),
                dedup_key=make_dedup_key("Throttled article"),
                raw_payload={},
            )
            blocked = ArticleRecord(
                source_id="theverge",
                source_name="The Verge",
                title="Blocked article",
                url="https://www.theverge.com/ai/blocked",
                canonical_url="https://www.theverge.com/ai/blocked",
                summary="Blocked by challenge",
                published_at=published,
                discovered_at=published,
                language="en",
                region="international",
                country="US",
                topic="news",
                content_hash=make_content_hash("Blocked article", "Blocked by challenge"),
                dedup_key=make_dedup_key("Blocked article"),
                raw_payload={},
            )
            repository.insert_if_new(throttled)
            repository.insert_if_new(blocked)
            rows = repository.list_articles(limit=10, include_hidden=True)
            throttled_row = next(row for row in rows if row["title"] == "Throttled article")
            blocked_row = next(row for row in rows if row["title"] == "Blocked article")

            repository.mark_article_extraction_failure(
                int(throttled_row["id"]),
                error="retry later",
                status="throttled",
                error_category="throttled",
                http_status=429,
                next_retry_at="2000-01-01T00:00:00+00:00",
            )
            repository.mark_article_extraction_failure(
                int(blocked_row["id"]),
                error="blocked",
                status="blocked",
                error_category="blocked",
                http_status=403,
                next_retry_at="2999-01-01T00:00:00+00:00",
            )

            filtered = repository.list_articles(
                extraction_status="throttled",
                extraction_error_category="throttled",
                due_only=True,
                limit=10,
                include_hidden=True,
            )
            self.assertEqual([item["title"] for item in filtered], ["Throttled article"])

            queued = repository.list_articles_for_extraction(
                extraction_status="blocked",
                due_only=True,
                force=True,
                limit=10,
            )
            self.assertEqual(queued, [])

    def test_repository_excludes_articles_from_active_source_cooldowns(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repository = ArticleRepository(Path(temp_dir) / "ainews.db")
            published = utc_now()
            article = ArticleRecord(
                source_id="venturebeat",
                source_name="VentureBeat",
                title="Cooldown article",
                url="https://venturebeat.com/ai/cooldown",
                canonical_url="https://venturebeat.com/ai/cooldown",
                summary="Cooling down",
                published_at=published,
                discovered_at=published,
                language="en",
                region="international",
                country="US",
                topic="news",
                content_hash=make_content_hash("Cooldown article", "Cooling down"),
                dedup_key=make_dedup_key("Cooldown article"),
                raw_payload={},
            )
            repository.insert_if_new(article)
            repository.upsert_source_state(
                source_id="venturebeat",
                source_name="VentureBeat",
                cooldown_status="blocked",
                cooldown_until="2999-01-01T00:00:00+00:00",
                consecutive_failures=2,
                last_error_category="blocked",
                last_http_status=403,
                last_error="blocked",
                last_error_at=utc_now().isoformat(),
            )

            queued = repository.list_articles_for_extraction(limit=10, force=False)
            source_states = repository.list_source_states(active_only=True, limit=10)

            self.assertEqual(queued, [])
            self.assertEqual(len(source_states), 1)
            self.assertEqual(source_states[0]["source_id"], "venturebeat")
            self.assertTrue(source_states[0]["cooldown_active"])

    def test_repository_can_reset_source_cooldowns(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repository = ArticleRepository(Path(temp_dir) / "ainews.db")
            repository.upsert_source_state(
                source_id="venturebeat",
                source_name="VentureBeat",
                cooldown_status="throttled",
                cooldown_until="2999-01-01T00:00:00+00:00",
                consecutive_failures=3,
                last_error_category="throttled",
                last_http_status=429,
                last_error="retry later",
                last_error_at=utc_now().isoformat(),
            )

            cleared = repository.reset_source_cooldowns(source_ids=["venturebeat"], active_only=False)
            state = repository.get_source_state("venturebeat")

            self.assertEqual(len(cleared), 1)
            self.assertEqual(state["cooldown_status"], "")
            self.assertEqual(state["cooldown_until"], "")
            self.assertEqual(state["consecutive_failures"], 0)

    def test_repository_updates_url_even_when_canonical_url_conflicts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repository = ArticleRepository(Path(temp_dir) / "ainews.db")
            published = utc_now()
            direct = ArticleRecord(
                source_id="direct",
                source_name="Direct Source",
                title="Direct article",
                url="https://techcrunch.com/2026/04/07/arcee/",
                canonical_url="https://techcrunch.com/2026/04/07/arcee/",
                summary="A short summary",
                published_at=published,
                discovered_at=published,
                language="en",
                region="international",
                country="US",
                topic="news",
                content_hash=make_content_hash("Direct article", "A short summary"),
                dedup_key=make_dedup_key("Direct article"),
                raw_payload={},
            )
            wrapped = ArticleRecord(
                source_id="google-news",
                source_name="Google News",
                title="Wrapped article",
                url="https://news.google.com/rss/articles/demo?oc=5",
                canonical_url="https://news.google.com/rss/articles/demo?oc=5",
                summary="Another short summary",
                published_at=published,
                discovered_at=published,
                language="en",
                region="international",
                country="US",
                topic="news",
                content_hash=make_content_hash("Wrapped article", "Another short summary"),
                dedup_key=make_dedup_key("Wrapped article"),
                raw_payload={},
            )
            repository.insert_if_new(direct)
            repository.insert_if_new(wrapped)
            wrapped_row = next(
                row
                for row in repository.list_articles(limit=10, include_hidden=True)
                if row["source_id"] == "google-news"
            )

            updated = repository.update_article_urls(
                int(wrapped_row["id"]),
                url="https://techcrunch.com/2026/04/07/arcee/",
                canonical_url="https://techcrunch.com/2026/04/07/arcee/",
            )

            self.assertEqual(updated["url"], "https://techcrunch.com/2026/04/07/arcee/")
            self.assertEqual(updated["canonical_url"], "https://news.google.com/rss/articles/demo?oc=5")

    def test_repository_resolve_article_urls_merges_conflicting_google_news_duplicate(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repository = ArticleRepository(Path(temp_dir) / "ainews.db")
            published = utc_now()
            direct = ArticleRecord(
                source_id="direct",
                source_name="Direct Source",
                title="Direct article",
                url="https://techcrunch.com/2026/04/07/arcee/",
                canonical_url="https://techcrunch.com/2026/04/07/arcee",
                summary="Short direct summary",
                published_at=published,
                discovered_at=published,
                language="en",
                region="international",
                country="US",
                topic="news",
                content_hash=make_content_hash("Direct article", "Short direct summary"),
                dedup_key=make_dedup_key("Direct article"),
                raw_payload={"link": "https://techcrunch.com/2026/04/07/arcee/"},
            )
            wrapped = ArticleRecord(
                source_id="google-news",
                source_name="Google News",
                title="Wrapped article",
                url="https://news.google.com/rss/articles/demo?oc=5",
                canonical_url="https://news.google.com/rss/articles/demo?oc=5",
                summary="Longer wrapped summary with more detail",
                published_at=published,
                discovered_at=published,
                language="en",
                region="international",
                country="US",
                topic="news",
                content_hash=make_content_hash("Wrapped article", "Longer wrapped summary with more detail"),
                dedup_key=make_dedup_key("Wrapped article"),
                raw_payload={"link": "https://news.google.com/rss/articles/demo?oc=5"},
            )
            repository.insert_if_new(direct)
            repository.insert_if_new(wrapped)
            wrapped_row = next(
                row
                for row in repository.list_articles(limit=10, include_hidden=True)
                if row["source_id"] == "google-news"
            )
            repository.save_article_extraction(
                int(wrapped_row["id"]),
                extracted_text="Wrapped article extraction body survives the merge.",
            )

            merged = repository.resolve_article_urls(
                int(wrapped_row["id"]),
                url="https://techcrunch.com/2026/04/07/arcee/",
                canonical_url="https://techcrunch.com/2026/04/07/arcee/",
            )

            self.assertEqual(merged["action"], "merged")
            self.assertEqual(repository.count_articles(), 1)
            stored = repository.list_articles(limit=10, include_hidden=True)[0]
            self.assertEqual(stored["url"], "https://techcrunch.com/2026/04/07/arcee/")
            self.assertEqual(stored["canonical_url"], "https://techcrunch.com/2026/04/07/arcee")
            self.assertEqual(stored["summary"], "Longer wrapped summary with more detail")
            self.assertIn("survives the merge", stored["extracted_text"])

    def test_repository_migrates_legacy_schema_and_sets_version(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database_path = Path(temp_dir) / "ainews.db"
            connection = sqlite3.connect(str(database_path))
            connection.executescript(
                """
                CREATE TABLE articles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_id TEXT NOT NULL,
                    source_name TEXT NOT NULL,
                    title TEXT NOT NULL,
                    url TEXT NOT NULL,
                    canonical_url TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    published_at TEXT NOT NULL,
                    discovered_at TEXT NOT NULL,
                    language TEXT NOT NULL,
                    region TEXT NOT NULL,
                    country TEXT NOT NULL,
                    topic TEXT NOT NULL,
                    content_hash TEXT NOT NULL,
                    dedup_key TEXT NOT NULL,
                    raw_payload TEXT NOT NULL
                );

                CREATE TABLE digests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    region TEXT NOT NULL,
                    since_hours INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    body_markdown TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    model TEXT NOT NULL,
                    article_count INTEGER NOT NULL,
                    source_count INTEGER NOT NULL,
                    generated_at TEXT NOT NULL,
                    payload TEXT NOT NULL
                );

                CREATE TABLE publications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    digest_id INTEGER,
                    target TEXT NOT NULL,
                    status TEXT NOT NULL,
                    external_id TEXT NOT NULL,
                    message TEXT NOT NULL,
                    response_payload TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                """
            )
            connection.commit()
            connection.close()

            repository = ArticleRepository(database_path)

            self.assertEqual(repository.get_schema_version(), CURRENT_SCHEMA_VERSION)
            stats = repository.get_stats()
            self.assertEqual(stats["schema_version"], CURRENT_SCHEMA_VERSION)
            article = repository.list_articles(limit=1, include_hidden=True)
            self.assertEqual(article, [])


if __name__ == "__main__":
    unittest.main()
