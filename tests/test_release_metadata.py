import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

PROJECT_VERSION_RE = re.compile(r'^version = "([^"]+)"$', re.MULTILINE)
PROJECT_NAME_RE = re.compile(r'^name = "([^"]+)"$', re.MULTILINE)
RUNTIME_VERSION_RE = re.compile(r'^__version__ = "([^"]+)"$', re.MULTILINE)
CHANGELOG_RELEASE_RE = re.compile(
    r"^## \[(\d+\.\d+\.\d+)\] - \d{4}-\d{2}-\d{2}$",
    re.MULTILINE,
)
MARKDOWN_LINK_RE = re.compile(r"!?\[[^\]\n]+\]\(([^)\n]+)\)")
SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")
LATEST_HEADING_ZH = "\u6700\u65b0\u7248\u672c"


def _read_text(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def _match_required(pattern: re.Pattern[str], text: str, label: str) -> str:
    match = pattern.search(text)
    if match is None:
        raise AssertionError(f"{label} is missing")
    return match.group(1)


def _project_version() -> str:
    return _match_required(PROJECT_VERSION_RE, _read_text("pyproject.toml"), "project.version")


def _project_name() -> str:
    return _match_required(PROJECT_NAME_RE, _read_text("pyproject.toml"), "project.name")


def _distribution_name() -> str:
    return re.sub(r"[-_.]+", "_", _project_name()).lower()


def _expected_release_asset_names(version: str) -> tuple[str, str, str, str]:
    distribution = _distribution_name()
    return (
        f"{distribution}-{version}-py3-none-any.whl",
        f"{distribution}-{version}.tar.gz",
        "sha256sums.txt",
        f"v{version}-sbom.json",
    )


def _markdown_section(text: str, heading: str) -> str:
    marker = f"## {heading}"
    start = text.find(marker)
    if start == -1:
        raise AssertionError(f"Markdown section not found: {heading}")

    content_start = start + len(marker)
    next_heading = re.search(r"^## ", text[content_start:], re.MULTILINE)
    if next_heading is None:
        return text[content_start:]
    return text[content_start : content_start + next_heading.start()]


def _markdown_link_targets(relative_path: str) -> set[str]:
    targets: set[str] = set()
    for target in MARKDOWN_LINK_RE.findall(_read_text(relative_path)):
        path_target = target.split("#", 1)[0].strip()
        if path_target:
            targets.add(path_target)
    return targets


class ReleaseMetadataTestCase(unittest.TestCase):
    def test_project_and_runtime_versions_match(self) -> None:
        project_version = _project_version()
        runtime_version = _match_required(
            RUNTIME_VERSION_RE,
            _read_text("src/ainews/__init__.py"),
            "ainews.__version__",
        )

        self.assertRegex(project_version, SEMVER_RE)
        self.assertEqual(runtime_version, project_version)

    def test_current_release_docs_are_present_and_indexed(self) -> None:
        version = _project_version()
        release_note_path = ROOT / "docs" / "releases" / f"v{version}.md"
        release_link = f"- [v{version}](./v{version}.md)"

        self.assertTrue(release_note_path.is_file(), f"{release_note_path} does not exist")
        self.assertEqual(
            release_note_path.read_text(encoding="utf-8").splitlines()[0],
            f"# AI News Open v{version}",
        )

        changelog_version = _match_required(
            CHANGELOG_RELEASE_RE,
            _read_text("CHANGELOG.md"),
            "latest CHANGELOG release entry",
        )
        self.assertEqual(changelog_version, version)

        release_index = _read_text("docs/releases/README.md")
        release_index_zh = _read_text("docs/releases/README.zh-CN.md")
        self.assertIn(release_link, _markdown_section(release_index, "Latest"))
        self.assertIn(release_link, _markdown_section(release_index_zh, LATEST_HEADING_ZH))

    def test_release_asset_names_match_current_package_version(self) -> None:
        version = _project_version()

        self.assertEqual(
            _expected_release_asset_names(version),
            (
                f"ainews_open-{version}-py3-none-any.whl",
                f"ainews_open-{version}.tar.gz",
                "sha256sums.txt",
                f"v{version}-sbom.json",
            ),
        )

    def test_release_asset_contract_is_documented_and_enforced(self) -> None:
        distribution = _distribution_name()
        templated_asset_names = (
            f"{distribution}-${{VERSION}}-py3-none-any.whl",
            f"{distribution}-${{VERSION}}.tar.gz",
            "sha256sums.txt",
            "v${VERSION}-sbom.json",
        )
        release_docs = _read_text("docs/release-artifacts.md")
        release_docs_zh = _read_text("docs/release-artifacts.zh-CN.md")

        for asset_name in templated_asset_names:
            self.assertIn(asset_name, release_docs)
            self.assertIn(asset_name, release_docs_zh)

        release_workflow = _read_text(".github/workflows/release.yml")
        self.assertIn("for artifact in *.whl *.tar.gz; do", release_workflow)
        self.assertIn('-o "dist/${GITHUB_REF_NAME}-sbom.json"', release_workflow)
        self.assertIn('gh release create "${TAG}" dist/*', release_workflow)

        smoke_workflow = _read_text(".github/workflows/release-artifact-smoke.yml")
        self.assertIn('VERSION="${RELEASE_TAG#v}"', smoke_workflow)
        self.assertIn(
            f'echo "WHEEL_ASSET={distribution}-${{VERSION}}-py3-none-any.whl"',
            smoke_workflow,
        )
        self.assertIn(f'echo "SDIST_ASSET={distribution}-${{VERSION}}.tar.gz"', smoke_workflow)
        self.assertIn('echo "CHECKSUMS_ASSET=sha256sums.txt"', smoke_workflow)
        self.assertIn('echo "SBOM_ASSET=v${VERSION}-sbom.json"', smoke_workflow)

        for asset_variable in ("WHEEL_ASSET", "SDIST_ASSET", "CHECKSUMS_ASSET", "SBOM_ASSET"):
            self.assertIn(f'--pattern "${{{asset_variable}}}"', smoke_workflow)
            self.assertIn(f'"${{{asset_variable}}}"', smoke_workflow)

    def test_readmes_expose_release_maintenance_entry_points(self) -> None:
        expected_readme_links = {
            "docs/releases/README.md",
            "docs/release-artifacts.md",
            "docs/release-recovery.md",
            "docs/release-checklist.md",
            "docs/support-lifecycle.md",
        }
        expected_readme_zh_links = {
            "docs/releases/README.zh-CN.md",
            "docs/release-artifacts.zh-CN.md",
            "docs/release-recovery.zh-CN.md",
            "docs/release-checklist.zh-CN.md",
            "docs/support-lifecycle.zh-CN.md",
        }

        self.assertLessEqual(expected_readme_links, _markdown_link_targets("README.md"))
        self.assertLessEqual(expected_readme_zh_links, _markdown_link_targets("README.zh-CN.md"))


if __name__ == "__main__":
    unittest.main()
