import re
import unittest
from pathlib import Path
from typing import Optional
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]

INLINE_LINK_RE = re.compile(r"!?\[[^\]\n]+\]\(([^)\n]+)\)")
HTML_HREF_RE = re.compile(r"""href=["']([^"']+)["']""")


def _markdown_files() -> list[Path]:
    paths = list(ROOT.glob("*.md"))
    paths.extend((ROOT / "docs").rglob("*.md"))
    paths.extend((ROOT / ".github").rglob("*.md"))
    return sorted(path for path in paths if path.is_file())


def _iter_link_targets(path: Path) -> list[tuple[int, str]]:
    targets: list[tuple[int, str]] = []
    in_fence = False
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        for pattern in (INLINE_LINK_RE, HTML_HREF_RE):
            targets.extend((line_number, match.group(1).strip()) for match in pattern.finditer(line))
    return targets


def _local_path_target(target: str) -> Optional[str]:
    if not target or target.startswith("#") or target.startswith("//"):
        return None
    if urlsplit(target).scheme:
        return None
    if target.startswith("/"):
        return None

    if target.startswith("<") and ">" in target:
        target = target[1 : target.index(">")]
    else:
        target = target.split()[0]

    path_part = target.split("#", 1)[0]
    if not path_part:
        return None
    return unquote(path_part)


class DocsLinksTestCase(unittest.TestCase):
    def test_markdown_relative_links_point_to_existing_files(self) -> None:
        failures: list[str] = []
        for markdown_file in _markdown_files():
            for line_number, raw_target in _iter_link_targets(markdown_file):
                path_target = _local_path_target(raw_target)
                if path_target is None:
                    continue

                resolved = (markdown_file.parent / path_target).resolve()
                try:
                    resolved.relative_to(ROOT.resolve())
                except ValueError:
                    failures.append(
                        f"{markdown_file.relative_to(ROOT)}:{line_number}: "
                        f"{raw_target} points outside the repository"
                    )
                    continue

                if not resolved.exists():
                    failures.append(
                        f"{markdown_file.relative_to(ROOT)}:{line_number}: "
                        f"{raw_target} does not resolve to an existing file"
                    )

        self.assertEqual(failures, [])


if __name__ == "__main__":
    unittest.main()
