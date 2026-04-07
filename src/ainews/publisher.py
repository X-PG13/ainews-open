from __future__ import annotations

import base64
import hashlib
import hmac
import html
import json
import logging
import mimetypes
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional
from urllib.parse import quote

from .config import Settings
from .http import DownloadedBinary, fetch_binary, fetch_json, post_json, post_multipart
from .utils import clean_text, format_local_date, truncate_text

WECHAT_PUBLISH_STATUS_LABELS = {
    0: "wechat publish succeeded",
    1: "wechat publish in progress",
    2: "wechat publish failed originality check",
    3: "wechat publish failed",
    4: "wechat publish rejected by platform review",
    5: "wechat published article was deleted",
    6: "wechat published article was blocked by the platform",
}
logger = logging.getLogger("ainews.publisher")


@dataclass
class PublicationResult:
    target: str
    status: str
    message: str = ""
    external_id: str = ""
    files: List[str] = field(default_factory=list)
    response: Dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, object]:
        return {
            "target": self.target,
            "status": self.status,
            "message": self.message,
            "external_id": self.external_id,
            "files": self.files,
            "response": self.response,
        }


class DigestPublisher:
    def __init__(
        self,
        settings: Settings,
        *,
        json_post: Callable[..., Dict[str, object]] = post_json,
        json_get: Callable[..., Dict[str, object]] = fetch_json,
        binary_fetch: Callable[..., DownloadedBinary] = fetch_binary,
        multipart_post: Callable[..., Dict[str, object]] = post_multipart,
    ):
        self.settings = settings
        self.json_post = json_post
        self.json_get = json_get
        self.binary_fetch = binary_fetch
        self.multipart_post = multipart_post

    def can_refresh_publication(self, publication: Dict[str, object]) -> bool:
        target = clean_text(str(publication.get("target", ""))).lower()
        if target != "wechat":
            return False
        return bool(self._wechat_publication_id(publication))

    def normalize_targets(self, targets: Optional[Iterable[str]]) -> List[str]:
        return self._normalize_targets(targets)

    def refresh_publication(self, publication: Dict[str, object]) -> PublicationResult:
        target = clean_text(str(publication.get("target", ""))).lower()
        if target != "wechat":
            raise ValueError(f"refresh is not supported for target: {target or 'unknown'}")

        publish_id = self._wechat_publication_id(publication)
        if not publish_id:
            raise ValueError("wechat publish id is not configured")

        access_token = self._resolve_wechat_access_token()
        response = self.json_post(
            f"https://api.weixin.qq.com/cgi-bin/freepublish/get?access_token={quote(access_token, safe='')}",
            {"publish_id": publish_id},
            timeout=self.settings.request_timeout,
            user_agent=self.settings.user_agent,
        )
        self._raise_wechat_error(response, action="query publish status")

        publish_status = int(response.get("publish_status", -1))
        return PublicationResult(
            target="wechat",
            status=self._wechat_publication_state(publish_status),
            message=self._wechat_publication_message(publish_status),
            external_id=publish_id,
            response={"status_query": response},
        )

    def publish(
        self,
        payload: Dict[str, object],
        *,
        targets: Optional[Iterable[str]] = None,
        wechat_submit: Optional[bool] = None,
    ) -> Dict[str, object]:
        requested = self._normalize_targets(targets)
        if not requested:
            requested = self._normalize_targets(self.settings.publish_targets.split(","))
        if not requested:
            return {
                "status": "skipped",
                "reason": "no_targets_configured",
                "targets": [],
                "published": 0,
                "errors": 0,
            }

        results: List[Dict[str, object]] = []
        error_count = 0
        for target in requested:
            try:
                result = self._publish_target(
                    target,
                    payload,
                    wechat_submit=wechat_submit,
                )
            except Exception as exc:
                result = PublicationResult(
                    target=target,
                    status="error",
                    message=str(exc),
                )
                error_count += 1
                logger.warning(
                    "publish target failed",
                    extra={
                        "event": "publisher.target_error",
                        "target": target,
                    },
                )
            else:
                if result.status != "ok":
                    error_count += 1
                logger.info(
                    "publish target completed",
                    extra={
                        "event": "publisher.target_finish",
                        "target": target,
                    },
                )
            results.append(result.to_dict())

        payload = {
            "status": "ok" if error_count == 0 else "partial_error",
            "requested_targets": requested,
            "targets": results,
            "published": len(results) - error_count,
            "errors": error_count,
        }
        logger.info(
            "publisher finished",
            extra={
                "event": "publisher.finish",
                "published": payload["published"],
                "errors": payload["errors"],
                "requested": len(requested),
            },
        )
        return payload

    def _publish_target(
        self,
        target: str,
        payload: Dict[str, object],
        *,
        wechat_submit: Optional[bool],
    ) -> PublicationResult:
        if target == "telegram":
            return self._publish_telegram(payload)
        if target == "feishu":
            return self._publish_feishu(payload)
        if target == "static_site":
            return self._publish_static_site(payload)
        if target == "wechat":
            submit = self.settings.wechat_publish_after_draft if wechat_submit is None else wechat_submit
            return self._publish_wechat(payload, submit=submit)
        raise ValueError(f"unsupported publish target: {target}")

    def _publish_telegram(self, payload: Dict[str, object]) -> PublicationResult:
        token = clean_text(self.settings.telegram_bot_token)
        chat_id = clean_text(self.settings.telegram_chat_id)
        if not token or not chat_id:
            raise ValueError("telegram bot token or chat id is not configured")

        text = self._render_plain_text(payload)
        chunks = self._split_text(text, max_chars=4000)
        responses = []
        last_message_id = ""
        for chunk in chunks:
            response = self.json_post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                {
                    "chat_id": chat_id,
                    "text": chunk,
                    "disable_notification": self.settings.telegram_disable_notification,
                },
                timeout=self.settings.request_timeout,
                user_agent=self.settings.user_agent,
            )
            if not response.get("ok", False):
                raise ValueError(str(response.get("description") or "telegram sendMessage failed"))
            result = response.get("result") or {}
            last_message_id = str(result.get("message_id") or last_message_id)
            responses.append(response)

        return PublicationResult(
            target="telegram",
            status="ok",
            message=f"sent {len(chunks)} telegram message(s)",
            external_id=last_message_id,
            response={"messages": responses},
        )

    def _publish_feishu(self, payload: Dict[str, object]) -> PublicationResult:
        webhook = clean_text(self.settings.feishu_webhook)
        if not webhook:
            raise ValueError("feishu webhook is not configured")

        bodies: List[tuple[str, Dict[str, object]]] = []
        if self.settings.feishu_message_type == "card":
            bodies.append(("card", self._build_feishu_card_body(payload)))
        bodies.append(("text", self._build_feishu_text_body(payload)))

        last_error = ""
        for mode, body in bodies:
            enriched_body = dict(body)
            if self.settings.feishu_secret:
                timestamp = str(int(time.time()))
                enriched_body["timestamp"] = timestamp
                enriched_body["sign"] = self._sign_feishu(timestamp, self.settings.feishu_secret)

            response = self.json_post(
                webhook,
                enriched_body,
                timeout=self.settings.request_timeout,
                user_agent=self.settings.user_agent,
            )
            if int(response.get("code", -1)) == 0:
                message = "sent feishu card message" if mode == "card" else "sent feishu text message"
                return PublicationResult(
                    target="feishu",
                    status="ok",
                    message=message,
                    response=response,
                )
            last_error = str(response.get("msg") or "feishu webhook failed")
            if mode != "card":
                break

        raise ValueError(last_error or "feishu webhook failed")

    def _publish_static_site(self, payload: Dict[str, object]) -> PublicationResult:
        stem = self._digest_stem(payload)
        digest_dir = self.settings.static_site_dir / "digests"
        digest_dir.mkdir(parents=True, exist_ok=True)

        html_path = digest_dir / f"{stem}.html"
        json_path = digest_dir / f"{stem}.json"
        index_path = self.settings.static_site_dir / "index.html"
        latest_json_path = self.settings.static_site_dir / "latest.json"

        html_content = self._render_static_site_html(payload)
        json_content = json.dumps(payload, ensure_ascii=False, indent=2)

        html_path.write_text(html_content, encoding="utf-8")
        json_path.write_text(json_content, encoding="utf-8")
        index_path.write_text(html_content, encoding="utf-8")
        latest_json_path.write_text(json_content, encoding="utf-8")

        return PublicationResult(
            target="static_site",
            status="ok",
            message="rendered static digest site",
            files=[str(index_path), str(html_path), str(latest_json_path), str(json_path)],
            response={
                "base_url": self.settings.static_site_base_url,
            },
        )

    def _publish_wechat(self, payload: Dict[str, object], *, submit: bool) -> PublicationResult:
        access_token = self._resolve_wechat_access_token()
        thumb_media_id = clean_text(self.settings.wechat_thumb_media_id)
        thumb_upload_response: Optional[Dict[str, object]] = None
        if not thumb_media_id:
            thumb_upload_response = self._upload_wechat_thumb(access_token)
            thumb_media_id = clean_text(str(thumb_upload_response.get("media_id", "")))
        if not thumb_media_id:
            raise ValueError("wechat thumb media id is not configured")

        digest = payload.get("digest") or {}
        articles = payload.get("articles") or []
        primary_link = clean_text(self.settings.wechat_content_source_url)
        if not primary_link and articles:
            primary_link = clean_text(str(articles[0].get("url", "")))

        article = {
            "article_type": "news",
            "title": self._wechat_title(str(digest.get("title", "AI 新闻日报"))),
            "author": clean_text(self.settings.wechat_author),
            "digest": truncate_text(str(digest.get("overview", "")), 120),
            "content": self._render_wechat_content(payload),
            "content_source_url": primary_link,
            "thumb_media_id": thumb_media_id,
            "need_open_comment": self.settings.wechat_need_open_comment,
            "only_fans_can_comment": self.settings.wechat_only_fans_can_comment,
        }

        draft_response = self.json_post(
            f"https://api.weixin.qq.com/cgi-bin/draft/add?access_token={quote(access_token, safe='')}",
            {"articles": [article]},
            timeout=self.settings.request_timeout,
            user_agent=self.settings.user_agent,
        )
        self._raise_wechat_error(draft_response, action="create draft")
        media_id = clean_text(str(draft_response.get("media_id", "")))

        response: Dict[str, object] = {"draft": draft_response}
        if thumb_upload_response:
            response["thumb_upload"] = thumb_upload_response
        external_id = media_id
        message = "wechat draft created"
        if submit:
            submit_response = self.json_post(
                f"https://api.weixin.qq.com/cgi-bin/freepublish/submit?access_token={quote(access_token, safe='')}",
                {"media_id": media_id},
                timeout=self.settings.request_timeout,
                user_agent=self.settings.user_agent,
            )
            self._raise_wechat_error(submit_response, action="submit publish")
            response["publish"] = submit_response
            external_id = clean_text(str(submit_response.get("publish_id", media_id)))
            message = "wechat draft created and publish submitted"

        return PublicationResult(
            target="wechat",
            status="ok",
            message=message,
            external_id=external_id,
            response=response,
        )

    def _resolve_wechat_access_token(self) -> str:
        if self.settings.wechat_access_token:
            return self.settings.wechat_access_token

        app_id = clean_text(self.settings.wechat_app_id)
        app_secret = clean_text(self.settings.wechat_app_secret)
        if not app_id or not app_secret:
            raise ValueError("wechat access token or app credentials are not configured")

        response = self.json_get(
            (
                "https://api.weixin.qq.com/cgi-bin/token"
                f"?grant_type=client_credential&appid={quote(app_id, safe='')}"
                f"&secret={quote(app_secret, safe='')}"
            ),
            timeout=self.settings.request_timeout,
            user_agent=self.settings.user_agent,
        )
        access_token = clean_text(str(response.get("access_token", "")))
        if not access_token:
            raise ValueError(str(response.get("errmsg") or "wechat access token request failed"))
        return access_token

    def _upload_wechat_thumb(self, access_token: str) -> Dict[str, object]:
        upload_type = clean_text(self.settings.wechat_thumb_upload_type) or "thumb"
        if upload_type not in {"thumb", "image"}:
            raise ValueError("wechat thumb upload type must be thumb or image")

        source = self._load_wechat_thumb_source()
        if upload_type == "thumb":
            self._validate_wechat_thumb_source(source)

        response = self.multipart_post(
            (
                "https://api.weixin.qq.com/cgi-bin/material/add_material"
                f"?access_token={quote(access_token, safe='')}&type={quote(upload_type, safe='')}"
            ),
            files={
                "media": (
                    source.filename,
                    source.data,
                    source.content_type or "application/octet-stream",
                )
            },
            timeout=self.settings.request_timeout,
            user_agent=self.settings.user_agent,
        )
        self._raise_wechat_error(response, action="upload thumb")
        return response

    def _load_wechat_thumb_source(self) -> DownloadedBinary:
        image_path = clean_text(self.settings.wechat_thumb_image_path)
        if image_path:
            resolved = Path(image_path)
            if not resolved.is_absolute():
                resolved = self.settings.base_dir / resolved
            if not resolved.exists():
                raise ValueError(f"wechat thumb image path does not exist: {resolved}")
            data = resolved.read_bytes()
            content_type = mimetypes.guess_type(str(resolved))[0] or "application/octet-stream"
            return DownloadedBinary(
                data=data,
                content_type=content_type,
                filename=resolved.name,
            )

        image_url = clean_text(self.settings.wechat_thumb_image_url)
        if image_url:
            return self.binary_fetch(
                image_url,
                timeout=self.settings.request_timeout,
                user_agent=self.settings.user_agent,
            )

        raise ValueError("wechat thumb media id or thumb image source is not configured")

    @staticmethod
    def _validate_wechat_thumb_source(source: DownloadedBinary) -> None:
        filename = source.filename.lower()
        content_type = clean_text(source.content_type).lower()
        is_jpeg = filename.endswith(".jpg") or filename.endswith(".jpeg") or "jpeg" in content_type
        if not is_jpeg:
            raise ValueError("wechat thumb upload requires a JPG image")
        if len(source.data) > 64 * 1024:
            raise ValueError("wechat thumb upload requires image size <= 64KB")

    @staticmethod
    def _raise_wechat_error(response: Dict[str, object], *, action: str) -> None:
        errcode = int(response.get("errcode", 0) or 0)
        if errcode != 0:
            raise ValueError(f"wechat {action} failed: {response.get('errmsg') or errcode}")

    @staticmethod
    def _wechat_publication_id(publication: Dict[str, object]) -> str:
        response_payload = publication.get("response_payload")
        if isinstance(response_payload, dict):
            status_query = response_payload.get("status_query")
            if isinstance(status_query, dict):
                publish_id = clean_text(str(status_query.get("publish_id", "")))
                if publish_id:
                    return publish_id
            publish_payload = response_payload.get("publish")
            if isinstance(publish_payload, dict):
                publish_id = clean_text(str(publish_payload.get("publish_id", "")))
                if publish_id:
                    return publish_id
        if clean_text(str(publication.get("status", ""))).lower() == "pending":
            return clean_text(str(publication.get("external_id", "")))
        return ""

    @staticmethod
    def _wechat_publication_state(publish_status: int) -> str:
        if publish_status == 0:
            return "ok"
        if publish_status == 1:
            return "pending"
        return "error"

    @staticmethod
    def _wechat_publication_message(publish_status: int) -> str:
        return WECHAT_PUBLISH_STATUS_LABELS.get(
            publish_status,
            f"wechat publish returned unknown status {publish_status}",
        )

    @staticmethod
    def _sign_feishu(timestamp: str, secret: str) -> str:
        key = f"{timestamp}\n{secret}".encode("utf-8")
        digest = hmac.new(key, digestmod=hashlib.sha256).digest()
        return base64.b64encode(digest).decode("utf-8")

    @staticmethod
    def _normalize_targets(targets: Optional[Iterable[str]]) -> List[str]:
        if targets is None:
            return []

        aliases = {
            "static": "static_site",
            "site": "static_site",
            "wechat_draft": "wechat",
            "wechat_material": "wechat",
        }
        normalized: List[str] = []
        for raw_target in targets:
            value = clean_text(str(raw_target)).lower().replace("-", "_")
            if not value:
                continue
            value = aliases.get(value, value)
            if value not in normalized:
                normalized.append(value)
        return normalized

    @staticmethod
    def _digest_stem(payload: Dict[str, object]) -> str:
        date_prefix = format_local_date().replace("-", "")
        region = clean_text(str(payload.get("region", "all"))) or "all"
        return f"{date_prefix}-{region}-ai-digest"

    def _render_plain_text(self, payload: Dict[str, object]) -> str:
        digest = payload.get("digest") or {}
        sections = digest.get("sections") or []
        highlights = digest.get("highlights") or []

        lines = [clean_text(str(digest.get("title", "AI 新闻日报"))), ""]
        overview = clean_text(str(digest.get("overview", "")))
        if overview:
            lines.extend([overview, ""])
        if highlights:
            lines.append("今日要点")
            lines.extend([f"- {clean_text(str(item))}" for item in highlights])
            lines.append("")
        for section in sections:
            title = clean_text(str(section.get("title", "")))
            if title:
                lines.append(title)
            for item in section.get("items", []):
                lines.append(f"- {clean_text(str(item))}")
            lines.append("")
        closing = clean_text(str(digest.get("closing", "")))
        if closing:
            lines.append(closing)
        return "\n".join(lines).strip()

    def _build_feishu_text_body(self, payload: Dict[str, object]) -> Dict[str, object]:
        text = self._render_plain_text(payload)
        trimmed_text = text if len(text) <= 18000 else text[:18000].rstrip()
        return {
            "msg_type": "text",
            "content": {"text": trimmed_text},
        }

    def _build_feishu_card_body(self, payload: Dict[str, object]) -> Dict[str, object]:
        digest = payload.get("digest") or {}
        static_link = ""
        if self.settings.static_site_base_url:
            static_link = f"{self.settings.static_site_base_url.rstrip('/')}/"
        first_article_url = ""
        articles = payload.get("articles") or []
        if articles:
            first_article_url = clean_text(str(articles[0].get("url", "")))

        sections = []
        overview = clean_text(str(digest.get("overview", "")))
        highlights = [clean_text(str(item)) for item in (digest.get("highlights") or [])[:4]]
        if overview:
            sections.append(overview)
        if highlights:
            sections.append("\n".join([f"- {item}" for item in highlights]))

        markdown_content = truncate_text("\n\n".join(sections), 2200)
        elements: List[Dict[str, object]] = [
            {
                "tag": "markdown",
                "content": markdown_content or "AI 新闻日报已生成。",
                "text_align": "left",
                "text_size": "normal_v2",
                "margin": "0px 0px 12px 0px",
            }
        ]

        action_links = []
        if static_link:
            action_links.append(("查看日报", static_link))
        if first_article_url:
            action_links.append(("查看首条原文", first_article_url))

        for label, url in action_links[:2]:
            elements.append(
                {
                    "tag": "button",
                    "text": {
                        "tag": "plain_text",
                        "content": label,
                    },
                    "type": "default",
                    "width": "default",
                    "size": "medium",
                    "behaviors": [
                        {
                            "type": "open_url",
                            "default_url": url,
                            "pc_url": "",
                            "ios_url": "",
                            "android_url": "",
                        }
                    ],
                    "margin": "0px 0px 0px 0px",
                }
            )

        return {
            "msg_type": "interactive",
            "card": {
                "schema": "2.0",
                "config": {
                    "update_multi": True,
                    "style": {
                        "text_size": {
                            "normal_v2": {
                                "default": "normal",
                                "pc": "normal",
                                "mobile": "heading",
                            }
                        }
                    },
                },
                "body": {
                    "direction": "vertical",
                    "padding": "12px 12px 12px 12px",
                    "elements": elements,
                },
                "header": {
                    "title": {
                        "tag": "plain_text",
                        "content": clean_text(str(digest.get("title", "AI 新闻日报"))),
                    },
                    "subtitle": {
                        "tag": "plain_text",
                        "content": "AI News Open",
                    },
                    "template": "orange",
                    "padding": "12px 12px 12px 12px",
                },
            },
        }

    def _render_static_site_html(self, payload: Dict[str, object]) -> str:
        digest = payload.get("digest") or {}
        articles = payload.get("articles") or []
        title = html.escape(clean_text(str(digest.get("title", "AI 新闻日报"))))
        overview = html.escape(clean_text(str(digest.get("overview", ""))))
        sections_html = []
        for section in digest.get("sections", []):
            items_html = "".join(
                f"<li>{html.escape(clean_text(str(item)))}</li>"
                for item in section.get("items", [])
            )
            sections_html.append(
                f"<section><h2>{html.escape(clean_text(str(section.get('title', ''))))}</h2><ul>{items_html}</ul></section>"
            )

        article_cards = []
        for article in articles[:20]:
            article_cards.append(
                (
                    "<article class=\"news-card\">"
                    f"<h3><a href=\"{html.escape(str(article.get('url', '')))}\" target=\"_blank\" rel=\"noreferrer\">"
                    f"{html.escape(clean_text(str(article.get('display_title_zh') or article.get('title') or '')))}</a></h3>"
                    f"<p>{html.escape(clean_text(str(article.get('compact_summary_zh') or article.get('display_summary_zh') or '')))}</p>"
                    f"<div class=\"meta\">{html.escape(clean_text(str(article.get('source_name', ''))))} · "
                    f"{html.escape(clean_text(str(article.get('published_at', ''))))}</div>"
                    "</article>"
                )
            )

        latest_json_link = "latest.json"
        if self.settings.static_site_base_url:
            latest_json_link = f"{self.settings.static_site_base_url.rstrip('/')}/latest.json"

        return f"""<!DOCTYPE html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>{title}</title>
    <style>
      :root {{
        --bg: #f7f3ec;
        --paper: #fffdf9;
        --ink: #1f1b16;
        --muted: #6d6255;
        --line: rgba(31, 27, 22, 0.12);
        --accent: #bb3a17;
      }}
      * {{ box-sizing: border-box; }}
      body {{
        margin: 0;
        font-family: "Noto Sans SC", sans-serif;
        color: var(--ink);
        background:
          radial-gradient(circle at top left, rgba(187, 58, 23, 0.08), transparent 28%),
          linear-gradient(180deg, #f8f3ea 0%, #efe5d8 100%);
      }}
      main {{
        width: min(1100px, calc(100vw - 32px));
        margin: 0 auto;
        padding: 32px 0 56px;
      }}
      .hero, section, .news-grid {{
        background: rgba(255, 253, 249, 0.9);
        border: 1px solid var(--line);
        border-radius: 24px;
        padding: 24px;
        box-shadow: 0 24px 70px rgba(76, 46, 16, 0.08);
        margin-bottom: 18px;
      }}
      h1, h2, h3 {{ margin: 0; }}
      h1 {{ font-size: clamp(30px, 5vw, 54px); line-height: 1; margin-bottom: 10px; }}
      h2 {{ font-size: 22px; margin-bottom: 12px; }}
      ul {{ padding-left: 18px; margin: 0; }}
      li {{ margin-bottom: 8px; line-height: 1.6; }}
      p {{ line-height: 1.75; }}
      .eyebrow {{ color: var(--accent); font-size: 12px; letter-spacing: 0.18em; text-transform: uppercase; }}
      .meta {{ color: var(--muted); font-size: 13px; }}
      .news-grid {{
        display: grid;
        gap: 14px;
        grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
      }}
      .news-card {{
        border: 1px solid var(--line);
        border-radius: 18px;
        padding: 16px;
        background: rgba(255, 255, 255, 0.62);
      }}
      .news-card a {{
        color: var(--ink);
        text-decoration: none;
      }}
      .news-card a:hover {{
        text-decoration: underline;
      }}
      .footer-link {{
        color: var(--accent);
        text-decoration: none;
      }}
    </style>
  </head>
  <body>
    <main>
      <section class="hero">
        <p class="eyebrow">AI News Open</p>
        <h1>{title}</h1>
        <p>{overview}</p>
        <p class="meta">地区：{html.escape(clean_text(str(payload.get("region", "all"))))} · 文章数：{len(articles)} · JSON：<a class="footer-link" href="{html.escape(latest_json_link)}">latest.json</a></p>
      </section>
      {''.join(sections_html)}
      <section>
        <h2>文章池</h2>
        <div class="news-grid">
          {''.join(article_cards) if article_cards else '<p>当前没有可展示的文章。</p>'}
        </div>
      </section>
    </main>
  </body>
</html>
"""

    def _render_wechat_content(self, payload: Dict[str, object]) -> str:
        digest = payload.get("digest") or {}
        articles = payload.get("articles") or []
        parts = [
            f"<section><h2>{html.escape(clean_text(str(digest.get('title', 'AI 新闻日报'))))}</h2></section>"
        ]

        overview = clean_text(str(digest.get("overview", "")))
        if overview:
            parts.append(f"<p>{html.escape(overview)}</p>")

        highlights = digest.get("highlights") or []
        if highlights:
            parts.append("<h3>今日要点</h3><ul>")
            parts.extend(
                f"<li>{html.escape(clean_text(str(item)))}</li>" for item in highlights
            )
            parts.append("</ul>")

        for section in digest.get("sections", []):
            title = clean_text(str(section.get("title", "")))
            items = section.get("items", [])
            if title:
                parts.append(f"<h3>{html.escape(title)}</h3>")
            if items:
                parts.append("<ul>")
                for item in items:
                    parts.append(f"<li>{html.escape(clean_text(str(item)))}</li>")
                parts.append("</ul>")

        if articles:
            parts.append("<h3>原文链接</h3>")
            for article in articles[:8]:
                article_title = clean_text(
                    str(article.get("display_title_zh") or article.get("title") or "")
                )
                article_url = clean_text(str(article.get("url", "")))
                if article_title and article_url:
                    parts.append(
                        f"<p><a href=\"{html.escape(article_url)}\">{html.escape(article_title)}</a></p>"
                    )

        closing = clean_text(str(digest.get("closing", "")))
        if closing:
            parts.append(f"<p>{html.escape(closing)}</p>")

        return self._truncate_html("".join(parts), 18000)

    @staticmethod
    def _wechat_title(title: str) -> str:
        text = clean_text(title)
        if len(text) <= 32:
            return text
        return text[:32].rstrip()

    @staticmethod
    def _split_text(text: str, *, max_chars: int) -> List[str]:
        normalized = "\n".join(clean_text(line) for line in str(text).splitlines() if clean_text(line))
        if len(normalized) <= max_chars:
            return [normalized]

        chunks: List[str] = []
        current = ""
        for paragraph in normalized.splitlines():
            candidate = paragraph if not current else f"{current}\n{paragraph}"
            if len(candidate) <= max_chars:
                current = candidate
                continue
            if current:
                chunks.append(current)
                current = ""
            while len(paragraph) > max_chars:
                chunks.append(paragraph[:max_chars].rstrip())
                paragraph = paragraph[max_chars:].lstrip()
            current = paragraph
        if current:
            chunks.append(current)
        return chunks

    @staticmethod
    def _truncate_html(value: str, max_chars: int) -> str:
        if len(value) <= max_chars:
            return value
        truncated = value[:max_chars]
        return truncated.rsplit("<", 1)[0].rstrip()
