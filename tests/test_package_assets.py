import unittest
from fnmatch import fnmatch
from importlib import resources
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class PackageAssetsTestCase(unittest.TestCase):
    def test_package_data_declares_web_console_assets(self) -> None:
        pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        expected_patterns = ("web/*.html", "web/*.css", "web/*.js", "web/*.svg")
        expected_assets = (
            "web/index.html",
            "web/styles.css",
            "web/app.js",
            "web/favicon.svg",
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

    def test_web_console_assets_are_readable_package_resources(self) -> None:
        package_root = resources.files("ainews")
        assets = {
            name: package_root.joinpath("web", name).read_text(encoding="utf-8")
            for name in ("index.html", "styles.css", "app.js", "favicon.svg")
        }

        self.assertIn("<title>AI News Open Console</title>", assets["index.html"])
        self.assertIn('href="favicon.svg"', assets["index.html"])
        self.assertIn('<style id="consoleFallbackStyles">', assets["index.html"])
        self.assertIn(".preview-mode-strip", assets["index.html"])
        self.assertIn(".preview-mode-strip", assets["styles.css"])
        self.assertIn("function setPreviewModeState", assets["app.js"])
        self.assertIn('<svg xmlns="http://www.w3.org/2000/svg"', assets["favicon.svg"])

        for expected_path in (
            "/assets/styles.css",
            "assets/styles.css",
            "styles.css",
            "/assets/app.js",
            "assets/app.js",
            "app.js",
        ):
            self.assertIn(expected_path, assets["index.html"])


if __name__ == "__main__":
    unittest.main()
