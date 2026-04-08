import io
import sys
import types
import unittest
from unittest.mock import MagicMock, patch

from ainews.cli import main


class CliTestCase(unittest.TestCase):
    @patch("ainews.cli.configure_logging")
    @patch("ainews.cli.NewsService")
    @patch("ainews.cli.load_settings")
    def test_stats_command(self, mock_load_settings, mock_service_class, mock_configure_logging) -> None:
        mock_load_settings.return_value = MagicMock()
        service = mock_service_class.return_value
        service.get_stats.return_value = {"total_articles": 1}
        stdout = io.StringIO()

        with patch("sys.stdout", stdout):
            exit_code = main(["stats"])

        self.assertEqual(exit_code, 0)
        mock_configure_logging.assert_called_once()
        service.get_stats.assert_called_once()
        self.assertIn('"total_articles": 1', stdout.getvalue())

    @patch("ainews.cli.configure_logging")
    @patch("ainews.cli.NewsService")
    @patch("ainews.cli.load_settings")
    def test_run_pipeline_command_passes_force_republish(
        self,
        mock_load_settings,
        mock_service_class,
        mock_configure_logging,
    ) -> None:
        mock_load_settings.return_value = MagicMock()
        service = mock_service_class.return_value
        service.run_pipeline.return_value = {"status": "ok"}
        stdout = io.StringIO()

        with patch("sys.stdout", stdout):
            exit_code = main(
                [
                    "run-pipeline",
                    "--publish",
                    "--target",
                    "static_site",
                    "--force-republish",
                ]
            )

        self.assertEqual(exit_code, 0)
        service.run_pipeline.assert_called_once()
        self.assertTrue(service.run_pipeline.call_args.kwargs["force_republish"])
        self.assertEqual(service.run_pipeline.call_args.kwargs["publish_targets"], ["static_site"])

    @patch("ainews.cli.configure_logging")
    @patch("ainews.cli.NewsService")
    @patch("ainews.cli.load_settings")
    def test_serve_command_invokes_uvicorn(
        self,
        mock_load_settings,
        mock_service_class,
        mock_configure_logging,
    ) -> None:
        mock_load_settings.return_value = MagicMock()
        fake_uvicorn = types.SimpleNamespace(run=MagicMock())

        with patch.dict(sys.modules, {"uvicorn": fake_uvicorn}):
            exit_code = main(["serve", "--host", "127.0.0.1", "--port", "9000"])

        self.assertEqual(exit_code, 0)
        fake_uvicorn.run.assert_called_once_with(
            "ainews.api:create_app",
            factory=True,
            host="127.0.0.1",
            port=9000,
            reload=False,
        )

    @patch("ainews.cli.configure_logging")
    @patch("ainews.cli.NewsService")
    @patch("ainews.cli.load_settings")
    def test_resolve_google_news_command(
        self,
        mock_load_settings,
        mock_service_class,
        mock_configure_logging,
    ) -> None:
        mock_load_settings.return_value = MagicMock()
        service = mock_service_class.return_value
        service.resolve_google_news_urls.return_value = {"status": "ok", "updated": 1}
        stdout = io.StringIO()

        with patch("sys.stdout", stdout):
            exit_code = main(["resolve-google-news", "--since-hours", "72", "--limit", "10"])

        self.assertEqual(exit_code, 0)
        service.resolve_google_news_urls.assert_called_once_with(
            source_ids=None,
            article_ids=None,
            since_hours=72,
            limit=10,
        )
        self.assertIn('"updated": 1', stdout.getvalue())

    @patch("ainews.cli.configure_logging")
    @patch("ainews.cli.NewsService")
    @patch("ainews.cli.load_settings")
    def test_retry_extractions_command(
        self,
        mock_load_settings,
        mock_service_class,
        mock_configure_logging,
    ) -> None:
        mock_load_settings.return_value = MagicMock()
        service = mock_service_class.return_value
        service.retry_extractions.return_value = {"status": "ok", "requested": 1}
        stdout = io.StringIO()

        with patch("sys.stdout", stdout):
            exit_code = main(
                [
                    "retry-extractions",
                    "--status",
                    "throttled",
                    "--error-category",
                    "throttled",
                    "--due-only",
                    "--limit",
                    "5",
                ]
            )

        self.assertEqual(exit_code, 0)
        service.retry_extractions.assert_called_once_with(
            source_ids=None,
            article_ids=None,
            since_hours=None,
            extraction_status="throttled",
            extraction_error_category="throttled",
            due_only=True,
            limit=5,
        )
        self.assertIn('"requested": 1', stdout.getvalue())

    @patch("ainews.cli.configure_logging")
    @patch("ainews.cli.NewsService")
    @patch("ainews.cli.load_settings")
    def test_reset_source_cooldowns_command(
        self,
        mock_load_settings,
        mock_service_class,
        mock_configure_logging,
    ) -> None:
        mock_load_settings.return_value = MagicMock()
        service = mock_service_class.return_value
        service.reset_source_cooldowns.return_value = {"status": "ok", "cleared": 1}
        stdout = io.StringIO()

        with patch("sys.stdout", stdout):
            exit_code = main(["reset-source-cooldowns", "--source", "venturebeat"])

        self.assertEqual(exit_code, 0)
        service.reset_source_cooldowns.assert_called_once_with(
            source_ids=["venturebeat"],
            active_only=True,
        )
        self.assertIn('"cleared": 1', stdout.getvalue())

    @patch("ainews.cli.configure_logging")
    @patch("ainews.cli.NewsService")
    @patch("ainews.cli.load_settings")
    def test_ack_source_alerts_command(
        self,
        mock_load_settings,
        mock_service_class,
        mock_configure_logging,
    ) -> None:
        mock_load_settings.return_value = MagicMock()
        service = mock_service_class.return_value
        service.acknowledge_source_alerts.return_value = {"status": "ok", "acknowledged": 1}
        stdout = io.StringIO()

        with patch("sys.stdout", stdout):
            exit_code = main(
                ["ack-source-alerts", "--source", "venturebeat", "--note", "known issue"]
            )

        self.assertEqual(exit_code, 0)
        service.acknowledge_source_alerts.assert_called_once_with(
            source_ids=["venturebeat"],
            note="known issue",
        )
        self.assertIn('"acknowledged": 1', stdout.getvalue())

    @patch("ainews.cli.configure_logging")
    @patch("ainews.cli.NewsService")
    @patch("ainews.cli.load_settings")
    def test_snooze_source_alerts_command(
        self,
        mock_load_settings,
        mock_service_class,
        mock_configure_logging,
    ) -> None:
        mock_load_settings.return_value = MagicMock()
        service = mock_service_class.return_value
        service.snooze_source_alerts.return_value = {"status": "ok", "updated": 1}
        stdout = io.StringIO()

        with patch("sys.stdout", stdout):
            exit_code = main(
                ["snooze-source-alerts", "--source", "venturebeat", "--minutes", "90"]
            )

        self.assertEqual(exit_code, 0)
        service.snooze_source_alerts.assert_called_once_with(
            source_ids=["venturebeat"],
            minutes=90,
            clear=False,
        )
        self.assertIn('"updated": 1', stdout.getvalue())

    @patch("ainews.cli.configure_logging")
    @patch("ainews.cli.NewsService")
    @patch("ainews.cli.load_settings")
    def test_set_source_maintenance_command(
        self,
        mock_load_settings,
        mock_service_class,
        mock_configure_logging,
    ) -> None:
        mock_load_settings.return_value = MagicMock()
        service = mock_service_class.return_value
        service.set_source_maintenance.return_value = {"status": "ok", "updated": 1}
        stdout = io.StringIO()

        with patch("sys.stdout", stdout):
            exit_code = main(
                ["set-source-maintenance", "--source", "venturebeat", "--disable"]
            )

        self.assertEqual(exit_code, 0)
        service.set_source_maintenance.assert_called_once_with(
            source_ids=["venturebeat"],
            enabled=False,
        )
        self.assertIn('"updated": 1', stdout.getvalue())

    @patch("ainews.cli.configure_logging")
    @patch("ainews.cli.NewsService")
    @patch("ainews.cli.load_settings")
    def test_prune_source_runtime_history_command(
        self,
        mock_load_settings,
        mock_service_class,
        mock_configure_logging,
    ) -> None:
        mock_load_settings.return_value = MagicMock()
        service = mock_service_class.return_value
        service.prune_source_runtime_history.return_value = {"status": "ok", "events_deleted": 4}
        stdout = io.StringIO()

        with patch("sys.stdout", stdout):
            exit_code = main(
                ["prune-source-runtime-history", "--retention-days", "14", "--no-archive"]
            )

        self.assertEqual(exit_code, 0)
        service.prune_source_runtime_history.assert_called_once_with(
            retention_days=14,
            archive=False,
        )
        self.assertIn('"events_deleted": 4', stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
