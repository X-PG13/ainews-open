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

    def _seed_article(self) -> None:
        repository = ArticleRepository(Path(self._temp_dir.name) / "data" / "ainews.db")
        published = utc_now()
        repository.insert_if_new(
            ArticleRecord(
                source_id="openai-news",
                source_name="OpenAI News",
                title="OpenAI launches a new model",
                url="https://example.com/openai-model",
                canonical_url="https://example.com/openai-model",
                summary="A release update",
                published_at=published,
                discovered_at=published,
                language="en",
                region="international",
                country="US",
                topic="company",
                content_hash=make_content_hash("OpenAI launches a new model", "A release update"),
                dedup_key=make_dedup_key("OpenAI launches a new model"),
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

    def test_admin_route_requires_token(self) -> None:
        unauthorized = self.client.get("/admin/stats")
        authorized = self.client.get(
            "/admin/stats",
            headers={"X-Admin-Token": "secret-token"},
        )

        self.assertEqual(unauthorized.status_code, 401)
        self.assertEqual(authorized.status_code, 200)
        self.assertIn("total_articles", authorized.json())

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
