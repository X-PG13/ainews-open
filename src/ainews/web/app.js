const state = {
  token: localStorage.getItem("ainews_admin_token") || "",
  currentDigest: null,
  currentDigestPayload: null,
  currentArticles: [],
  selectedDigestId: null,
  editorActor: localStorage.getItem("ainews_digest_editor_actor") || "",
};

const refs = {
  adminToken: document.getElementById("adminToken"),
  saveTokenButton: document.getElementById("saveTokenButton"),
  refreshAllButton: document.getElementById("refreshAllButton"),
  ingestButton: document.getElementById("ingestButton"),
  extractButton: document.getElementById("extractButton"),
  enrichButton: document.getElementById("enrichButton"),
  digestPreviewButton: document.getElementById("digestPreviewButton"),
  freezeDigestButton: document.getElementById("freezeDigestButton"),
  saveDigestEditorButton: document.getElementById("saveDigestEditorButton"),
  digestEditorActorInput: document.getElementById("digestEditorActorInput"),
  digestChangeSummaryInput: document.getElementById("digestChangeSummaryInput"),
  digestButton: document.getElementById("digestButton"),
  pipelineButton: document.getElementById("pipelineButton"),
  publishButton: document.getElementById("publishButton"),
  jobOutput: document.getElementById("jobOutput"),
  statsGrid: document.getElementById("statsGrid"),
  sourcesList: document.getElementById("sourcesList"),
  refreshSourcesButton: document.getElementById("refreshSourcesButton"),
  resetSourceCooldownsButton: document.getElementById("resetSourceCooldownsButton"),
  digestView: document.getElementById("digestView"),
  digestPreviewView: document.getElementById("digestPreviewView"),
  digestEditorView: document.getElementById("digestEditorView"),
  digestHistoryView: document.getElementById("digestHistoryView"),
  refreshDigestHistoryButton: document.getElementById("refreshDigestHistoryButton"),
  digestArchive: document.getElementById("digestArchive"),
  articlesList: document.getElementById("articlesList"),
  regionSelect: document.getElementById("regionSelect"),
  sinceHoursSelect: document.getElementById("sinceHoursSelect"),
  limitInput: document.getElementById("limitInput"),
  maxItemsInput: document.getElementById("maxItemsInput"),
  publicationsList: document.getElementById("publicationsList"),
  publicationsHint: document.getElementById("publicationsHint"),
  publicationTargetFilter: document.getElementById("publicationTargetFilter"),
  publicationStatusFilter: document.getElementById("publicationStatusFilter"),
  publicationOnlyPendingCheckbox: document.getElementById("publicationOnlyPendingCheckbox"),
  refreshPublicationsButton: document.getElementById("refreshPublicationsButton"),
  clearPublicationDigestFilterButton: document.getElementById("clearPublicationDigestFilterButton"),
  extractionOpsSummary: document.getElementById("extractionOpsSummary"),
  extractionOpsList: document.getElementById("extractionOpsList"),
  extractionStatusFilter: document.getElementById("extractionStatusFilter"),
  extractionErrorCategoryFilter: document.getElementById("extractionErrorCategoryFilter"),
  extractionDueOnlyCheckbox: document.getElementById("extractionDueOnlyCheckbox"),
  refreshExtractionOpsButton: document.getElementById("refreshExtractionOpsButton"),
  retryExtractionSelectionButton: document.getElementById("retryExtractionSelectionButton"),
  sourceAlertsList: document.getElementById("sourceAlertsList"),
  refreshSourceAlertsButton: document.getElementById("refreshSourceAlertsButton"),
  publishPreviewView: document.getElementById("publishPreviewView"),
  refreshPublishPreviewButton: document.getElementById("refreshPublishPreviewButton"),
  operationsSummary: document.getElementById("operationsSummary"),
  operationsHealth: document.getElementById("operationsHealth"),
  operationsMetrics: document.getElementById("operationsMetrics"),
  operationsPipelineRuns: document.getElementById("operationsPipelineRuns"),
  operationsSources: document.getElementById("operationsSources"),
  operationsAlerts: document.getElementById("operationsAlerts"),
  operationsPublicationFailures: document.getElementById("operationsPublicationFailures"),
  publishTargetInputs: Array.from(document.querySelectorAll(".publish-target")),
  wechatSubmitCheckbox: document.getElementById("wechatSubmitCheckbox"),
};

refs.adminToken.value = state.token;
refs.digestEditorActorInput.value = state.editorActor;

function adminHeaders() {
  const headers = { "Content-Type": "application/json" };
  if (state.token) {
    headers["X-Admin-Token"] = state.token;
  }
  return headers;
}

async function fetchJson(url, options = {}) {
  const response = await fetch(url, options);
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = payload.detail || `${response.status} ${response.statusText}`;
    throw new Error(detail);
  }
  return payload;
}

function logJob(title, payload) {
  refs.jobOutput.textContent = `${title}\n${JSON.stringify(payload, null, 2)}`;
}

function getFilters() {
  return {
    region: refs.regionSelect.value,
    since_hours: Number(refs.sinceHoursSelect.value),
    limit: Number(refs.limitInput.value),
    max_items_per_source: Number(refs.maxItemsInput.value),
  };
}

function getDigestEditorMeta() {
  return {
    actor: refs.digestEditorActorInput.value.trim() || null,
    change_summary: refs.digestChangeSummaryInput.value.trim() || null,
  };
}

function renderStats(stats) {
  const cards = [
    ["文章总数", stats.total_articles || 0],
    ["可见文章", stats.visible_articles || 0],
    ["已 suppress", stats.suppressed_articles || 0],
    ["已抓正文", stats.extracted_articles || 0],
    ["已翻译国际稿", stats.enriched_articles || 0],
    ["来源冷却", stats.active_source_cooldowns || 0],
    ["静默来源", stats.silenced_source_alerts || 0],
    ["维护来源", stats.sources_in_maintenance || 0],
    ["已发布", stats.total_publications || 0],
    ["日报存档", stats.total_digests || 0],
    ["LLM", stats.llm_configured ? (stats.llm_model || "已配置") : "未配置"],
  ];
  refs.statsGrid.innerHTML = cards
    .map(
      ([label, value]) => `
      <article class="panel stat-card">
        <p class="stat-label">${label}</p>
        <div class="stat-value">${value}</div>
      </article>
    `
    )
    .join("");
  renderExtractionOpsSummary(stats);
}

function operationStatusClass(status) {
  if (status === "ok" || status === "ready") return "good";
  if (status === "degraded" || status === "pending" || status === "partial_error") return "pending";
  if (status === "error" || status === "blocked") return "warn";
  return "";
}

function summarizePairs(payload) {
  if (!payload || typeof payload !== "object") return "";
  return Object.entries(payload)
    .filter(([, value]) => value !== null && value !== undefined && value !== "" && value !== 0)
    .slice(0, 4)
    .map(([key, value]) => `${key}=${value}`)
    .join(" · ");
}

function renderOperationsSummary(payload) {
  const health = payload.health || {};
  const stats = payload.stats || {};
  const metrics = payload.metrics || {};
  const cards = [
    ["health", health.status || "unknown", operationStatusClass(health.status)],
    ["cooldowns", stats.active_source_cooldowns || 0, stats.active_source_cooldowns ? "warn" : "good"],
    ["publish errors", stats.publication_errors || 0, stats.publication_errors ? "warn" : "good"],
    ["pending publish", stats.pending_publications || 0, stats.pending_publications ? "pending" : "good"],
    ["scheduled retries", stats.scheduled_extraction_retries || 0, stats.scheduled_extraction_retries ? "pending" : "good"],
    ["alerts sent", metrics.alert_sends_total || 0, metrics.alert_sends_total ? "" : "good"],
  ];
  refs.operationsSummary.innerHTML = cards
    .map(
      ([label, value, klass]) => `
        <article class="stat-card operations-stat-card">
          <p class="stat-label">${escapeHtml(String(label))}</p>
          <div class="stat-value ${klass ? `status-${klass}` : ""}">${escapeHtml(String(value))}</div>
        </article>
      `
    )
    .join("");
}

