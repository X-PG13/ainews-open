from __future__ import annotations

from typing import Dict, List, Protocol

from .config import Settings
from .http import post_json
from .models import ArticleEnrichment, DailyDigest
from .utils import clean_text, extract_json_object, format_local_date


class LLMClient(Protocol):
    def is_configured(self) -> bool: ...

    def enrich_article(self, article: Dict[str, object]) -> ArticleEnrichment: ...

    def generate_digest(
        self,
        article_briefs: List[Dict[str, object]],
        *,
        region: str,
        since_hours: int,
    ) -> DailyDigest: ...


class OpenAICompatibleLLMClient:
    def __init__(self, settings: Settings):
        self.settings = settings

    def is_configured(self) -> bool:
        return all(
            [
                self.settings.llm_base_url,
                self.settings.llm_api_key,
                self.settings.llm_model,
            ]
        )

    def enrich_article(self, article: Dict[str, object]) -> ArticleEnrichment:
        article_context = clean_text(str(article.get("extracted_text", "")))
        if article_context:
            article_context = article_context[: self.settings.llm_article_context_chars]
        else:
            article_context = clean_text(str(article.get("summary", "")))

        payload = self._generate_json(
            system_prompt=(
                "You are a careful bilingual AI news editor. "
                "Translate and summarize international AI news for Chinese readers. "
                "Return valid JSON only and do not fabricate facts."
            ),
            user_prompt=(
                "基于下面这篇 AI 新闻元数据，输出 JSON，字段必须为 "
                "title_zh, summary_zh, importance_zh。\n"
                "要求：\n"
                "1. title_zh 是简洁准确的中文标题。\n"
                "2. summary_zh 用 1 到 2 句话概括新闻内容。\n"
                "3. importance_zh 用 1 句话说明这条新闻为什么值得关注。\n"
                "4. 只根据给定信息总结，不要补充未提供的事实。\n\n"
                f"source_name: {article.get('source_name', '')}\n"
                f"published_at: {article.get('published_at', '')}\n"
                f"title: {article.get('title', '')}\n"
                f"summary: {article.get('summary', '')}\n"
                f"article_context: {article_context}\n"
                f"url: {article.get('url', '')}\n"
            ),
        )
        return ArticleEnrichment(
            title_zh=clean_text(str(payload.get("title_zh", ""))),
            summary_zh=clean_text(str(payload.get("summary_zh", ""))),
            importance_zh=clean_text(str(payload.get("importance_zh", ""))),
            provider=self.settings.llm_provider,
            model=self.settings.llm_model,
        )

    def generate_digest(
        self,
        article_briefs: List[Dict[str, object]],
        *,
        region: str,
        since_hours: int,
    ) -> DailyDigest:
        articles_block = "\n".join(
            [
                (
                    f"{index}. [{article.get('region')}] {article.get('display_title_zh')}\n"
                    f"   source: {article.get('source_name')}\n"
                    f"   published_at: {article.get('published_at')}\n"
                    f"   summary: {article.get('display_summary_zh')}\n"
                    f"   importance: {article.get('display_brief_zh')}\n"
                )
                for index, article in enumerate(article_briefs, start=1)
            ]
        )
        payload = self._generate_json(
            system_prompt=(
                "You are the chief editor of a Chinese AI industry daily. "
                "Produce a tight, professional briefing in simplified Chinese. "
                "Return valid JSON only."
            ),
            user_prompt=(
                "请根据以下新闻条目，生成一份中文 AI 日报 JSON，字段必须为 "
                "title, overview, highlights, sections, closing。\n"
                "要求：\n"
                "1. highlights 是 3 到 5 条字符串数组。\n"
                "2. sections 是数组，每项包含 title 和 items 字段，items 是字符串数组。\n"
                "3. 内容要面向中文读者，优先突出模型、产品、融资、政策、芯片、开源、应用落地。\n"
                "4. 不要编造信息，不要出现 JSON 之外的文字。\n"
                f"5. 日报日期使用 {format_local_date()}，范围为最近 {since_hours} 小时，region={region}。\n\n"
                f"{articles_block}"
            ),
        )
        highlights = [
            clean_text(str(item)) for item in payload.get("highlights", []) if clean_text(str(item))
        ]
        sections = []
        for section in payload.get("sections", []):
            if not isinstance(section, dict):
                continue
            title = clean_text(str(section.get("title", "")))
            items = [
                clean_text(str(item)) for item in section.get("items", []) if clean_text(str(item))
            ]
            if title and items:
                sections.append({"title": title, "items": items})

        return DailyDigest(
            title=clean_text(str(payload.get("title", f"AI 新闻日报 {format_local_date()}"))),
            overview=clean_text(str(payload.get("overview", ""))),
            highlights=highlights,
            sections=sections,
            closing=clean_text(str(payload.get("closing", ""))),
            provider=self.settings.llm_provider,
            model=self.settings.llm_model,
        )

    def _generate_json(self, *, system_prompt: str, user_prompt: str) -> Dict[str, object]:
        if not self.is_configured():
            raise RuntimeError("LLM is not configured")

        response = post_json(
            f"{self.settings.llm_base_url}/chat/completions",
            {
                "model": self.settings.llm_model,
                "temperature": self.settings.llm_temperature,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            },
            timeout=self.settings.llm_timeout,
            user_agent=self.settings.user_agent,
            headers={"Authorization": f"Bearer {self.settings.llm_api_key}"},
        )

        choices = response.get("choices", [])
        if not choices:
            raise ValueError("LLM response did not include choices")

        message = choices[0].get("message", {})
        content = message.get("content", "")
        if isinstance(content, list):
            text_parts = [
                str(item.get("text", ""))
                for item in content
                if isinstance(item, dict) and item.get("type") in {None, "text", "output_text"}
            ]
            content = "\n".join(part for part in text_parts if part)

        return extract_json_object(str(content))
