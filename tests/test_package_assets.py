import tempfile
import unittest
import zipfile
from pathlib import Path

from build import ProjectBuilder

ROOT = Path(__file__).resolve().parents[1]


class PackageAssetsTestCase(unittest.TestCase):
    def test_wheel_includes_web_console_assets(self) -> None:
        expected_assets = {
            "ainews/web/app.js",
            "ainews/web/index.html",
            "ainews/web/styles.css",
        }

        with tempfile.TemporaryDirectory() as tmp_dir:
            wheel_path = ProjectBuilder(ROOT).build("wheel", tmp_dir)
            with zipfile.ZipFile(wheel_path) as wheel:
                packaged_files = set(wheel.namelist())

        self.assertTrue(
            expected_assets.issubset(packaged_files),
            f"Missing packaged web console assets: {sorted(expected_assets - packaged_files)}",
        )


if __name__ == "__main__":
    unittest.main()