function renderOperationsHealth(payload) {
  const health = payload.health || {};
  const checks = Object.entries(health.checks || {})
    .map(
      ([key, value]) =>
        `<span class="chip ${operationStatusClass(String(value))}">${escapeHtml(String(key))}: ${escapeHtml(String(value))}</span>`
    )
    .join("");
  const reasons = (health.degraded_reasons || []).length
    ? (health.degraded_reasons || [])
        .map((reason) => `<span class="chip warn">${escapeHtml(reason)}</span>`)
        .join("")
    : '<span class="chip good">no degraded reasons</span>';
  refs.operationsHealth.innerHTML = `
    <article class="publication-card">
      <header class="publication-head">
        <div>
          <strong>status</strong>
          <div class="publication-meta">
            <span>generated_at: ${escapeHtml(payload.generated_at || "")}</span>
            <span>ready: ${escapeHtml(String(Boolean(health.ready)))}</span>
            <span>schema: ${escapeHtml(String(health.schema_version || ""))}</span>
          </div>
        </div>
        <span class="chip ${operationStatusClass(health.status)}">${escapeHtml(health.status || "unknown")}</span>
      </header>
      <div class="chip-row compact">${checks}</div>
      <div class="chip-row">${reasons}</div>
    </article>
  `;
  const metrics = payload.metrics || {};
  const pipelineTotals = summarizePairs(metrics.pipeline_runs_total);
  const extractFailures = summarizePairs(metrics.extract_failures_total);
  refs.operationsMetrics.innerHTML = [
    ["pipeline_runs", pipelineTotals || "none"],
    ["extract_failures", extractFailures || "none"],
    ["source_recoveries_total", metrics.source_recoveries_total || 0],
    ["source_cooldowns_active", metrics.source_cooldowns_active || 0],
    ["alert_sends_total", metrics.alert_sends_total || 0],
  ]
    .map(
      ([label, value]) =>
        `<span class="chip">${escapeHtml(String(label))}: ${escapeHtml(String(value))}</span>`
    )
    .join("");
}

function renderOperationsPipelineRuns(runs) {
  refs.operationsPipelineRuns.innerHTML = runs.length
    ? runs
        .map(
          (item) => `
            <article class="publication-card operations-card">
              <header class="publication-head">
                <strong>${escapeHtml(item.name || "pipeline")}</strong>
                <span class="chip ${operationStatusClass(item.status)}">${escapeHtml(item.status || "unknown")}</span>
              </header>
              <div class="publication-meta">
                <span>started: ${escapeHtml(item.started_at || "")}</span>
                <span>finished: ${escapeHtml(item.finished_at || "")}</span>
                <span>duration: ${escapeHtml(String(item.duration_ms || 0))}ms</span>
              </div>
              ${
                summarizePairs(item.context)
                  ? `<p class="article-brief"><strong>context:</strong> ${escapeHtml(summarizePairs(item.context))}</p>`
                  : ""
              }
              ${
                summarizePairs(item.metrics)
                  ? `<p class="article-brief"><strong>metrics:</strong> ${escapeHtml(summarizePairs(item.metrics))}</p>`
                  : ""
              }
            </article>
          `
        )
        .join("")
    : '<p class="muted">最近还没有记录到 pipeline 运行。</p>';
}

function renderOperationsSources(sources) {
  refs.operationsSources.innerHTML = sources.length
    ? sources
        .map(
          (source) => `
            <article class="publication-card operations-card">
              <header class="publication-head">
                <strong>${escapeHtml(source.name || source.id || "unknown source")}</strong>
                <div class="chip-row compact">
                  ${
                    source.cooldown_active
                      ? `<span class="chip ${source.cooldown_status === "blocked" ? "warn" : "pending"}">${escapeHtml(source.cooldown_status || "cooldown")}</span>`
                      : '<span class="chip good">normal</span>'
                  }
                  ${source.maintenance_mode ? '<span class="chip pending">maintenance</span>' : ""}
                  ${source.silenced_active ? '<span class="chip">silenced</span>' : ""}
                </div>
              </header>
              <div class="publication-meta">
                ${
                  source.recent_success_rate !== null && source.recent_success_rate !== undefined
                    ? `<span>success_rate: ${escapeHtml(String(source.recent_success_rate))}%</span>`
                    : "<span>success_rate: n/a</span>"
                }
                <span>failures: ${escapeHtml(String(source.consecutive_failures || 0))}</span>
                ${
                  source.cooldown_until
                    ? `<span>until: ${escapeHtml(source.cooldown_until)}</span>`
                    : "<span>until: none</span>"
                }
              </div>
              ${
                Object.keys(source.recent_failure_categories || {}).length
                  ? `<p class="article-brief"><strong>failure_mix:</strong> ${escapeHtml(
                      Object.entries(source.recent_failure_categories)
                        .map(([key, value]) => `${key}=${value}`)
                        .join(", ")
                    )}</p>`
                  : ""
              }
            </article>
          `
        )
        .join("")
    : '<p class="muted">当前没有处于冷却、静默或维护中的来源。</p>';
}

function renderOperationsAlerts(sourceAlerts) {
  refs.operationsAlerts.innerHTML = sourceAlerts.length
    ? sourceAlerts
        .map(
          (item) => `
            <article class="publication-card operations-card">
              <header class="publication-head">
                <strong>${escapeHtml(item.source_name || item.source_id || "unknown source")}</strong>
                <span class="chip ${sourceAlertStatusClass(item.alert_status)}">${escapeHtml(sourceAlertStatusLabel(item.alert_status))}</span>
              </header>
              <div class="publication-meta">
                <span>${escapeHtml(item.created_at || "")}</span>
                ${item.severity ? `<span>${escapeHtml(item.severity)}</span>` : ""}
              </div>
              <p class="article-brief">${escapeHtml(item.title || "source alert")}</p>
            </article>
          `
        )
        .join("")
    : '<p class="muted">最近没有来源级告警。</p>';
}

function renderOperationsPublicationFailures(failures, pending) {
  const cards = [];
  if (failures.length) {
    cards.push(
      ...failures.map(
        (item) => `
          <article class="publication-card operations-card">
            <header class="publication-head">
              <strong>${escapeHtml(publicationTargetLabel(item.target))}</strong>
              <span class="chip warn">error</span>
            </header>
            <div class="publication-meta">
              <span>digest #${escapeHtml(String(item.digest_id || ""))}</span>
              <span>${escapeHtml(item.updated_at || item.created_at || "")}</span>
            </div>
            <p class="article-brief">${escapeHtml(item.message || "publication failed")}</p>
          </article>
        `
      )
    );
  }
  if (pending.length) {
    cards.push(
      ...pending.map(
        (item) => `
          <article class="publication-card operations-card">
            <header class="publication-head">
              <strong>${escapeHtml(publicationTargetLabel(item.target))}</strong>
              <span class="chip pending">pending</span>
            </header>
            <div class="publication-meta">
              <span>digest #${escapeHtml(String(item.digest_id || ""))}</span>
              <span>${escapeHtml(item.updated_at || item.created_at || "")}</span>
            </div>
            <p class="article-brief">${escapeHtml(item.message || "publication pending")}</p>
          </article>
        `
      )
    );
  }
  refs.operationsPublicationFailures.innerHTML = cards.length
    ? cards.join("")
    : '<p class="muted">最近没有发布失败或待完成记录。</p>';
}

function renderOperations(payload) {
  renderOperationsSummary(payload);
  renderOperationsHealth(payload);
  renderOperationsPipelineRuns(payload.pipeline_runs || []);
  renderOperationsSources(payload.source_runtime || []);
  renderOperationsAlerts(payload.source_alerts || []);
  renderOperationsPublicationFailures(
    payload.publication_failures || [],
    payload.pending_publications || []
  );
}

