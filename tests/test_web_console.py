import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read_text(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


class WebConsoleTestCase(unittest.TestCase):
    def test_console_exposes_operator_workflow_map(self) -> None:
        index = _read_text("src/ainews/web/index.html")
        styles = _read_text("src/ainews/web/styles.css")

        for expected in (
            'class="workflow-map panel"',
            "Operator Workflow",
            "从线索到发布的闭环",
            "采集线索",
            "抽取与恢复",
            "选稿与编辑",
            "多渠道发布",
            "Zero-build admin",
            "Runtime-aware",
            "Publish-ready",
        ):
            self.assertIn(expected, index)

        for expected in (
            ".workflow-map",
            ".workflow-steps",
            ".workflow-step",
            ".hero-pills",
        ):
            self.assertIn(expected, styles)


if __name__ == "__main__":
    unittest.main()
