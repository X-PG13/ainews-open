# Operator Console Walkthrough

This walkthrough starts from a local checkout and follows the zero-build admin
console from first startup through ingest, extraction, digest review, and safe
publication preview.

Use it when you want to try the operator workflow without sending anything to
Telegram, Feishu, WeChat, or another outbound channel.

## Safety Model

- Safe demo steps: `ingest`, `extract`, `enrich`, digest preview, digest
  generation, digest snapshot editing, publication preview, and `static_site`
  export write only to the local database or local output directory.
- Network note: ingest and extraction still fetch public source/article URLs, and
  enrichment can call a configured LLM provider. "Safe" here means no publish
  target receives the digest.
- Real outbound publishing: clicking `发布日报` with Telegram, Feishu, or WeChat
  selected, or running `publish` / `run-pipeline --publish` with those targets,
  sends data to external services when credentials are configured.
- Keep `AINEWS_PUBLISH_TARGETS` empty during a local console trial unless you
  intentionally want publishing defaults.

## 1. Prepare An Isolated Local Console

From the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
python -m pip install -e ".[dev]"

export AINEWS_DEMO_HOME="$PWD/.local/operator-console"
mkdir -p "$AINEWS_DEMO_HOME"

export AINEWS_DATABASE_URL="sqlite:///$AINEWS_DEMO_HOME/ainews.db"
export AINEWS_OUTPUT_DIR="$AINEWS_DEMO_HOME/output"
export AINEWS_STATIC_SITE_DIR="$AINEWS_DEMO_HOME/output/site"
export AINEWS_ADMIN_TOKEN="local-demo-token"
export AINEWS_PUBLISH_TARGETS=""
```

These variables keep the demo database and generated files under
`.local/operator-console/` instead of mixing them with another development run.

## 2. Start The API And Console

Run the service in the same shell so it keeps the exported settings:

```bash
python -m ainews serve --host 127.0.0.1 --port 8000
```

If you use the CLI checkpoint commands below while the server is still running,
open a second terminal and repeat the export block from step 1 first.

Open the console:

```text
http://127.0.0.1:8000/
```

In the `Admin Token` field, paste:

```text
local-demo-token
```

Click `保存`. The browser will send `X-Admin-Token` on admin requests.

## 3. Read The First Screen

Before running anything, confirm the first-screen operator map is visible:

- `采集线索`: ingest candidate articles from configured sources.
- `抽取与恢复`: fetch article bodies and inspect retry/cooldown state.
- `选稿与编辑`: preview selection decisions and freeze a reviewed digest draft.
- `多渠道发布`: preview or publish the confirmed digest to configured targets.

The `Operations` panel is the best place to check whether the stack is healthy
before changing data.

## 4. Ingest A Small Candidate Pool

In the console:

1. Keep `区域` as `全部`.
2. Keep `时间窗口` at `48 小时`.
3. Set `单源抓取上限` to a small number such as `10`.
4. Click `抓取新闻`.

Then inspect:

- `文章总数` and `可见文章` in the stat cards.
- `来源状态` for disabled, cooling down, or failing sources.
- `文章池` for the imported article titles.

CLI equivalent:

```bash
python -m ainews ingest --max-items 10
python -m ainews stats
```

## 5. Extract Article Bodies

Click `抓正文`.

Then inspect:

- `已抓正文` in the stat cards.
- `抽取队列` for blocked, throttled, or retry-due articles.
- `告警历史` for repeated source failures.

CLI equivalent:

```bash
python -m ainews extract --since-hours 48 --limit 20
```

Extraction touches remote article pages, but it does not publish anything.

## 6. Preview Digest Selection

Click `选稿预览`.

Use the preview panel to check:

- selected articles
- editorial suppressions
- duplicate secondary articles
- ranked-out articles that missed the limit

If needed, adjust articles in the `文章池`:

- `pin`: raise priority without forcing inclusion.
- `must_include`: force a story into the digest candidate set.
- `suppress`: keep the article in storage but exclude it from digest selection.
- `primary`: choose the lead item for a duplicate cluster.

Previewing selection is safe. It explains the candidate set before a stored
digest is created.

## 7. Generate And Freeze A Reviewable Digest

Click `生成中文日报`.

If no LLM credentials are configured, the service falls back to the built-in
rule-based digest template. That is enough for a local console trial.

After the digest appears:

1. Click `冻结为编辑稿`.
2. Fill `编辑者` and `变更摘要`.
3. Adjust article order, section overrides, publish titles, or publish summaries
   in the editor panel.
4. Click `保存编辑稿`.

Then inspect `编辑稿版本历史`. Publishing by `digest_id` uses this frozen snapshot
instead of recomputing the digest live.

CLI checkpoint:

```bash
python -m ainews list-digests --limit 5
```

## 8. Use Publication Preview Before Publishing

For a safe local preview:

1. Leave Telegram, Feishu, and WeChat unchecked.
2. Optionally check `静态站点` if you want a local static-site output preview.
3. Click `刷新预览`.

Publication preview renders target-specific payloads for review. It does not
send Telegram messages, Feishu cards, or WeChat drafts.

Local-only static-site publish is safe because it writes files under
`AINEWS_STATIC_SITE_DIR`:

```bash
python -m ainews list-digests --limit 5
python -m ainews publish --digest-id 1 --target static_site --force-republish --export
find "$AINEWS_STATIC_SITE_DIR" -maxdepth 2 -type f | sort
```

Replace `1` with the digest ID you want to publish from `list-digests`.

Real outbound publishing starts only when a real target is selected and the
matching credentials are configured:

- `telegram`: requires `AINEWS_TELEGRAM_BOT_TOKEN` and
  `AINEWS_TELEGRAM_CHAT_ID`.
- `feishu`: requires `AINEWS_FEISHU_WEBHOOK`.
- `wechat`: requires the WeChat credential and draft-cover settings documented
  in [Configuration Matrix](./configuration.md).

## 9. Confirm The Trial State

Use these commands after the console run:

```bash
python -m ainews stats
python -m ainews list-digests --limit 5
python -m ainews list-publications --limit 10
find "$AINEWS_DEMO_HOME/output" -maxdepth 2 -type f | sort
```

If you want to reset the trial, stop the server and remove the isolated demo
directory:

```bash
rm -rf "$AINEWS_DEMO_HOME"
```

## Troubleshooting Pointers

- If admin requests return `401`, re-enter the token and click `保存`.
- If ingest imports no articles, widen the lookback window or check
  [Troubleshooting](./troubleshooting.md#the-pipeline-runs-but-there-are-no-articles).
- If extraction failures accumulate, inspect the `抽取队列` and
  [Troubleshooting](./troubleshooting.md).
- If publication preview is empty, open a stored digest first or freeze the
  current digest into an editor snapshot.
