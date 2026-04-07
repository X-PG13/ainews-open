const state = {
  token: localStorage.getItem("ainews_admin_token") || "",
  currentDigest: null,
  selectedDigestId: null,
};

const refs = {
  adminToken: document.getElementById("adminToken"),
  saveTokenButton: document.getElementById("saveTokenButton"),
  refreshAllButton: document.getElementById("refreshAllButton"),
  ingestButton: document.getElementById("ingestButton"),
  extractButton: document.getElementById("extractButton"),
  enrichButton: document.getElementById("enrichButton"),
  digestButton: document.getElementById("digestButton"),
  pipelineButton: document.getElementById("pipelineButton"),
  publishButton: document.getElementById("publishButton"),
  jobOutput: document.getElementById("jobOutput"),
  statsGrid: document.getElementById("statsGrid"),
  sourcesList: document.getElementById("sourcesList"),
  digestView: document.getElementById("digestView"),
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
  publishTargetInputs: Array.from(document.querySelectorAll(".publish-target")),
  wechatSubmitCheckbox: document.getElementById("wechatSubmitCheckbox"),
};

refs.adminToken.value = state.token;

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

function renderStats(stats) {
  const cards = [
    ["文章总数", stats.total_articles || 0],
    ["可见文章", stats.visible_articles || 0],
    ["已抓正文", stats.extracted_articles || 0],
    ["已翻译国际稿", stats.enriched_articles || 0],
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
}

function renderSources(sources) {
  refs.sourcesList.innerHTML = sources
    .map(
      (source) => `
      <article class="source-item">
        <strong>${source.name}</strong>
        <div class="chip-row">
          <span class="chip">${source.region}</span>
          <span class="chip">${source.language}</span>
          <span class="chip">${source.topic}</span>
          <span class="chip ${source.enabled ? "good" : "warn"}">${source.enabled ? "enabled" : "disabled"}</span>
        </div>
      </article>
    `
    )
    .join("");
}

function renderDigest(payload) {
  const digest = payload?.digest || payload?.payload;
  if (!digest) {
    refs.digestView.innerHTML = '<p class="muted">还没有生成日报。</p>';
    return;
  }
  state.currentDigest = digest;
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
  refs.digestView.innerHTML = `
    <p class="eyebrow">Mode: ${escapeHtml(payload.generation_mode || "stored")}</p>
    <h2>${escapeHtml(digest.title || "AI 新闻日报")}</h2>
    <p class="article-summary">${escapeHtml(digest.overview || "")}</p>
    ${highlights ? `<section><h3>今日要点</h3><ul>${highlights}</ul></section>` : ""}
    ${sections}
    ${digest.closing ? `<p class="article-brief">${escapeHtml(digest.closing)}</p>` : ""}
  `;
}

function renderArchive(digests) {
  refs.digestArchive.innerHTML = digests.length
    ? digests
        .map(
          (item) => `
          <article class="archive-item" data-digest-id="${item.id}">
            <strong>${escapeHtml(item.title)}</strong>
            <p class="muted">${escapeHtml(item.generated_at)} · ${escapeHtml(item.region)} · ${item.article_count} 篇</p>
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
    article.llm_status || "pending",
  ];
  if (article.is_pinned) chips.push("pinned");
  if (article.is_hidden) chips.push("hidden");
  return chips
    .filter(Boolean)
    .map((chip) => `<span class="chip">${escapeHtml(String(chip))}</span>`)
    .join("");
}

function renderArticles(articles) {
  refs.articlesList.innerHTML = articles.length
    ? articles
        .map(
          (article) => `
          <article class="article-card" data-article-id="${article.id}" data-is-pinned="${article.is_pinned}" data-is-hidden="${article.is_hidden}">
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
            <p class="article-brief">
              <a class="article-link" href="${escapeAttribute(article.url)}" target="_blank" rel="noreferrer">查看原文</a>
            </p>
            <label>
              编辑备注
              <textarea data-role="note">${escapeHtml(article.editorial_note || "")}</textarea>
            </label>
            <div class="article-actions">
              <button class="button ghost" data-action="toggle-pin">${article.is_pinned ? "取消置顶" : "置顶"}</button>
              <button class="button ghost" data-action="toggle-hide">${article.is_hidden ? "取消隐藏" : "隐藏"}</button>
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

async function loadStats() {
  const stats = await fetchJson("/admin/stats", { headers: adminHeaders() });
  renderStats(stats);
}

async function loadSources() {
  const payload = await fetchJson("/sources");
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

async function loadPublications() {
  const payload = await fetchJson(`/admin/publications?${buildPublicationQuery().toString()}`, {
    headers: adminHeaders(),
  });
  renderPublications(payload.publications || []);
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
    await Promise.all([loadStats(), loadSources(), loadArticles(), loadDigests(), loadPublications()]);
  } catch (error) {
    logJob("refresh failed", { error: error.message });
  }
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
  const payload = await fetchJson("/admin/publish", {
    method: "POST",
    headers: adminHeaders(),
    body: JSON.stringify({
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
}

refs.saveTokenButton.addEventListener("click", () => {
  state.token = refs.adminToken.value.trim();
  localStorage.setItem("ainews_admin_token", state.token);
  logJob("token", { saved: Boolean(state.token) });
});

refs.refreshAllButton.addEventListener("click", refreshAll);
refs.ingestButton.addEventListener("click", () => runIngest().catch((error) => logJob("ingest failed", { error: error.message })));
refs.extractButton.addEventListener("click", () => runExtract().catch((error) => logJob("extract failed", { error: error.message })));
refs.enrichButton.addEventListener("click", () => runEnrich().catch((error) => logJob("enrich failed", { error: error.message })));
refs.digestButton.addEventListener("click", () => runDigest().catch((error) => logJob("digest failed", { error: error.message })));
refs.pipelineButton.addEventListener("click", () => runPipeline().catch((error) => logJob("pipeline failed", { error: error.message })));
refs.publishButton.addEventListener("click", () => runPublish().catch((error) => logJob("publish failed", { error: error.message })));
refs.refreshPublicationsButton.addEventListener("click", () =>
  refreshPublications().catch((error) => logJob("refresh publications failed", { error: error.message }))
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

  try {
    if (action === "toggle-pin") {
      const shouldPin = !isPinned;
      await updateArticle(articleId, { is_pinned: shouldPin });
    } else if (action === "toggle-hide") {
      const shouldHide = !isHidden;
      await updateArticle(articleId, { is_hidden: shouldHide });
    } else if (action === "save-note") {
      await updateArticle(articleId, { editorial_note: note });
    }
  } catch (error) {
    logJob("article update failed", { error: error.message, articleId });
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

setSelectedDigestId(null);
refreshAll();
