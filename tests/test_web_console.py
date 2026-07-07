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
            'id="previewModeStrip"',
            'id="previewModeTitle"',
            'id="previewModeDetail"',
            "Preview mode",
            "正在确认连接方式",
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
            'id="heroLastSync"',
            'id="heroVersionPulse"',
            "status-rail-item",
            "heroRailHealth",
            "heroRailSchema",
            "heroRailBuild",
            "heroRailAge",
            "heroAutoRefreshCountdown",
            "heroLastSync",
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
            "refs.heroLastSync",
            "refs.heroReleaseVersion",
            "refs.heroDataWindow",
            "refs.previewModeStrip",
            "refs.previewModeTitle",
            "refs.previewModeDetail",
            "setPreviewModeState",
            "静态预览，只读",
            "HTTP 服务视图，等待后端数据",
            "已连接后端服务",
            "heroReleaseVersion",
            "heroDataWindow",
            "updateLastSyncStatus",
            "formatLastSyncTime",
            "state.lastSyncAt",
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
            ".preview-mode-strip",
            ".preview-mode-strip.connected",
            ".preview-mode-strip.file",
            ".preview-mode-kicker",
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

    def test_console_asset_loading_paths_cover_file_and_http_modes(self) -> None:
        index = _read_text("src/ainews/web/index.html")
        app = _read_text("src/ainews/web/app.js")

        expected_snippets = (
            "styles.css",
            "app.js",
            "assets/styles.css",
            "assets/app.js",
            "consoleStylesheet",
            "consoleAppScript",
            "loadElementWithFallback",
            "waitForAssetLoad",
            "bootstrapConsoleAssets",
            "LOAD_TIMEOUT_MS",
        )
        for expected in expected_snippets:
            self.assertIn(expected, index)

        expected_absent_snippets = (
            "this.dataset.fallback",
            "window.__ainewsAppScriptFallback",
        )
        for expected in expected_absent_snippets:
            self.assertNotIn(expected, index)

        expected_app_snippets = (
            "const IS_FILE_PROTOCOL = window.location.protocol === \"file:\";",
            "const CAN_USE_BACKEND = !IS_FILE_PROTOCOL;",
            "const FILE_MODE_MESSAGE =",
            "function setFileModeReadOnly()",
            "if (!CAN_USE_BACKEND)",
            "setFileModeReadOnly();",
        )
        for expected in expected_app_snippets:
            self.assertIn(expected, app)

    def test_console_includes_inline_fallback_styles_for_static_views(self) -> None:
        index = _read_text("src/ainews/web/index.html")

        for expected in (
            '<style id="consoleFallbackStyles">',
            ".hero-status-rail",
            ".preview-mode-strip",
            ".preview-mode-kicker",
            ".toolbar-row",
            ".publication-list",
            "background:",
        ):
            self.assertIn(expected, index)


if __name__ == "__main__":
    unittest.main()
