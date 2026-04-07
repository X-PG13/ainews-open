import os
import tempfile
import unittest

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

    def test_health_route(self) -> None:
        response = self.client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

    def test_admin_route_requires_token(self) -> None:
        unauthorized = self.client.get("/admin/stats")
        authorized = self.client.get(
            "/admin/stats",
            headers={"X-Admin-Token": "secret-token"},
        )

        self.assertEqual(unauthorized.status_code, 401)
        self.assertEqual(authorized.status_code, 200)
        self.assertIn("total_articles", authorized.json())
