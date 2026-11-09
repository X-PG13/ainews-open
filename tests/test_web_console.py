import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read_text(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


class WebConsoleTestCase(unittest.TestCase):
    def test_console_exposes_page_identity_and_keyboard_entry(self) -> None:
        index = _read_text("src/ainews/web/index.html")
        styles = _read_text("src/ainews/web/styles.css")

        for expected in (
            'name="description"',
            'name="theme-color" content="#f7f0e5"',
            '<link rel="icon" type="image/svg+xml" href="favicon.svg" />',
            '<a class="skip-link" href="#operator-console">',
            'id="mainContent"',
            'id="operator-console"',
            'aria-labelledby="operatorConsoleTitle"',
            'id="operatorConsoleTitle"',
            'tabindex="-1"',
        ):
            self.assertIn(expected, index)

        for expected in (
            ".skip-link",
            ".skip-link:focus-visible",
            "max-width: calc(100vw - 24px);",
            "transform: translateY(-180%);",
            "transform: translateY(0);",
            "#operator-console",
            "scroll-margin-top: 16px;",
            "outline: 2px solid rgba(219, 61, 27, 0.48);",
            ".article-link:focus-visible",
        ):
            self.assertIn(expected, styles)

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
            'id="previewAssetDetail"',
            "Preview mode",
            "正在确认连接方式",
            "Assets: CSS/JS 等待加载",
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
            "refs.previewAssetDetail",
            "setPreviewModeState",
            "updatePreviewAssetStatus",
            "formatAssetStatus",
            "shortAssetPath",
            "静态预览，只读",
            "HTTP 服务视图，等待后端数据",
            "已连接后端服务",
            'formatAssetStatus("CSS", status.css)',
            'formatAssetStatus("JS", status.js)',
            'loaded: "已加载"',
            'fallback: "仅 fallback"',
            "inline fallback",
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
            ".preview-mode-detail",
            ".preview-asset-detail",
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
            "ASSET_STATUS_EVENT",
            "ainews-console-asset-status",
            "window.__ainewsConsoleAssetStatus",
            "updateAssetStatus",
            "snapshotAssetStatus",
            "data-console-asset",
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

    def test_console_first_screen_loading_states_are_visible_and_settled(self) -> None:
        index = _read_text("src/ainews/web/index.html")
        app = _read_text("src/ainews/web/app.js")
        styles = _read_text("src/ainews/web/styles.css")

        for expected in (
            'class="operations-status-strip loading"',
            'class="status-rail-item is-loading"',
            'class="stats-grid first-screen-loading"',
            'class="operations-summary-grid first-screen-loading"',
            'class="first-screen-loading-block"',
            'data-loading-placeholder="stats"',
            'data-loading-placeholder="operations-summary"',
            'data-loading-placeholder="operations-health"',
            'data-loading-placeholder="pipeline-runs"',
            'data-loading-placeholder="runtime-sources"',
            'data-loading-placeholder="source-alerts"',
            'data-loading-placeholder="publication-failures"',
            "首屏统计正在加载",
            "运维摘要正在加载",
            "metrics: 等待采样",
        ):
            self.assertIn(expected, index)

        for expected in (
            "function firstScreenLoadingContainers",
            "function markFirstScreenSectionLoaded",
            "function settleFirstScreenLoading",
            "function markFirstScreenWaiting",
            'classList.remove("first-screen-loading", "first-screen-loading-block")',
            'document.querySelectorAll(".status-rail-item.is-loading")',
            'document.querySelectorAll("[data-loading-placeholder]")',
            'element.classList.add("loading-paused")',
            'refs.operationsStatusStrip.classList.remove("loading", "waiting")',
            'refs.operationsStatusStrip.classList.add("waiting")',
            "markFirstScreenSectionLoaded(refs.statsGrid)",
            "markFirstScreenSectionLoaded(refs.operationsSummary)",
            "markFirstScreenSectionLoaded(refs.operationsHealth)",
            "markFirstScreenSectionLoaded(refs.operationsPipelineRuns)",
            "markFirstScreenWaiting();",
            "settleFirstScreenLoading();",
        ):
            self.assertIn(expected, app)

        for expected in (
            ".operations-status-strip.loading",
            ".status-rail-item.is-loading",
            ".first-screen-loading-block",
            ".loading-card",
            ".loading-card.loading-paused",
            ".loading-kicker",
            ".loading-heading",
            ".loading-line.short",
            "@keyframes loading-sweep",
            "@media (prefers-reduced-motion: reduce)",
            ".loading-card::after",
        ):
            self.assertIn(expected, styles)

    def test_console_includes_inline_fallback_styles_for_static_views(self) -> None:
        index = _read_text("src/ainews/web/index.html")

        for expected in (
            '<style id="consoleFallbackStyles">',
            ".hero-status-rail",
            ".preview-mode-strip",
            ".preview-mode-kicker",
            ".preview-asset-detail",
            ".refresh-failure-strip",
            ".refresh-failure-strip[hidden]",
            ".first-screen-loading-block",
            ".loading-card",
            ".loading-heading",
            ".loading-line",
            ".toolbar-row",
            ".publication-list",
            "background:",
        ):
            self.assertIn(expected, index)

    def test_console_refresh_failure_exposes_retry_and_recovery_hooks(self) -> None:
        index = _read_text("src/ainews/web/index.html")
        app = _read_text("src/ainews/web/app.js")
        styles = _read_text("src/ainews/web/styles.css")

        status_at = index.index('id="operationsStatusStrip"')
        failure_at = index.index('id="refreshFailureStrip"')
        preview_at = index.index('id="previewModeStrip"')
        self.assertLess(status_at, failure_at)
        self.assertLess(failure_at, preview_at)

        for expected in (
            'id="refreshFailureStrip"',
            'class="refresh-failure-strip"',
            'role="status"',
            'aria-live="polite"',
            'aria-atomic="true"',
            'id="refreshFailureTitle"',
            'id="refreshFailureSummary"',
            'id="refreshFailureLastSync"',
            'id="retryRefreshButton"',
            "面板刷新失败",
            "上次成功同步：尚未成功同步",
            "重试刷新",
            "Refresh failed",
        ):
            self.assertIn(expected, index)

        for expected in (
            "refreshFailure: null",
            "refs.refreshFailureStrip",
            "refs.refreshFailureSummary",
            "refs.refreshFailureLastSync",
            "refs.retryRefreshButton",
            "function isFileModeRefreshError",
            "function sanitizeRefreshFailureMessage",
            "function renderRefreshFailure",
            "function clearRefreshFailure",
            "function setRefreshFailure",
            "function lastSuccessfulSyncText",
            "REFRESH_FAILURE_SUMMARY_LIMIT",
            "REFRESH_FAILURE_FALLBACK",
            'normalized === FILE_MODE_MESSAGE',
            'return "";',
            '.replace(/<[^>]*>/g, " ")',
            '.replace(/bearer\\s+\\S+/gi, "bearer [redacted]")',
            '(token|password|secret|api[_-]?key)',
            '$1=[redacted]',
            '.replace(/https?:\\/\\/\\S+/gi, "[url]")',
            "redacted.slice(0, REFRESH_FAILURE_SUMMARY_LIMIT)",
            "refs.refreshFailureSummary.textContent = active ? failure.message : \"\"",
            'strip.dataset.refreshState = active ? "failed" : "idle"',
            "strip.hidden = !active",
            "state.refreshFailure = null",
            "failedAt: Date.now()",
            "sanitizeRefreshFailureMessage(error && error.message)",
            "if (!message) {\n    clearRefreshFailure();",
            'refs.retryRefreshButton.addEventListener("click", refreshAll);',
            "renderRefreshFailure();",
        ):
            self.assertIn(expected, app)

        self.assertNotIn("refreshFailureSummary.innerHTML", app)

        refresh_all = _function_source(app, "refreshAll")
        self.assertIn('logJob("refresh failed", { error: error.message });', refresh_all)
        self.assertIn("markFirstScreenWaiting();", refresh_all)
        self.assertIn("setRefreshFailure(error);", refresh_all)
        self.assertIn("if (success) {\n      state.lastSyncAt = Date.now();\n      clearRefreshFailure();", refresh_all)
        self.assertEqual(refresh_all.count("state.lastSyncAt = Date.now();"), 1)

        file_mode = _function_source(app, "setFileModeReadOnly")
        self.assertIn("clearRefreshFailure();", file_mode)
        self.assertIn('setPreviewModeState("file");', file_mode)
        self.assertNotIn("setRefreshFailure(", file_mode)
        self.assertIn("refs.retryRefreshButton.disabled = true;", file_mode)

        for expected in (
            ".refresh-failure-strip",
            ".refresh-failure-strip[hidden]",
            ".refresh-failure-copy",
            ".refresh-failure-kicker",
            ".refresh-failure-summary",
            ".refresh-failure-last-sync",
            ".refresh-failure-strip .button",
        ):
            self.assertIn(expected, styles)


def _function_source(source: str, name: str) -> str:
    marker = f"function {name}("
    start = source.index(marker)
    brace = source.index("{", start)
    depth = 0
    for index in range(brace, len(source)):
        char = source[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return source[start : index + 1]
    raise AssertionError(f"could not extract {name}")


if __name__ == "__main__":
    unittest.main()
