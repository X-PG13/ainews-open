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

    def test_console_exposes_operator_status_rail(self) -> None:
        index = _read_text("src/ainews/web/index.html")
        app = _read_text("src/ainews/web/app.js")
        styles = _read_text("src/ainews/web/styles.css")

        for expected in (
            'id="heroStatusRail"',
            'id="heroRailHealthCard"',
            'id="heroRailSchemaCard"',
            'id="heroRailBuildCard"',
            'id="heroRailAgeCard"',
            'id="heroRailHealthHint"',
            'id="heroRailSchemaHint"',
            'id="heroRailBuildHint"',
            'id="heroRailAgeHint"',
            'id="heroReleaseVersion"',
            'id="heroDataWindow"',
            'id="heroAutoRefreshCountdown"',
            'id="heroVersionPulse"',
            "status-rail-item",
            "heroRailHealth",
            "heroRailSchema",
            "heroRailBuild",
            "heroRailAge",
            "heroAutoRefreshCountdown",
            'role="list"',
            'role="listitem"',
        ):
            self.assertIn(expected, index)

        for expected in (
            "heroRailHealth",
            "heroRailSchema",
            "heroRailBuild",
            "heroRailAge",
            "refs.heroRailHealth",
            "heroRailHealthCard",
            "heroRailSchemaCard",
            "heroRailBuildCard",
            "heroRailAgeCard",
            "refs.heroRailSchema",
            "refs.heroRailBuild",
            "refs.heroRailAge",
            "refs.heroRailHealthHint",
            "refs.heroRailSchemaHint",
            "refs.heroRailBuildHint",
            "refs.heroRailAgeHint",
            "refs.heroAutoRefreshCountdown",
            "refs.heroReleaseVersion",
            "refs.heroDataWindow",
            "heroReleaseVersion",
            "heroDataWindow",
            "updateAutoRefreshCountdown",
            "formatCountdown",
            "autoRefreshCountdownTimer",
            "AUTO_REFRESH_TICK_MS",
            "describeDataWindow",
            "statusClass",
            "refs.heroRailHealthCard.className",
            "refs.heroRailHealthCard.setAttribute",
            "refs.heroRailAgeCard.setAttribute",
            "schemaDisplay",
            "buildDisplay",
            "ageDisplay",
            "refs.heroRailAgeCard.className",
            "formatDataAge(generatedAt)",
            "operationStatusLabelAndClass",
        ):
            self.assertIn(expected, app)

        for expected in (
            ".hero-status-rail",
            ".status-rail-item",
            ".status-rail-item p",
            ".status-rail-item h3",
            ".status-rail-item.status-good",
            ".status-rail-item.status-pending",
            ".status-rail-item.status-warn",
            ".status-rail-item.status-unknown",
            ".hero-version-pulse",
            ".version-pulse-grid",
            ".version-pulse-item",
            ".version-kicker",
            ".sr-only",
            "grid-template-columns: repeat(2, minmax(0, 1fr));",
            "grid-template-columns: repeat(3, minmax(0, 1fr));",
        ):
            self.assertIn(expected, styles)

    def test_console_exposes_actionable_empty_states(self) -> None:
        index = _read_text("src/ainews/web/index.html")
        app = _read_text("src/ainews/web/app.js")
        styles = _read_text("src/ainews/web/styles.css")

        for expected in (
            'class="start-cues"',
            "1 保存 Token",
            "2 抓取新闻",
            "3 选稿预览",
        ):
            self.assertIn(expected, index)

        for expected in (
            "function emptyState",
            "当前没有文章",
            "没有待处理抽取项",
            "还没有选稿结果",
            "还没有发布记录",
            "暂无来源告警历史",
            "来源运行正常",
            "先跑一次流水线",
            "renderDigest(null);",
        ):
            self.assertIn(expected, app)

        for expected in (
            ".empty-state",
            ".empty-kicker",
            ".empty-steps",
            ".start-cues",
            "width: calc(100vw - 20px);",
            "flex-direction: column;",
        ):
            self.assertIn(expected, styles)


if __name__ == "__main__":
    unittest.main()
