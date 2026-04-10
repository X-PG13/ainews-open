import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ainews import __version__
from ainews.models import ArticleRecord
from ainews.repository import ArticleRepository
from ainews.utils import make_content_hash, make_dedup_key, utc_now

try:
    from fastapi.testclient import TestClient
except (ModuleNotFoundError, RuntimeError):  # pragma: no cover
    TestClient = None


@unittest.skipIf(TestClient is None, "fastapi test client is not installed")
class ApiTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._previous_env = {
            "AINEWS_HOME": os.environ.get("AINEWS_HOME"),
            "AINEWS_ADMIN_TOKEN": os.environ.get("AINEWS_ADMIN_TOKEN"),
        }
        self._temp_dir = tempfile.TemporaryDirectory()
        os.environ["AINEWS_HOME"] = self._temp_dir.name
        os.environ["AINEWS_ADMIN_TOKEN"] = "secret-token"

        from ainews.api import create_app

        self.client = TestClient(create_app())

    def tearDown(self) -> None:
        self._temp_dir.cleanup()
        for key, value in self._previous_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def _seed_article(
        self,
        *,
        title: str = "OpenAI launches a new model",
        url: str = "https://example.com/openai-model",
    ) -> None:
        repository = ArticleRepository(Path(self._temp_dir.name) / "data" / "ainews.db")
        published = utc_now()
        repository.insert_if_new(
            ArticleRecord(
                source_id="openai-news",
                source_name="OpenAI News",
                title=title,
                url=url,
                canonical_url=url,
                summary="A release update",
                published_at=published,
                discovered_at=published,
                language="en",
                region="international",
                country="US",
                topic="company",
                content_hash=make_content_hash(title, "A release update"),
                dedup_key=make_dedup_key(title),
                raw_payload={},
            )
        )

    def test_health_route(self) -> None:
        response = self.client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")
        self.assertTrue(response.json()["ready"])
        self.assertEqual(response.json()["version"], __version__)
        self.assertEqual(response.json()["checks"]["database"], "ok")
        self.assertEqual(response.json()["checks"]["sources"], "ok")
        self.assertGreaterEqual(response.json()["schema_version"], 1)
        self.assertIn("stats", response.json())
        self.assertTrue(response.headers["X-Request-ID"])

    def test_metrics_route_exposes_prometheus_counters(self) -> None:
        repository = ArticleRepository(Path(self._temp_dir.name) / "data" / "ainews.db")
        repository.record_source_event(
            source_id="venturebeat",
            source_name="VentureBeat",
            event_type="extract",
            status="blocked",
            error_category="blocked",
            http_status=403,
            message="blocked extraction",
        )
        repository.record_source_event(
            source_id="venturebeat",
            source_name="VentureBeat",
            event_type="cooldown",
            status="recovered",
            message="recovered",
        )
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
        repository.save_alert_state(
            alert_key="source_cooldown:venturebeat",
            is_active=True,
            fingerprint="blocked|2999-01-01T00:00:00+00:00",
            last_status="active",
            last_title="source cooldown active: VentureBeat",
            last_message="entered cooldown",
            sent_at=utc_now().isoformat(),
            increment_delivery=True,
        )

        response = self.client.get("/metrics")

        self.assertEqual(response.status_code, 200)
        self.assertIn("text/plain", response.headers["content-type"])
        body = response.text
        self.assertIn('ainews_pipeline_runs_total{status="ok"} 0', body)
        self.assertIn('ainews_extract_failures_total{category="blocked"} 1', body)
        self.assertIn("ainews_source_cooldowns_active 1", body)
        self.assertIn("ainews_source_recoveries_total 1", body)
        self.assertIn("ainews_alert_sends_total 1", body)

    def test_admin_route_requires_token(self) -> None:
        unauthorized = self.client.get("/admin/stats")
        authorized = self.client.get(
            "/admin/stats",
            headers={"X-Admin-Token": "secret-token"},
        )

        self.assertEqual(unauthorized.status_code, 401)
        self.assertEqual(authorized.status_code, 200)
        self.assertIn("total_articles", authorized.json())

    def test_admin_route_masks_invalid_token_detail(self) -> None:
        response = self.client.get(
            "/admin/stats",
            headers={"X-Admin-Token": "wrong-token"},
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(
            response.json()["detail"],
            "request could not be processed; inspect server logs with the response X-Request-ID",
        )

    def test_admin_route_masks_validation_error_detail(self) -> None:
        response = self.client.post(
            "/admin/extract/retry",
            headers={"X-Admin-Token": "secret-token"},
            json={"limit": 1000},
        )

        self.assertEqual(response.status_code, 422)
        self.assertEqual(
            response.json()["detail"],
            "request could not be processed; inspect server logs with the response X-Request-ID",
        )

    def test_admin_publish_skips_duplicate_digest_target(self) -> None:
        self._seed_article()

        first = self.client.post(
            "/admin/publish",
            headers={"X-Admin-Token": "secret-token"},
            json={"targets": ["static_site"], "use_llm": False, "persist": True},
        )
        self.assertEqual(first.status_code, 200)
        first_payload = first.json()
        digest_id = first_payload["digest"]["stored_digest"]["id"]

        second = self.client.post(
            "/admin/publish",
            headers={"X-Admin-Token": "secret-token"},
            json={"digest_id": digest_id, "targets": ["static_site"]},
        )

        self.assertEqual(second.status_code, 200)
        second_payload = second.json()
        self.assertEqual(second_payload["published"], 0)
        self.assertEqual(second_payload["skipped"], 1)
        self.assertEqual(second_payload["targets"][0]["status"], "skipped")
        self.assertEqual(second_payload["publication_records"], [])

    def test_admin_operations_returns_recent_runs(self) -> None:
        self._seed_article()
        self.client.post(
            "/admin/publish",
            headers={"X-Admin-Token": "secret-token"},
            json={"targets": ["static_site"], "use_llm": False, "persist": True},
        )

        response = self.client.get(
            "/admin/operations",
            headers={"X-Admin-Token": "secret-token"},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("operations", payload)
        self.assertIn("publish", payload["operations"])
        self.assertEqual(payload["operations"]["publish"]["status"], "ok")

    def test_admin_article_curation_can_set_must_include(self) -> None:
        self._seed_article()
        repository = ArticleRepository(Path(self._temp_dir.name) / "data" / "ainews.db")
        article_id = repository.list_articles(limit=10, include_hidden=True)[0]["id"]

        response = self.client.patch(
            f"/admin/articles/{article_id}",
            headers={"X-Admin-Token": "secret-token"},
            json={"must_include": True},
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["article"]["must_include"])

    def test_admin_can_promote_duplicate_primary(self) -> None:
        repository = ArticleRepository(Path(self._temp_dir.name) / "data" / "ainews.db")
        published = utc_now()
        repository.insert_if_new(
            ArticleRecord(
                source_id="openai-news",
                source_name="OpenAI News",
                title="OpenAI launches enterprise governance controls",
                url="https://openai.com/index/enterprise-governance",
                canonical_url="https://openai.com/index/enterprise-governance",
                summary="Direct release coverage.",
                published_at=published,
                discovered_at=published,
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
                published_at=published,
                discovered_at=published,
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
        yahoo_id = next(
            row["id"]
            for row in repository.list_articles(limit=10, include_hidden=True)
            if row["source_id"] == "yahoo-ai"
        )

        response = self.client.post(
            f"/admin/articles/{yahoo_id}/duplicate-primary",
            headers={"X-Admin-Token": "secret-token"},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()["article"]
        self.assertTrue(payload["is_duplicate_primary"])
        self.assertEqual(payload["source_id"], "yahoo-ai")

    def test_admin_operations_includes_runtime_summary_sections(self) -> None:
        repository = ArticleRepository(Path(self._temp_dir.name) / "data" / "ainews.db")
        repository.upsert_source_state(
            source_id="openai-news",
            source_name="OpenAI News",
            cooldown_status="blocked",
            cooldown_until="2999-01-01T00:00:00+00:00",
            consecutive_failures=2,
            last_error_category="blocked",
            last_http_status=403,
            last_error="blocked",
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
            response_payload={"status_query_error": {"message": "publish failed"}},
        )

        response = self.client.get(
            "/admin/operations",
            headers={"X-Admin-Token": "secret-token"},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("health", payload)
        self.assertIn("metrics", payload)
        self.assertIn("source_runtime", payload)
        self.assertIn("source_alerts", payload)
        self.assertIn("publication_failures", payload)
        self.assertEqual(payload["health"]["status"], "degraded")
        self.assertEqual(payload["source_runtime"][0]["id"], "openai-news")
        self.assertEqual(payload["source_alerts"][0]["source_id"], "openai-news")
        self.assertEqual(payload["publication_failures"][0]["status"], "error")

    def test_admin_extract_sanitizes_internal_error_message(self) -> None:
        with patch(
            "ainews.api.NewsService.extract_articles",
            return_value={
                "status": "partial_error",
                "errors": 1,
                "articles": [
                    {
                        "article_id": 1,
                        "status": "error",
                        "error": "database path leaked: /tmp/private.db",
                        "error_category": "unexpected",
                    }
                ],
            },
        ):
            response = self.client.post(
                "/admin/extract",
                headers={"X-Admin-Token": "secret-token"},
                json={"limit": 1},
            )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(
            payload["articles"][0]["error"],
            "operation failed; inspect server logs with the response X-Request-ID",
        )

    def test_admin_articles_supports_extraction_filters(self) -> None:
        self._seed_article(title="Throttled article", url="https://example.com/throttled")
        self._seed_article(title="Blocked article", url="https://example.com/blocked")
        repository = ArticleRepository(Path(self._temp_dir.name) / "data" / "ainews.db")
        rows = repository.list_articles(limit=10, include_hidden=True)
        throttled = next(row for row in rows if row["title"] == "Throttled article")
        blocked = next(row for row in rows if row["title"] == "Blocked article")
        repository.mark_article_extraction_failure(
            int(throttled["id"]),
            error="retry later",
            status="throttled",
            error_category="throttled",
            http_status=429,
            next_retry_at="2000-01-01T00:00:00+00:00",
        )
        repository.mark_article_extraction_failure(
            int(blocked["id"]),
            error="blocked",
            status="blocked",
            error_category="blocked",
            http_status=403,
            next_retry_at="2999-01-01T00:00:00+00:00",
        )

        response = self.client.get(
            "/admin/articles?extraction_status=throttled&due_only=true",
            headers={"X-Admin-Token": "secret-token"},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(len(payload["articles"]), 1)
        self.assertEqual(payload["articles"][0]["title"], "Throttled article")

    def test_admin_extract_retry_passes_filters(self) -> None:
        with patch(
            "ainews.api.NewsService.retry_extractions",
            return_value={"status": "ok", "requested": 1, "articles": []},
        ) as mock_retry:
            response = self.client.post(
                "/admin/extract/retry",
                headers={"X-Admin-Token": "secret-token"},
                json={
                    "extraction_status": "throttled",
                    "extraction_error_category": "throttled",
                    "due_only": True,
                    "limit": 5,
                },
            )

        self.assertEqual(response.status_code, 200)
        mock_retry.assert_called_once_with(
            source_ids=None,
            article_ids=None,
            since_hours=None,
            extraction_status="throttled",
            extraction_error_category="throttled",
            due_only=True,
            limit=5,
        )

    def test_admin_sources_includes_runtime_cooldown_state(self) -> None:
        self._seed_article(title="Blocked article", url="https://example.com/blocked-source")
        repository = ArticleRepository(Path(self._temp_dir.name) / "data" / "ainews.db")
        repository.upsert_source_state(
            source_id="openai-news",
            source_name="OpenAI News",
            cooldown_status="blocked",
            cooldown_until="2999-01-01T00:00:00+00:00",
            consecutive_failures=2,
            last_error_category="blocked",
            last_http_status=403,
            last_error="blocked",
            last_error_at=utc_now().isoformat(),
        )

        response = self.client.get(
            "/admin/sources",
            headers={"X-Admin-Token": "secret-token"},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        source = next(item for item in payload["sources"] if item["id"] == "openai-news")
        self.assertEqual(source["cooldown_status"], "blocked")
        self.assertTrue(source["cooldown_active"])

    def test_admin_sources_includes_runtime_summary_metrics(self) -> None:
        self._seed_article()
        repository = ArticleRepository(Path(self._temp_dir.name) / "data" / "ainews.db")
        repository.record_source_event(
            source_id="openai-news",
            source_name="OpenAI News",
            event_type="extract",
            status="ok",
            article_title="OpenAI launches a new model",
        )
        repository.record_source_event(
            source_id="openai-news",
            source_name="OpenAI News",
            event_type="extract",
            status="error",
            error_category="temporary_error",
            http_status=503,
            article_title="OpenAI launches a new model",
            message="temporary failure",
        )

        response = self.client.get(
            "/admin/sources",
            headers={"X-Admin-Token": "secret-token"},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        source = next(item for item in payload["sources"] if item["id"] == "openai-news")
        self.assertEqual(source["recent_success_rate"], 50)
        self.assertEqual(source["recent_failure_categories"]["temporary_error"], 1)
        self.assertEqual(len(source["recent_operations"]), 2)
        self.assertTrue(source["last_success_at"])
        self.assertTrue(source["last_error_at"])

    def test_admin_source_alerts_returns_recent_history(self) -> None:
        repository = ArticleRepository(Path(self._temp_dir.name) / "data" / "ainews.db")
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

        response = self.client.get(
            "/admin/source-alerts?limit=10",
            headers={"X-Admin-Token": "secret-token"},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(len(payload["source_alerts"]), 1)
        self.assertEqual(payload["source_alerts"][0]["source_id"], "openai-news")
        self.assertEqual(payload["source_alerts"][0]["alert_status"], "sent")
        self.assertEqual(payload["source_alerts"][0]["targets"], [{"target": "telegram", "status": "ok"}])

    def test_admin_reset_source_cooldowns_passes_filters(self) -> None:
        with patch(
            "ainews.api.NewsService.reset_source_cooldowns",
            return_value={"status": "ok", "cleared": 1, "sources": []},
        ) as mock_reset:
            response = self.client.post(
                "/admin/sources/cooldowns/reset",
                headers={"X-Admin-Token": "secret-token"},
                json={"source_ids": ["venturebeat"], "active_only": False},
            )

        self.assertEqual(response.status_code, 200)
        mock_reset.assert_called_once_with(
            source_ids=["venturebeat"],
            active_only=False,
        )

    def test_admin_source_control_routes_update_runtime_state(self) -> None:
        repository = ArticleRepository(Path(self._temp_dir.name) / "data" / "ainews.db")
        repository.upsert_source_state(
            source_id="openai-news",
            source_name="OpenAI News",
            cooldown_status="blocked",
            cooldown_until="2999-01-01T00:00:00+00:00",
            consecutive_failures=2,
            last_error_category="blocked",
            last_http_status=403,
            last_error="blocked",
            last_error_at=utc_now().isoformat(),
        )

        ack = self.client.post(
            "/admin/sources/acknowledge",
            headers={"X-Admin-Token": "secret-token"},
            json={"source_ids": ["openai-news"], "note": "known issue"},
        )
        snooze = self.client.post(
            "/admin/sources/snooze",
            headers={"X-Admin-Token": "secret-token"},
            json={"source_ids": ["openai-news"], "minutes": 60},
        )
        maintenance = self.client.post(
            "/admin/sources/maintenance",
            headers={"X-Admin-Token": "secret-token"},
            json={"source_ids": ["openai-news"], "enabled": True},
        )
        source = repository.get_source_state("openai-news")

        self.assertEqual(ack.status_code, 200)
        self.assertEqual(snooze.status_code, 200)
        self.assertEqual(maintenance.status_code, 200)
        self.assertEqual(source["ack_note"], "known issue")
        self.assertTrue(source["silenced_active"])
        self.assertTrue(source["maintenance_mode"])

    def test_admin_refresh_publications_sanitizes_nested_error_message(self) -> None:
        with patch(
            "ainews.api.NewsService.refresh_publications",
            return_value={
                "status": "partial_error",
                "errors": 1,
                "publications": [
                    {
                        "publication_id": 1,
                        "target": "wechat",
                        "status": "error",
                        "message": "token expired for tenant secret abc123",
                        "publication": {
                            "id": 1,
                            "target": "wechat",
                            "status": "error",
                            "message": "token expired for tenant secret abc123",
                            "response_payload": {
                                "status_query_error": {
                                    "message": "token expired for tenant secret abc123"
                                }
                            },
                        },
                    }
                ],
            },
        ):
            response = self.client.post(
                "/admin/publications/refresh",
                headers={"X-Admin-Token": "secret-token"},
                json={"limit": 1},
            )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(
            payload["publications"][0]["message"],
            "operation failed; inspect server logs with the response X-Request-ID",
        )
        self.assertEqual(
            payload["publications"][0]["publication"]["message"],
            "operation failed; inspect server logs with the response X-Request-ID",
        )
        self.assertEqual(
            payload["publications"][0]["publication"]["response_payload"]["status_query_error"][
                "message"
            ],
            "operation failed; inspect server logs with the response X-Request-ID",
        )

    def test_digest_daily_masks_internal_exception_details(self) -> None:
        with patch(
            "ainews.api.NewsService.build_digest",
            side_effect=RuntimeError("internal path leaked: /tmp/private.db"),
        ):
            response = self.client.get("/digest/daily")

        self.assertEqual(response.status_code, 500)
        self.assertEqual(
            response.json()["detail"],
            "operation failed; inspect server logs with the response X-Request-ID",
        )
        self.assertNotIn("/tmp/private.db", response.text)
        self.assertTrue(response.headers["X-Request-ID"])

    def test_admin_stats_masks_internal_exception_details(self) -> None:
        with patch(
            "ainews.api.NewsService.get_stats",
            side_effect=RuntimeError("stack secret: /srv/internal"),
        ):
            response = self.client.get(
                "/admin/stats",
                headers={"X-Admin-Token": "secret-token"},
            )

        self.assertEqual(response.status_code, 500)
        self.assertEqual(
            response.json()["detail"],
            "operation failed; inspect server logs with the response X-Request-ID",
        )
        self.assertNotIn("/srv/internal", response.text)

    def test_admin_ingest_masks_bad_request_details(self) -> None:
        with patch(
            "ainews.api.NewsService.ingest",
            side_effect=ValueError("upstream validation failed: token abc123"),
        ):
            response = self.client.post(
                "/admin/ingest",
                headers={"X-Admin-Token": "secret-token"},
                json={"source_ids": ["openai-news"]},
            )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()["detail"],
            "request could not be processed; inspect server logs with the response X-Request-ID",
        )
        self.assertNotIn("abc123", response.text)

    def test_admin_publish_masks_internal_exception_details(self) -> None:
        with patch(
            "ainews.api.NewsService.publish_digest",
            side_effect=RuntimeError("webhook secret leaked"),
        ):
            response = self.client.post(
                "/admin/publish",
                headers={"X-Admin-Token": "secret-token"},
                json={"targets": ["static_site"]},
            )

        self.assertEqual(response.status_code, 500)
        self.assertEqual(
            response.json()["detail"],
            "operation failed; inspect server logs with the response X-Request-ID",
        )
        self.assertNotIn("webhook secret leaked", response.text)
