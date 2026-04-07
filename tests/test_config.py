import os
import tempfile
import unittest
from pathlib import Path

from ainews.config import load_settings


class ConfigTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._previous_env = dict(os.environ)

    def tearDown(self) -> None:
        os.environ.clear()
        os.environ.update(self._previous_env)

    def test_load_settings_reads_env_file_and_resolves_relative_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            with open(os.path.join(temp_dir, ".env"), "w", encoding="utf-8") as handle:
                handle.write("AINEWS_ADMIN_TOKEN=from-env-file\n")
                handle.write("AINEWS_LOG_FORMAT=json\n")
                handle.write("AINEWS_TELEGRAM_DISABLE_NOTIFICATION=true\n")

            os.environ["AINEWS_HOME"] = temp_dir
            os.environ["AINEWS_DATABASE_URL"] = "sqlite:///custom/ainews.db"
            os.environ["AINEWS_OUTPUT_DIR"] = "exports"
            os.environ["AINEWS_STATIC_SITE_DIR"] = "exports/site"
            os.environ["AINEWS_LOG_LEVEL"] = "debug"

            settings = load_settings()

            self.assertEqual(
                settings.database_path,
                (Path(temp_dir) / "custom" / "ainews.db").resolve(),
            )
            self.assertEqual(settings.output_dir, (Path(temp_dir) / "exports").resolve())
            self.assertEqual(settings.static_site_dir, (Path(temp_dir) / "exports" / "site").resolve())
            self.assertEqual(settings.admin_token, "from-env-file")
            self.assertEqual(settings.log_level, "DEBUG")
            self.assertEqual(settings.log_format, "json")
            self.assertTrue(settings.telegram_disable_notification)


if __name__ == "__main__":
    unittest.main()