function renderSources(sources) {
  refs.sourcesList.innerHTML = sources
    .map(
      (source) => `
      <article class="source-item">
        <header class="publication-head">
          <strong>${source.name}</strong>
          <div class="chip-row compact">
            ${
              source.cooldown_active
                ? `<span class="chip ${source.cooldown_status === "blocked" ? "warn" : "pending"}">${escapeHtml(source.cooldown_status || "cooldown")}</span>`
                : '<span class="chip good">normal</span>'
            }
            ${source.maintenance_mode ? '<span class="chip pending">maintenance</span>' : ""}
            ${source.silenced_active ? '<span class="chip">silenced</span>' : ""}
            ${source.acknowledged_at ? '<span class="chip good">acknowledged</span>' : ""}
          </div>
        </header>
        <div class="chip-row">
          <span class="chip">${source.region}</span>
          <span class="chip">${source.language}</span>
          <span class="chip">${source.topic}</span>
          <span class="chip ${source.enabled ? "good" : "warn"}">${source.enabled ? "enabled" : "disabled"}</span>
        </div>
        <div class="publication-meta">
          <span>streak: ${escapeHtml(String(source.consecutive_failures || 0))}</span>
          <span>recovery_streak: ${escapeHtml(String(source.consecutive_successes || 0))}</span>
          ${
            source.recent_success_rate !== null && source.recent_success_rate !== undefined
              ? `<span>success_rate: ${escapeHtml(String(source.recent_success_rate))}%</span>`
              : "<span>success_rate: n/a</span>"
          }
          ${
            source.cooldown_until
              ? `<span>cooldown_until: ${escapeHtml(source.cooldown_until)}</span>`
              : "<span>cooldown_until: none</span>"
          }
          ${
            source.last_error_category
              ? `<span>last_error: ${escapeHtml(source.last_error_category)}</span>`
              : ""
          }
          ${
            source.last_http_status
              ? `<span>http: ${escapeHtml(String(source.last_http_status))}</span>`
              : ""
          }
        </div>
        <div class="publication-meta">
          ${
            source.last_error_at
              ? `<span>last_error_at: ${escapeHtml(source.last_error_at)}</span>`
              : "<span>last_error_at: none</span>"
          }
          ${
            source.last_success_at
              ? `<span>last_success_at: ${escapeHtml(source.last_success_at)}</span>`
              : "<span>last_success_at: none</span>"
          }
          ${
            source.last_recovered_at
              ? `<span>last_recovered_at: ${escapeHtml(source.last_recovered_at)}</span>`
              : "<span>last_recovered_at: none</span>"
          }
        </div>
        <div class="publication-meta">
          ${
            source.silenced_until
              ? `<span>silenced_until: ${escapeHtml(source.silenced_until)}</span>`
              : "<span>silenced_until: none</span>"
          }
          ${
            source.acknowledged_at
              ? `<span>acknowledged_at: ${escapeHtml(source.acknowledged_at)}</span>`
              : "<span>acknowledged_at: none</span>"
          }
        </div>
        ${
          source.ack_note
            ? `<p class="article-brief"><strong>ack_note:</strong> ${escapeHtml(source.ack_note)}</p>`
            : ""
        }
        ${
          Object.keys(source.recent_failure_categories || {}).length
            ? `<p class="article-brief"><strong>failure_mix:</strong> ${escapeHtml(
                Object.entries(source.recent_failure_categories)
                  .map(([key, value]) => `${key}=${value}`)
                  .join(", ")
              )}</p>`
            : ""
        }
        ${
          (source.recent_operations || []).length
            ? `<div class="source-ops-list">${source.recent_operations
                .map(
                  (event) => `
                    <div class="source-op">
                      <span class="chip ${event.status === "ok" ? "good" : event.status === "skipped" ? "" : "warn"}">${escapeHtml(
                        event.event_type
                      )}:${escapeHtml(event.status)}</span>
                      <span class="muted">${escapeHtml(event.created_at || "")}</span>
                      <div class="article-brief">${escapeHtml(event.article_title || event.message || "")}</div>
                    </div>
                  `
                )
                .join("")}</div>`
            : ""
        }
        <div class="article-actions">
          ${
            source.cooldown_active && !source.acknowledged_at
              ? `<button class="button ghost" data-action="ack-source-alert" data-source-id="${escapeAttribute(source.id)}">确认告警</button>`
              : ""
          }
          <button class="button ghost" data-action="${source.silenced_active ? "clear-source-snooze" : "snooze-source-alert"}" data-source-id="${escapeAttribute(source.id)}">${source.silenced_active ? "解除静默" : "静默1h"}</button>
          <button class="button ghost" data-action="toggle-source-maintenance" data-source-id="${escapeAttribute(source.id)}" data-enabled="${source.maintenance_mode ? "true" : "false"}">${source.maintenance_mode ? "退出维护" : "进入维护"}</button>
          ${
            source.cooldown_active
              ? `<button class="button ghost" data-action="reset-source-cooldown" data-source-id="${escapeAttribute(source.id)}">解除冷却</button>`
              : ""
          }
        </div>
      </article>
    `
    )
    .join("");
}

function renderDigest(payload) {
  const digestPayload = payload?.digest
    ? payload
    : payload?.payload?.digest
      ? payload.payload
      : payload;
  const digest = digestPayload?.digest || digestPayload?.payload;
  if (!digest) {
    refs.digestView.innerHTML = '<p class="muted">还没有生成日报。</p>';
    refs.digestPreviewView.innerHTML = '<p class="muted">还没有预览结果。点击“选稿预览”或生成日报后会显示这里。</p>';
    refs.digestEditorView.innerHTML = '<p class="muted">先生成预览或打开一份已保存的日报，编辑页才会出现。</p>';
    refs.digestHistoryView.innerHTML = '<p class="muted">冻结为编辑稿后，这里会显示版本历史和回滚入口。</p>';
    refs.publishPreviewView.innerHTML = '<p class="muted">打开一份日报或冻结编辑稿后，这里会显示目标平台最终预览。</p>';
    return;
  }
  state.currentDigest = digest;
  state.currentDigestPayload = digestPayload;
  const highlights = (digest.highlights || [])
    .map((item) => `<li>${escapeHtml(item)}</li>`)
    .join("");
  const sections = (digest.sections || [])
    .map(
      (section) => `
        <section>
          <h3>${escapeHtml(section.title)}</h3>
          <ul>${(section.items || []).map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>
        </section>
      `
    )
    .join("");
  const selectionPreview = (digestPayload?.selection_preview || [])
    .map(
      (item) => `
        <li>
          <strong>${escapeHtml(item.title || "")}</strong>
          <span class="muted"> · ${escapeHtml(item.source_name || "")} · score ${escapeHtml(String(item.rank_score || 0))}</span>
          <div class="article-brief">${escapeHtml((item.selection_reasons || []).join(", "))}</div>
        </li>
      `
    )
    .join("");
  refs.digestView.innerHTML = `
    <p class="eyebrow">Mode: ${escapeHtml(digestPayload?.generation_mode || payload?.generation_mode || "stored")}</p>
    <h2>${escapeHtml(digest.title || "AI 新闻日报")}</h2>
    <p class="article-summary">${escapeHtml(digest.overview || "")}</p>
    ${
      digestPayload?.selection_summary
        ? `<p class="article-brief">候选 ${escapeHtml(String(digestPayload.selection_summary.candidate_articles || 0))} · 去重后 ${escapeHtml(String(digestPayload.selection_summary.unique_candidates || 0))} · 已压掉重复 ${escapeHtml(String(digestPayload.selection_summary.duplicates_suppressed || 0))}</p>`
        : ""
    }
    ${highlights ? `<section><h3>今日要点</h3><ul>${highlights}</ul></section>` : ""}
    ${sections}
    ${selectionPreview ? `<section><h3>入选解释</h3><ul>${selectionPreview}</ul></section>` : ""}
    ${digest.closing ? `<p class="article-brief">${escapeHtml(digest.closing)}</p>` : ""}
  `;
  renderDigestPreview(digestPayload);
  renderDigestEditor(digestPayload);
  const digestId = digestPayload?.stored_digest?.id || null;
  if (digestId) {
    loadDigestHistory(digestId).catch((error) => logJob("load digest history failed", { error: error.message, digestId }));
  } else {
    refs.digestHistoryView.innerHTML = '<p class="muted">冻结为编辑稿后，这里会显示版本历史和回滚入口。</p>';
  }
  loadPublishPreview(digestId).catch((error) => logJob("load publish preview failed", { error: error.message, digestId }));
}

function decisionLabel(decision) {
  switch (decision) {
    case "selected":
      return "入选";
    case "suppressed":
      return "suppress";
    case "duplicate_secondary":
      return "重复副本";
    case "ranked_out":
      return "条数外";
    default:
      return decision || "unknown";
  }
}

function decisionStatusClass(decision) {
  if (decision === "selected") return "status-good";
  if (decision === "ranked_out" || decision === "duplicate_secondary") return "status-pending";
  return "status-warn";
}

function snapshotStatusClass(status) {
  if (status === "published") return "status-good";
  if (status === "draft") return "status-pending";
  return "";
}

function snapshotStatusLabel(status) {
  if (status === "published") return "已发布快照";
  if (status === "draft") return "编辑稿";
  return "预览";
}

