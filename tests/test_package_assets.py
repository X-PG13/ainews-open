import unittest
from fnmatch import fnmatch
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class PackageAssetsTestCase(unittest.TestCase):
    def test_package_data_declares_web_console_assets(self) -> None:
        pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        expected_patterns = ("web/*.html", "web/*.css", "web/*.js")
        expected_assets = (
            "web/index.html",
            "web/styles.css",
            "web/app.js",
        )

        self.assertIn("[tool.setuptools.package-data]", pyproject)
        self.assertIn("ainews =", pyproject)
        for pattern in expected_patterns:
            self.assertIn(f'"{pattern}"', pyproject)

        for asset in expected_assets:
            self.assertTrue((ROOT / "src" / "ainews" / asset).is_file(), asset)
            self.assertTrue(
                any(fnmatch(asset, pattern) for pattern in expected_patterns),
                f"{asset} is not covered by package-data patterns",
            )


if __name__ == "__main__":
    unittest.main()
