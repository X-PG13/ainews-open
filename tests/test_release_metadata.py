import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

PROJECT_VERSION_RE = re.compile(r'^version = "([^"]+)"$', re.MULTILINE)
RUNTIME_VERSION_RE = re.compile(r'^__version__ = "([^"]+)"$', re.MULTILINE)
CHANGELOG_RELEASE_RE = re.compile(
    r"^## \[(\d+\.\d+\.\d+)\] - \d{4}-\d{2}-\d{2}$",
    re.MULTILINE,
)
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


if __name__ == "__main__":
    unittest.main()