function renderDigestPreview(payload) {
  const decisions = payload?.selection_decisions || [];
  const summary = payload?.selection_summary || null;
  if (!decisions.length) {
    refs.digestPreviewView.innerHTML = '<p class="muted">还没有预览结果。点击“选稿预览”或生成日报后会显示这里。</p>';
    return;
  }
  const summaryLine = summary
    ? `<p class="article-brief">候选 ${escapeHtml(String(summary.candidate_articles || 0))} · 入选 ${escapeHtml(String(summary.selected_count || 0))} · suppress ${escapeHtml(String(summary.editorially_suppressed || 0))} · 重复副本 ${escapeHtml(String(summary.duplicates_suppressed || 0))} · 条数外 ${escapeHtml(String(summary.ranked_out || 0))}</p>`
    : "";
  refs.digestPreviewView.innerHTML = `
    ${summaryLine}
    ${decisions
      .map(
        (item) => `
          <article class="archive-item">
            <div class="chip-row compact">
              <span class="chip ${decisionStatusClass(item.decision)}">${escapeHtml(decisionLabel(item.decision))}</span>
              <span class="chip">${escapeHtml(item.source_name || "")}</span>
              <span class="chip">score ${escapeHtml(String(item.rank_score || 0))}</span>
              ${item.must_include ? '<span class="chip">must_include</span>' : ""}
              ${item.is_pinned ? '<span class="chip">pinned</span>' : ""}
              ${item.is_suppressed ? '<span class="chip">suppressed</span>' : ""}
            </div>
            <strong>${escapeHtml(item.title || "")}</strong>
            <p class="muted">${escapeHtml(item.published_at || "")}</p>
            <p class="article-brief">${escapeHtml((item.selection_reasons || []).join(", "))}</p>
          </article>
        `
      )
      .join("")}
  `;
}

function renderDigestEditor(payload) {
  const snapshot = payload?.editor_snapshot || null;
  const items = snapshot?.items || [];
  if (!items.length) {
    refs.digestEditorView.innerHTML = '<p class="muted">先生成预览或打开一份已保存的日报，编辑页才会出现。</p>';
    return;
  }
  const summary = payload?.selection_summary || {};
  refs.digestEditorView.innerHTML = `
    <p class="article-brief">
      <span class="chip ${snapshotStatusClass(snapshot.snapshot_status)}">${escapeHtml(snapshotStatusLabel(snapshot.snapshot_status))}</span>
      <span class="chip">候选 ${escapeHtml(String(summary.candidate_articles || items.length))}</span>
      <span class="chip">入选 ${escapeHtml(String(summary.selected_count || 0))}</span>
      ${
        snapshot.last_published_at
          ? `<span class="chip">最近发布 ${escapeHtml(snapshot.last_published_at)}</span>`
          : ""
      }
    </p>
    ${items
      .map(
        (item) => `
          <article class="publication-card digest-editor-item" data-article-id="${item.article_id}">
            <header class="publication-head">
              <div>
                <strong>${escapeHtml(item.original_title || "")}</strong>
                <div class="publication-meta">
                  <span>${escapeHtml(item.source_name || "")}</span>
                  <span>${escapeHtml(item.published_at || "")}</span>
                </div>
              </div>
              <div class="chip-row compact">
                <span class="chip ${decisionStatusClass(item.base_decision === "selected" || item.selected ? "selected" : item.base_decision)}">${escapeHtml(decisionLabel(item.base_decision || "selected"))}</span>
                <span class="chip">score ${escapeHtml(String(item.rank_score || 0))}</span>
                ${item.must_include ? '<span class="chip">must_include</span>' : ""}
                ${item.is_pinned ? '<span class="chip">pinned</span>' : ""}
              </div>
            </header>
            <div class="form-grid digest-editor-grid">
              <label class="check-label">
                <input data-role="selected" type="checkbox" ${item.selected ? "checked" : ""} />
                纳入发布稿
              </label>
              <label>
                排序
                <input data-role="manual-rank" type="number" min="1" max="999" value="${escapeAttribute(String(item.manual_rank || ""))}" />
              </label>
              <label>
                分组标题
                <input data-role="section-override" type="text" placeholder="${escapeAttribute(item.default_section || "")}" value="${escapeAttribute(item.section_override || "")}" />
              </label>
            </div>
            <label>
              发布标题
              <input data-role="publish-title-override" type="text" placeholder="${escapeAttribute(item.original_title || "")}" value="${escapeAttribute(item.publish_title_override || "")}" />
            </label>
            <label>
              发布摘要
              <textarea data-role="publish-summary-override" placeholder="${escapeAttribute(item.original_summary || "")}">${escapeHtml(item.publish_summary_override || "")}</textarea>
            </label>
            <p class="article-brief"><strong>原因：</strong>${escapeHtml((item.selection_reasons || []).join(", ") || "none")}</p>
          </article>
        `
      )
      .join("")}
  `;
}

function renderDigestHistory(payload) {
  const versions = payload?.versions || [];
  const currentVersion = payload?.current_version || 0;
  if (!versions.length) {
    refs.digestHistoryView.innerHTML = '<p class="muted">当前还没有可用的编辑版本历史。</p>';
    return;
  }
  refs.digestHistoryView.innerHTML = versions
    .map((item) => {
      const publicationRecords = item.publication_records || [];
      return `
        <article class="publication-card">
          <header class="publication-head">
            <div>
              <strong>v${escapeHtml(String(item.version || 0))}</strong>
              <div class="publication-meta">
                <span>${escapeHtml(item.created_at || "")}</span>
                <span>created_by: ${escapeHtml(item.created_by || "system")}</span>
                <span>updated_by: ${escapeHtml(item.updated_by || item.created_by || "system")}</span>
              </div>
            </div>
            <div class="chip-row compact">
              ${item.version === currentVersion ? '<span class="chip status-good">当前版本</span>' : ""}
              ${item.action ? `<span class="chip">${escapeHtml(item.action)}</span>` : ""}
              ${item.restored_from_version ? `<span class="chip">from v${escapeHtml(String(item.restored_from_version))}</span>` : ""}
            </div>
          </header>
          <p class="article-brief">${escapeHtml(item.change_summary || "no change summary")}</p>
          ${
            publicationRecords.length
              ? `<div class="chip-row">${publicationRecords
                  .map(
                    (record) =>
                      `<span class="chip ${publicationStatusClass(record.status)}">${escapeHtml(publicationTargetLabel(record.target))} · ${escapeHtml(publicationStatusLabel(record.status))}${record.digest_changed_after_publish ? " · stale" : ""}</span>`
                  )
                  .join("")}</div>`
              : '<p class="muted">这一版还没有发布记录。</p>'
          }
          ${
            item.version !== currentVersion
              ? `<div class="article-actions"><button class="button ghost" data-action="rollback-digest-version" data-version="${item.version}">回滚到这一版</button></div>`
              : ""
          }
        </article>
      `;
    })
    .join("");
}

function renderPublishPreview(payload) {
  const targets = payload?.preview_targets?.targets || [];
  if (!targets.length) {
    refs.publishPreviewView.innerHTML = '<p class="muted">选择一份日报后，这里会显示目标平台最终预览。</p>';
    return;
  }
  refs.publishPreviewView.innerHTML = targets
    .map((entry) => {
      const target = entry.target;
      const preview = entry.preview || {};
      if (target === "telegram") {
        return `
          <article class="publication-card">
            <header class="publication-head">
              <strong>Telegram</strong>
              <span class="chip">chunks ${escapeHtml(String((preview.chunks || []).length || 0))}</span>
            </header>
            <pre class="terminal">${escapeHtml(preview.text || "")}</pre>
          </article>
        `;
      }
      if (target === "feishu") {
        return `
          <article class="publication-card">
            <header class="publication-head">
              <strong>飞书</strong>
              <span class="chip">${escapeHtml(preview.card_title || "interactive card")}</span>
            </header>
            <p class="article-brief"><strong>文本消息</strong></p>
            <pre class="terminal">${escapeHtml(preview.text || "")}</pre>
          </article>
        `;
      }
      if (target === "static_site") {
        return `
          <article class="publication-card">
            <header class="publication-head">
              <strong>静态站点</strong>
              <span class="chip">HTML</span>
            </header>
            <iframe class="preview-frame" sandbox="" srcdoc="${escapeAttribute(preview.html || "")}"></iframe>
          </article>
        `;
      }
      if (target === "wechat") {
        const wechatDocument = `
          <!doctype html>
          <html lang="zh-CN"><head><meta charset="utf-8"><style>
          body{font-family:-apple-system,BlinkMacSystemFont,'PingFang SC','Noto Sans SC',sans-serif;padding:18px;color:#1b1711;background:#fff;}
          h1{font-size:22px;line-height:1.35;margin:0 0 12px;}
          .digest{color:#6f665b;font-size:14px;margin-bottom:14px;}
          img{max-width:100%;}
          </style></head><body>
          <h1>${escapeHtml(preview.title || "")}</h1>
          <p class="digest">${escapeHtml(preview.digest || "")}</p>
          ${preview.content_html || ""}
          </body></html>
        `;
        return `
          <article class="publication-card">
            <header class="publication-head">
              <strong>公众号</strong>
              <span class="chip">${escapeHtml(preview.content_source_url || "no source link")}</span>
            </header>
            <iframe class="preview-frame" sandbox="" srcdoc="${escapeAttribute(wechatDocument)}"></iframe>
          </article>
        `;
      }
      return "";
    })
    .join("");
}

function renderArchive(digests) {
  refs.digestArchive.innerHTML = digests.length
    ? digests
        .map(
          (item) => `
          <article class="archive-item" data-digest-id="${item.id}">
            <strong>${escapeHtml(item.title)}</strong>
            <p class="muted">${escapeHtml(item.generated_at)} · ${escapeHtml(item.region)} · ${item.article_count} 篇 · v${escapeHtml(String(item.current_version || 1))}</p>
            ${
              item.payload?.editor_snapshot?.snapshot_status
                ? `<div class="chip-row compact"><span class="chip ${snapshotStatusClass(item.payload.editor_snapshot.snapshot_status)}">${escapeHtml(snapshotStatusLabel(item.payload.editor_snapshot.snapshot_status))}</span><span class="chip">${escapeHtml(item.updated_by || item.created_by || "system")}</span></div>`
                : ""
            }
            <button class="button ghost" data-action="open-digest" data-digest-id="${item.id}">查看</button>
          </article>
        `
        )
        .join("")
    : '<p class="muted">还没有存档日报。</p>';
}

function publicationTargetLabel(target) {
  const labels = {
    telegram: "Telegram",
    feishu: "飞书",
    wechat: "公众号",
    static_site: "静态站点",
  };
  return labels[target] || target || "unknown";
}

function publicationStatusLabel(status) {
  const labels = {
    ok: "成功",
    pending: "处理中",
    error: "失败",
    skipped: "跳过",
  };
  return labels[status] || status || "unknown";
}

function publicationStatusClass(status) {
  if (status === "ok") return "good";
  if (status === "pending") return "pending";
  if (status === "error") return "warn";
  return "";
}

function publicationPrimaryLink(publication) {
  const response = publication.response_payload || {};
  const statusQuery = response.status_query || {};
  const articleDetail = statusQuery.article_detail || {};
  const items = Array.isArray(articleDetail.item) ? articleDetail.item : [];
  if (items[0]?.article_url) {
    return items[0].article_url;
  }
  if (publication.target === "static_site" && response.base_url) {
    return `${String(response.base_url).replace(/\/$/, "")}/`;
  }
  return "";
}

function renderPublications(publications) {
  refs.publicationsList.innerHTML = publications.length
    ? publications
        .map((publication) => {
          const link = publicationPrimaryLink(publication);
          return `
            <article class="publication-card">
              <header class="publication-head">
                <div class="chip-row compact">
                  <span class="chip">${escapeHtml(publicationTargetLabel(publication.target))}</span>
                  <span class="chip ${publicationStatusClass(publication.status)}">${escapeHtml(publicationStatusLabel(publication.status))}</span>
                  ${
                    publication.digest_snapshot_version
                      ? `<span class="chip">v${escapeHtml(String(publication.digest_snapshot_version))}</span>`
                      : ""
                  }
                  ${
                    publication.digest_changed_after_publish
                      ? '<span class="chip warn">发布后已变更</span>'
                      : ""
                  }
                </div>
                <span class="muted">${escapeHtml(publication.updated_at || publication.created_at || "")}</span>
              </header>
              <p class="publication-message">${escapeHtml(publication.message || "无附加说明")}</p>
              <div class="publication-meta">
                <span>记录 #${publication.id}</span>
                ${publication.digest_id ? `<span>日报 #${publication.digest_id}</span>` : "<span>未绑定日报</span>"}
                ${publication.external_id ? `<span>ID: ${escapeHtml(publication.external_id)}</span>` : ""}
              </div>
              ${
                link
                  ? `<p class="article-brief"><a class="article-link" href="${escapeAttribute(link)}" target="_blank" rel="noreferrer">查看发布结果</a></p>`
                  : ""
              }
            </article>
          `;
        })
        .join("")
    : '<p class="muted">当前筛选下还没有发布记录。</p>';
}

function articleChips(article) {
  const chips = [
    article.region,
    article.language,
    article.source_name,
    article.extraction_status || "pending",
    article.llm_status || "pending",
  ];
  if (article.is_pinned) chips.push("pinned");
  if (article.must_include) chips.push("must_include");
  if (article.is_suppressed) chips.push("suppressed");
  if (article.is_hidden) chips.push("hidden");
  if ((article.duplicate_count || 1) > 1) {
    chips.push(article.is_duplicate_primary ? `primary x${article.duplicate_count}` : `duplicate -> #${article.duplicate_primary_id}`);
  }
  return chips
    .filter(Boolean)
    .map((chip) => `<span class="chip">${escapeHtml(String(chip))}</span>`)
    .join("");
}

function renderArticles(articles) {
  state.currentArticles = articles;
  refs.articlesList.innerHTML = articles.length
    ? articles
        .map(
          (article) => `
          <article class="article-card" data-article-id="${article.id}" data-is-pinned="${article.is_pinned}" data-is-hidden="${article.is_hidden}" data-is-suppressed="${article.is_suppressed}">
            <header>
              <div>
                <h3>${escapeHtml(article.display_title_zh || article.title)}</h3>
                <div class="article-meta">
                  <span>${escapeHtml(article.published_at)}</span>
                  <span>${escapeHtml(article.source_name)}</span>
                  <span>${escapeHtml(article.region)}</span>
                </div>
              </div>
              <div class="chip-row">${articleChips(article)}</div>
            </header>
            <p class="article-summary">${escapeHtml(article.compact_summary_zh || article.display_summary_zh || article.summary || "")}</p>
            ${
              article.display_brief_zh
                ? `<p class="article-brief"><strong>为什么重要：</strong>${escapeHtml(article.display_brief_zh)}</p>`
                : ""
            }
            ${
              (article.duplicate_count || 1) > 1
                ? `<p class="article-brief"><strong>重复簇：</strong>${escapeHtml(article.duplicate_group || "unknown")} · ${
                    article.is_duplicate_primary
                      ? "当前主记录"
                      : `主记录 #${escapeHtml(String(article.duplicate_primary_id || ""))} · ${escapeHtml(article.duplicate_primary_title || "")}`
                  }</p>`
                : ""
            }
            <p class="article-brief">
              <a class="article-link" href="${escapeAttribute(article.url)}" target="_blank" rel="noreferrer">查看原文</a>
            </p>
            <label>
              编辑备注
              <textarea data-role="note">${escapeHtml(article.editorial_note || "")}</textarea>
            </label>
            <div class="article-actions">
              <button class="button ghost" data-action="toggle-pin">${article.is_pinned ? "取消置顶" : "置顶"}</button>
              <button class="button ghost" data-action="toggle-must-include">${article.must_include ? "取消必选" : "设为必选"}</button>
              <button class="button ghost" data-action="toggle-suppress">${article.is_suppressed ? "取消 suppress" : "suppress"}</button>
              <button class="button ghost" data-action="toggle-hide">${article.is_hidden ? "取消隐藏" : "隐藏"}</button>
              ${
                (article.duplicate_count || 1) > 1 && !article.is_duplicate_primary
                  ? `<button class="button ghost" data-action="set-duplicate-primary">设为主记录</button>`
                  : ""
              }
              <button class="button secondary" data-action="save-note">保存备注</button>
            </div>
          </article>
        `
        )
        .join("")
    : '<p class="muted">当前筛选下没有文章。</p>';
}

function escapeHtml(value) {
  return String(value || "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function escapeAttribute(value) {
  return escapeHtml(value);
}

function getPublishTargets() {
  return refs.publishTargetInputs
    .filter((input) => input.checked)
    .map((input) => input.value);
}

function setSelectedDigestId(digestId) {
  state.selectedDigestId = digestId || null;
  refs.publicationsHint.textContent = state.selectedDigestId
    ? `当前仅显示日报 #${state.selectedDigestId} 的发布记录。`
    : "展示最近的发布记录；打开某份日报后会自动筛选到对应记录。";
  refs.clearPublicationDigestFilterButton.style.display = state.selectedDigestId ? "inline-flex" : "none";
}

function buildExtractionQuery() {
  const filters = getFilters();
  const query = new URLSearchParams({
    region: filters.region,
    since_hours: String(filters.since_hours),
    limit: String(Math.min(40, filters.limit)),
    include_hidden: "true",
  });
  if (refs.extractionStatusFilter.value) {
    query.set("extraction_status", refs.extractionStatusFilter.value);
  }
  if (refs.extractionErrorCategoryFilter.value) {
    query.set("extraction_error_category", refs.extractionErrorCategoryFilter.value);
  }
  if (refs.extractionDueOnlyCheckbox.checked) {
    query.set("due_only", "true");
  }
  return query;
}

function buildPublicationQuery() {
  const query = new URLSearchParams({
    limit: "20",
  });
  if (state.selectedDigestId) {
    query.set("digest_id", String(state.selectedDigestId));
  }
  if (refs.publicationTargetFilter.value) {
    query.set("target", refs.publicationTargetFilter.value);
  }
  if (refs.publicationStatusFilter.value) {
    query.set("status", refs.publicationStatusFilter.value);
  }
  return query;
}

function renderExtractionOpsSummary(stats) {
  const chips = [
    ["throttled", stats.throttled_extractions || 0, "pending"],
    ["blocked", stats.blocked_extractions || 0, "warn"],
    ["temporary_error", stats.temporary_extraction_errors || 0, ""],
    ["permanent_error", stats.permanent_extraction_errors || 0, "warn"],
    ["scheduled_retries", stats.scheduled_extraction_retries || 0, "pending"],
  ];
  refs.extractionOpsSummary.innerHTML = chips
    .map(
      ([label, value, klass]) =>
        `<span class="chip ${klass}">${escapeHtml(String(label))}: ${escapeHtml(String(value))}</span>`
    )
    .join("");
}

function extractionStatusClass(status) {
  if (status === "ready") return "good";
  if (status === "throttled") return "pending";
  if (status === "blocked" || status === "permanent_error") return "warn";
  return "";
}

function sourceAlertStatusClass(status) {
  if (status === "recovered") return "good";
  if (status === "sent") return "warn";
  if (status === "delivery_error" || status === "recovery_delivery_error") return "pending";
  return "";
}

function sourceAlertStatusLabel(status) {
  const labels = {
    sent: "active",
    delivery_error: "delivery_error",
    recovered: "recovered",
    recovery_delivery_error: "recovery_delivery_error",
  };
  return labels[status] || status || "unknown";
}

function retryDueLabel(article) {
  if (article.extraction_status === "pending") {
    return "pending";
  }
  return article.extraction_next_retry_at || "none";
}

function renderExtractionOps(articles) {
  refs.extractionOpsList.innerHTML = articles.length
    ? articles
        .map(
          (article) => `
            <article class="publication-card" data-extraction-article-id="${article.id}">
              <header class="publication-head">
                <div>
                  <strong>${escapeHtml(article.display_title_zh || article.title)}</strong>
                  <div class="publication-meta">
                    <span>${escapeHtml(article.source_name || "")}</span>
                    <span>${escapeHtml(article.published_at || "")}</span>
                  </div>
                </div>
                <div class="chip-row compact">
                  <span class="chip ${extractionStatusClass(article.extraction_status)}">${escapeHtml(article.extraction_status || "pending")}</span>
                  ${
                    article.extraction_error_category
                      ? `<span class="chip">${escapeHtml(article.extraction_error_category)}</span>`
                      : ""
                  }
                </div>
              </header>
              <div class="publication-meta">
                <span>attempts: ${escapeHtml(String(article.extraction_attempts || 0))}</span>
                <span>next_retry_at: ${escapeHtml(retryDueLabel(article))}</span>
                ${
                  article.extraction_last_http_status
                    ? `<span>http: ${escapeHtml(String(article.extraction_last_http_status))}</span>`
                    : ""
                }
              </div>
              <p class="article-summary">${escapeHtml(article.compact_summary_zh || article.display_summary_zh || article.summary || "")}</p>
              <div class="article-actions">
                <button class="button ghost" data-action="retry-extraction">立即重试</button>
                <a class="article-link" href="${escapeAttribute(article.url)}" target="_blank" rel="noreferrer">查看原文</a>
              </div>
            </article>
          `
        )
        .join("")
    : '<p class="muted">当前筛选下没有需要关注的抽取记录。</p>';
}

function renderSourceAlerts(sourceAlerts) {
  refs.sourceAlertsList.innerHTML = sourceAlerts.length
    ? sourceAlerts
        .map(
          (item) => `
            <article class="publication-card">
              <header class="publication-head">
                <div>
                  <strong>${escapeHtml(item.source_name || item.source_id || "unknown source")}</strong>
                  <div class="publication-meta">
                    <span>${escapeHtml(item.created_at || "")}</span>
                    <span>${escapeHtml(item.alert_key || "")}</span>
                  </div>
                </div>
                <div class="chip-row compact">
                  <span class="chip ${sourceAlertStatusClass(item.alert_status)}">${escapeHtml(sourceAlertStatusLabel(item.alert_status))}</span>
                  ${item.severity ? `<span class="chip">${escapeHtml(item.severity)}</span>` : ""}
                  ${(item.targets || [])
                    .map(
                      (target) =>
                        `<span class="chip">${escapeHtml(target.target || "target")}:${escapeHtml(target.status || "unknown")}</span>`
                    )
                    .join("")}
                </div>
              </header>
              <p class="publication-message">${escapeHtml(item.title || "source alert")}</p>
              <p class="article-brief">${escapeHtml(item.message || "")}</p>
            </article>
          `
        )
        .join("")
    : '<p class="muted">最近还没有来源级告警历史。</p>';
}

async function loadStats() {
  const stats = await fetchJson("/admin/stats", { headers: adminHeaders() });
  renderStats(stats);
}

async function loadOperations() {
  const payload = await fetchJson("/admin/operations", {
    headers: adminHeaders(),
  });
  renderOperations(payload);
}

async function loadSources() {
  const payload = await fetchJson("/admin/sources", { headers: adminHeaders() });
  renderSources(payload.sources || []);
}

async function loadArticles() {
  const filters = getFilters();
  const query = new URLSearchParams({
    region: filters.region,
    since_hours: String(filters.since_hours),
    limit: String(filters.limit),
    include_hidden: "true",
  });
  const payload = await fetchJson(`/admin/articles?${query.toString()}`, {
    headers: adminHeaders(),
  });
  renderArticles(payload.articles || []);
}

async function loadDigests() {
  const payload = await fetchJson("/admin/digests?limit=12", {
    headers: adminHeaders(),
  });
  renderArchive(payload.digests || []);
  if (payload.digests && payload.digests[0]) {
    if (state.selectedDigestId) {
      const selected = payload.digests.find((item) => item.id === state.selectedDigestId);
      renderDigest(selected || payload.digests[0]);
      return;
    }
    renderDigest(payload.digests[0]);
  }
}

async function loadDigestHistory(digestId = null) {
  const resolvedDigestId =
    digestId || state.currentDigestPayload?.stored_digest?.id || state.selectedDigestId || null;
  if (!resolvedDigestId) {
    refs.digestHistoryView.innerHTML = '<p class="muted">冻结为编辑稿后，这里会显示版本历史和回滚入口。</p>';
    return;
  }
  const payload = await fetchJson(`/admin/digests/${resolvedDigestId}/history?limit=20`, {
    headers: adminHeaders(),
  });
  renderDigestHistory(payload);
}

async function loadPublications() {
  const payload = await fetchJson(`/admin/publications?${buildPublicationQuery().toString()}`, {
    headers: adminHeaders(),
  });
  renderPublications(payload.publications || []);
}

async function loadPublishPreview(digestId = null) {
  const filters = getFilters();
  const resolvedDigestId =
    digestId || state.currentDigestPayload?.stored_digest?.id || state.selectedDigestId || null;
  const targets = getPublishTargets();
  const payload = await fetchJson("/admin/publish/preview", {
    method: "POST",
    headers: adminHeaders(),
    body: JSON.stringify({
      digest_id: resolvedDigestId,
      region: filters.region,
      since_hours: filters.since_hours,
      limit: filters.limit,
      use_llm: true,
      targets: targets.length ? targets : null,
    }),
  });
  renderPublishPreview(payload);
}

async function loadExtractionOps() {
  const payload = await fetchJson(`/admin/articles?${buildExtractionQuery().toString()}`, {
    headers: adminHeaders(),
  });
  renderExtractionOps(payload.articles || []);
}

async function loadSourceAlerts() {
  const payload = await fetchJson("/admin/source-alerts?limit=20", {
    headers: adminHeaders(),
  });
  renderSourceAlerts(payload.source_alerts || []);
}

async function acknowledgeSourceAlert(sourceIds, note = "") {
  const payload = await fetchJson("/admin/sources/acknowledge", {
    method: "POST",
    headers: adminHeaders(),
    body: JSON.stringify({
      source_ids: sourceIds,
      note,
    }),
  });
  logJob("acknowledge source alerts", payload);
  await refreshAll();
}

async function snoozeSourceAlerts(sourceIds, minutes = 60, clear = false) {
  const payload = await fetchJson("/admin/sources/snooze", {
    method: "POST",
    headers: adminHeaders(),
    body: JSON.stringify({
      source_ids: sourceIds,
      minutes,
      clear,
    }),
  });
  logJob(clear ? "clear source alert snooze" : "snooze source alerts", payload);
  await refreshAll();
}

async function setSourceMaintenance(sourceIds, enabled) {
  const payload = await fetchJson("/admin/sources/maintenance", {
    method: "POST",
    headers: adminHeaders(),
    body: JSON.stringify({
      source_ids: sourceIds,
      enabled,
    }),
  });
  logJob(enabled ? "enable source maintenance" : "disable source maintenance", payload);
  await refreshAll();
}

async function refreshPublications() {
  const payload = await fetchJson("/admin/publications/refresh", {
    method: "POST",
    headers: adminHeaders(),
    body: JSON.stringify({
      digest_id: state.selectedDigestId,
      target: refs.publicationTargetFilter.value || null,
      limit: 20,
      only_pending: refs.publicationOnlyPendingCheckbox.checked,
    }),
  });
  logJob("refresh publications", payload);
  await loadPublications();
  await loadStats();
}

async function refreshAll() {
  try {
    await Promise.all([
      loadOperations(),
      loadStats(),
      loadSources(),
      loadArticles(),
      loadDigests(),
      loadPublications(),
      loadExtractionOps(),
      loadSourceAlerts(),
    ]);
  } catch (error) {
    logJob("refresh failed", { error: error.message });
  }
}

async function resetSourceCooldowns(sourceIds = null) {
  const payload = await fetchJson("/admin/sources/cooldowns/reset", {
    method: "POST",
    headers: adminHeaders(),
    body: JSON.stringify({
      source_ids: sourceIds,
      active_only: sourceIds ? false : true,
    }),
  });
  logJob("reset source cooldowns", payload);
  await refreshAll();
}

async function runIngest() {
  const filters = getFilters();
  const payload = await fetchJson("/admin/ingest", {
    method: "POST",
    headers: adminHeaders(),
    body: JSON.stringify({
      max_items_per_source: filters.max_items_per_source,
    }),
  });
  logJob("ingest", payload);
  await refreshAll();
}

async function runEnrich() {
  const filters = getFilters();
  const payload = await fetchJson("/admin/enrich", {
    method: "POST",
    headers: adminHeaders(),
    body: JSON.stringify({
      since_hours: filters.since_hours,
      limit: filters.limit,
      force: false,
    }),
  });
  logJob("enrich", payload);
  await refreshAll();
}

async function runExtract() {
  const filters = getFilters();
  const payload = await fetchJson("/admin/extract", {
    method: "POST",
    headers: adminHeaders(),
    body: JSON.stringify({
      since_hours: filters.since_hours,
      limit: filters.limit,
      force: false,
    }),
  });
  logJob("extract", payload);
  await refreshAll();
}

async function retryExtractions(options = {}) {
  const filters = getFilters();
  const payload = await fetchJson("/admin/extract/retry", {
    method: "POST",
    headers: adminHeaders(),
    body: JSON.stringify({
      since_hours: filters.since_hours,
      limit: Math.min(40, filters.limit),
      extraction_status: refs.extractionStatusFilter.value || null,
      extraction_error_category: refs.extractionErrorCategoryFilter.value || null,
      due_only: refs.extractionDueOnlyCheckbox.checked,
      ...options,
    }),
  });
  logJob("retry extractions", payload);
  await refreshAll();
}

async function runDigest() {
  const filters = getFilters();
  const payload = await fetchJson("/admin/digests/generate", {
    method: "POST",
    headers: adminHeaders(),
    body: JSON.stringify({
      region: filters.region,
      since_hours: filters.since_hours,
      limit: filters.limit,
      use_llm: true,
      persist: true,
    }),
  });
  logJob("digest", payload);
  renderDigest(payload);
  await refreshAll();
}

async function previewDigest() {
  const filters = getFilters();
  const payload = await fetchJson("/admin/digests/preview", {
    method: "POST",
    headers: adminHeaders(),
    body: JSON.stringify({
      region: filters.region,
      since_hours: filters.since_hours,
      limit: filters.limit,
      use_llm: true,
      persist: false,
    }),
  });
  logJob("digest preview", payload);
  renderDigest(payload);
}

function collectDigestEditorItems() {
  return Array.from(refs.digestEditorView.querySelectorAll(".digest-editor-item")).map((card) => {
    const articleId = Number(card.dataset.articleId);
    const selected = card.querySelector('[data-role="selected"]').checked;
    const manualRankRaw = card.querySelector('[data-role="manual-rank"]').value.trim();
    return {
      article_id: articleId,
      selected,
      manual_rank: manualRankRaw ? Number(manualRankRaw) : null,
      section_override: card.querySelector('[data-role="section-override"]').value.trim() || null,
      publish_title_override:
        card.querySelector('[data-role="publish-title-override"]').value.trim() || null,
      publish_summary_override:
        card.querySelector('[data-role="publish-summary-override"]').value.trim() || null,
    };
  });
}

async function freezeDigestSnapshot() {
  const filters = getFilters();
  const editorMeta = getDigestEditorMeta();
  const payload = await fetchJson("/admin/digests/snapshot", {
    method: "POST",
    headers: adminHeaders(),
    body: JSON.stringify({
      region: filters.region,
      since_hours: filters.since_hours,
      limit: filters.limit,
      use_llm: true,
      article_ids: (state.currentDigestPayload?.articles || []).map((item) => item.id),
      editor_items: collectDigestEditorItems(),
      actor: editorMeta.actor,
      change_summary: editorMeta.change_summary,
    }),
  });
  logJob("freeze digest snapshot", payload);
  renderDigest(payload);
  setSelectedDigestId(payload.stored_digest?.id || payload.digest?.stored_digest?.id || null);
  await refreshAll();
}

async function saveDigestEditor() {
  const digestId =
    state.currentDigestPayload?.stored_digest?.id || state.selectedDigestId || null;
  if (!digestId) {
    throw new Error("请先冻结为编辑稿，再保存编辑修改");
  }
  const editorMeta = getDigestEditorMeta();
  const payload = await fetchJson(`/admin/digests/${digestId}/editor`, {
    method: "PATCH",
    headers: adminHeaders(),
    body: JSON.stringify({
      editor_items: collectDigestEditorItems(),
      actor: editorMeta.actor,
      change_summary: editorMeta.change_summary,
    }),
  });
  logJob("save digest editor", payload);
  renderDigest(payload);
  setSelectedDigestId(payload.stored_digest?.id || digestId);
  await refreshAll();
}

async function rollbackDigestVersion(version) {
  const digestId =
    state.currentDigestPayload?.stored_digest?.id || state.selectedDigestId || null;
  if (!digestId) {
    throw new Error("请先打开一份已保存的日报");
  }
  const editorMeta = getDigestEditorMeta();
  const payload = await fetchJson(`/admin/digests/${digestId}/rollback`, {
    method: "POST",
    headers: adminHeaders(),
    body: JSON.stringify({
      version,
      actor: editorMeta.actor,
      change_summary: editorMeta.change_summary,
    }),
  });
  logJob("rollback digest version", payload);
  renderDigest(payload);
  setSelectedDigestId(payload.stored_digest?.id || digestId);
  await refreshAll();
}

async function runPipeline() {
  const filters = getFilters();
  const payload = await fetchJson("/admin/pipeline", {
    method: "POST",
    headers: adminHeaders(),
    body: JSON.stringify({
      region: filters.region,
      since_hours: filters.since_hours,
      limit: filters.limit,
      max_items_per_source: filters.max_items_per_source,
      use_llm: true,
      persist: true,
      export: true,
      publish: false,
    }),
  });
  logJob("pipeline", payload);
  if (payload.digest) {
    renderDigest(payload.digest);
  }
  await refreshAll();
}

async function runPublish() {
  const filters = getFilters();
  const targets = getPublishTargets();
  const digestId =
    state.currentDigestPayload?.stored_digest?.id || state.selectedDigestId || null;
  const payload = await fetchJson("/admin/publish", {
    method: "POST",
    headers: adminHeaders(),
    body: JSON.stringify({
      digest_id: digestId,
      region: filters.region,
      since_hours: filters.since_hours,
      limit: filters.limit,
      use_llm: true,
      persist: true,
      export: targets.includes("static_site"),
      targets: targets.length ? targets : null,
      wechat_submit: refs.wechatSubmitCheckbox.checked,
    }),
  });
  logJob("publish", payload);
  if (payload.digest) {
    renderDigest(payload.digest);
    setSelectedDigestId(payload.digest.stored_digest?.id || state.selectedDigestId);
  }
  await refreshAll();
}

async function updateArticle(articleId, patch) {
  const payload = await fetchJson(`/admin/articles/${articleId}`, {
    method: "PATCH",
    headers: adminHeaders(),
    body: JSON.stringify(patch),
  });
  logJob("curation", payload);
  await loadArticles();
  await loadStats();
  await previewDigest().catch((error) => logJob("digest preview failed", { error: error.message }));
}

async function setDuplicatePrimary(articleId) {
  const payload = await fetchJson(`/admin/articles/${articleId}/duplicate-primary`, {
    method: "POST",
    headers: adminHeaders(),
  });
  logJob("duplicate primary", payload);
  await loadArticles();
  await loadDigests();
  await previewDigest().catch((error) => logJob("digest preview failed", { error: error.message }));
}

refs.saveTokenButton.addEventListener("click", () => {
  state.token = refs.adminToken.value.trim();
  localStorage.setItem("ainews_admin_token", state.token);
  logJob("token", { saved: Boolean(state.token) });
});
refs.digestEditorActorInput.addEventListener("change", () => {
  state.editorActor = refs.digestEditorActorInput.value.trim();
  localStorage.setItem("ainews_digest_editor_actor", state.editorActor);
});

refs.refreshAllButton.addEventListener("click", refreshAll);
refs.refreshSourcesButton.addEventListener("click", () =>
  loadSources().catch((error) => logJob("load sources failed", { error: error.message }))
);
refs.resetSourceCooldownsButton.addEventListener("click", () =>
  resetSourceCooldowns().catch((error) => logJob("reset source cooldowns failed", { error: error.message }))
);
refs.ingestButton.addEventListener("click", () => runIngest().catch((error) => logJob("ingest failed", { error: error.message })));
refs.extractButton.addEventListener("click", () => runExtract().catch((error) => logJob("extract failed", { error: error.message })));
refs.enrichButton.addEventListener("click", () => runEnrich().catch((error) => logJob("enrich failed", { error: error.message })));
refs.digestPreviewButton.addEventListener("click", () => previewDigest().catch((error) => logJob("digest preview failed", { error: error.message })));
refs.freezeDigestButton.addEventListener("click", () => freezeDigestSnapshot().catch((error) => logJob("freeze digest snapshot failed", { error: error.message })));
refs.saveDigestEditorButton.addEventListener("click", () => saveDigestEditor().catch((error) => logJob("save digest editor failed", { error: error.message })));
refs.refreshDigestHistoryButton.addEventListener("click", () => loadDigestHistory().catch((error) => logJob("load digest history failed", { error: error.message })));
refs.refreshPublishPreviewButton.addEventListener("click", () => loadPublishPreview().catch((error) => logJob("load publish preview failed", { error: error.message })));
refs.digestButton.addEventListener("click", () => runDigest().catch((error) => logJob("digest failed", { error: error.message })));
refs.pipelineButton.addEventListener("click", () => runPipeline().catch((error) => logJob("pipeline failed", { error: error.message })));
refs.publishButton.addEventListener("click", () => runPublish().catch((error) => logJob("publish failed", { error: error.message })));
refs.refreshPublicationsButton.addEventListener("click", () =>
  refreshPublications().catch((error) => logJob("refresh publications failed", { error: error.message }))
);
refs.refreshExtractionOpsButton.addEventListener("click", () =>
  loadExtractionOps().catch((error) => logJob("load extraction ops failed", { error: error.message }))
);
refs.retryExtractionSelectionButton.addEventListener("click", () =>
  retryExtractions().catch((error) => logJob("retry extractions failed", { error: error.message }))
);
refs.refreshSourceAlertsButton.addEventListener("click", () =>
  loadSourceAlerts().catch((error) => logJob("load source alerts failed", { error: error.message }))
);
refs.clearPublicationDigestFilterButton.addEventListener("click", () => {
  setSelectedDigestId(null);
  loadPublications().catch((error) => logJob("load publications failed", { error: error.message }));
});
refs.publicationTargetFilter.addEventListener("change", () =>
  loadPublications().catch((error) => logJob("load publications failed", { error: error.message }))
);
refs.publicationStatusFilter.addEventListener("change", () =>
  loadPublications().catch((error) => logJob("load publications failed", { error: error.message }))
);
refs.publishTargetInputs.forEach((input) =>
  input.addEventListener("change", () =>
    loadPublishPreview().catch((error) => logJob("load publish preview failed", { error: error.message }))
  )
);
refs.extractionStatusFilter.addEventListener("change", () =>
  loadExtractionOps().catch((error) => logJob("load extraction ops failed", { error: error.message }))
);
refs.extractionErrorCategoryFilter.addEventListener("change", () =>
  loadExtractionOps().catch((error) => logJob("load extraction ops failed", { error: error.message }))
);
refs.extractionDueOnlyCheckbox.addEventListener("change", () =>
  loadExtractionOps().catch((error) => logJob("load extraction ops failed", { error: error.message }))
);

refs.articlesList.addEventListener("click", async (event) => {
  const button = event.target.closest("button[data-action]");
  if (!button) return;

  const card = event.target.closest("[data-article-id]");
  if (!card) return;

  const articleId = Number(card.dataset.articleId);
  const action = button.dataset.action;
  const note = card.querySelector('[data-role="note"]').value;
  const isPinned = card.dataset.isPinned === "true";
  const isHidden = card.dataset.isHidden === "true";
  const isSuppressed = card.dataset.isSuppressed === "true";
  const article = state.currentArticles.find((item) => Number(item.id) === articleId);

  try {
    if (action === "toggle-pin") {
      const shouldPin = !isPinned;
      await updateArticle(articleId, { is_pinned: shouldPin });
    } else if (action === "toggle-must-include") {
      await updateArticle(articleId, { must_include: !(article?.must_include) });
    } else if (action === "toggle-suppress") {
      await updateArticle(articleId, { is_suppressed: !isSuppressed });
    } else if (action === "toggle-hide") {
      const shouldHide = !isHidden;
      await updateArticle(articleId, { is_hidden: shouldHide });
    } else if (action === "set-duplicate-primary") {
      await setDuplicatePrimary(articleId);
    } else if (action === "save-note") {
      await updateArticle(articleId, { editorial_note: note });
    }
  } catch (error) {
    logJob("article update failed", { error: error.message, articleId });
  }
});

refs.digestHistoryView.addEventListener("click", async (event) => {
  const button = event.target.closest('button[data-action="rollback-digest-version"]');
  if (!button) return;
  try {
    await rollbackDigestVersion(Number(button.dataset.version));
  } catch (error) {
    logJob("rollback digest version failed", { error: error.message, version: button.dataset.version });
  }
});

refs.sourcesList.addEventListener("click", async (event) => {
  const button = event.target.closest("button[data-action]");
  if (!button) return;

  const sourceId = button.dataset.sourceId;
  const action = button.dataset.action;
  try {
    if (action === "reset-source-cooldown") {
      await resetSourceCooldowns(sourceId ? [sourceId] : null);
    } else if (action === "ack-source-alert") {
      await acknowledgeSourceAlert(sourceId ? [sourceId] : []);
    } else if (action === "snooze-source-alert") {
      await snoozeSourceAlerts(sourceId ? [sourceId] : [], 60, false);
    } else if (action === "clear-source-snooze") {
      await snoozeSourceAlerts(sourceId ? [sourceId] : [], 60, true);
    } else if (action === "toggle-source-maintenance") {
      await setSourceMaintenance(sourceId ? [sourceId] : [], button.dataset.enabled !== "true");
    }
  } catch (error) {
    logJob("source control failed", { error: error.message, sourceId, action });
  }
});

refs.digestArchive.addEventListener("click", async (event) => {
  const button = event.target.closest('button[data-action="open-digest"]');
  if (!button) return;

  const digestId = Number(button.dataset.digestId);
  const payload = await fetchJson("/admin/digests?limit=20", {
    headers: adminHeaders(),
  });
  const digest = (payload.digests || []).find((item) => item.id === digestId);
  if (digest) {
    setSelectedDigestId(digestId);
    renderDigest(digest);
    await loadPublications();
  }
});

refs.extractionOpsList.addEventListener("click", async (event) => {
  const button = event.target.closest('button[data-action="retry-extraction"]');
  if (!button) return;

  const card = event.target.closest("[data-extraction-article-id]");
  if (!card) return;

  const articleId = Number(card.dataset.extractionArticleId);
  try {
    await retryExtractions({
      article_ids: [articleId],
      due_only: false,
      extraction_status: null,
      extraction_error_category: null,
      limit: 1,
    });
  } catch (error) {
    logJob("retry extraction failed", { error: error.message, articleId });
  }
});

setSelectedDigestId(null);
refreshAll();
