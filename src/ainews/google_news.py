from __future__ import annotations

import json
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Optional
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen

from .http import fetch_text

GOOGLE_NEWS_BATCH_EXECUTE_URL = "https://news.google.com/_/DotsSplashUi/data/batchexecute"
GOOGLE_NEWS_RPC_ID = "Fbv4je"
GOOGLE_NEWS_LOCALE = "US:en"


class GoogleNewsResolutionError(ValueError):
    pass


@dataclass
class GoogleNewsDecodeTokens:
    article_id: str
    timestamp: int
    signature: str


class _GoogleNewsTokenParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tokens: Optional[GoogleNewsDecodeTokens] = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if self.tokens is not None:
            return
        attrs_dict = {key.lower(): (value or "").strip() for key, value in attrs}
        article_id = attrs_dict.get("data-n-a-id", "")
        timestamp = attrs_dict.get("data-n-a-ts", "")
        signature = attrs_dict.get("data-n-a-sg", "")
        if article_id and timestamp and signature:
            self.tokens = GoogleNewsDecodeTokens(
                article_id=article_id,
                timestamp=int(timestamp),
                signature=signature,
            )


def is_google_news_url(url: str) -> bool:
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    if host != "news.google.com":
        return False
    return "/articles/" in parsed.path or "/read/" in parsed.path


class GoogleNewsURLResolver:
    def __init__(
        self,
        *,
        timeout: int,
        user_agent: str,
        batchexecute_url: str = GOOGLE_NEWS_BATCH_EXECUTE_URL,
    ) -> None:
        self.timeout = timeout
        self.user_agent = user_agent
        self.batchexecute_url = batchexecute_url

    def resolve(self, url: str) -> str:
        if not is_google_news_url(url):
            return url

        wrapper_html = fetch_text(url, timeout=self.timeout, user_agent=self.user_agent)
        tokens = self._extract_tokens(wrapper_html)
        return self._decode_target_url(tokens)

    @staticmethod
    def _extract_tokens(wrapper_html: str) -> GoogleNewsDecodeTokens:
        parser = _GoogleNewsTokenParser()
        parser.feed(wrapper_html)
        parser.close()
        if parser.tokens is None:
            raise GoogleNewsResolutionError("missing Google News decode tokens")
        return parser.tokens

    def _decode_target_url(self, tokens: GoogleNewsDecodeTokens) -> str:
        inner_payload = [
            "garturlreq",
            [
                [
                    "X",
                    "X",
                    ["X", "X"],
                    None,
                    None,
                    1,
                    1,
                    GOOGLE_NEWS_LOCALE,
                    None,
                    1,
                    None,
                    None,
                    None,
                    None,
                    None,
                    0,
                    1,
                ],
                "X",
                "X",
                1,
                [1, 1, 1],
                1,
                1,
                None,
                0,
                0,
                None,
                0,
            ],
            tokens.article_id,
            tokens.timestamp,
            tokens.signature,
        ]
        rpc_payload = [
            GOOGLE_NEWS_RPC_ID,
            json.dumps(inner_payload, ensure_ascii=False, separators=(",", ":")),
        ]
        body = "f.req=" + quote(
            json.dumps([[rpc_payload]], ensure_ascii=False, separators=(",", ":")),
            safe="",
        )
        request = Request(
            self.batchexecute_url,
            data=body.encode("utf-8"),
            headers={
                "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
                "Referer": "https://news.google.com/",
                "User-Agent": self.user_agent,
            },
            method="POST",
        )
        with urlopen(request, timeout=self.timeout) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            payload = response.read().decode(charset, errors="replace")
        resolved_url = self._parse_batchexecute_response(payload)
        if not resolved_url.startswith(("http://", "https://")):
            raise GoogleNewsResolutionError("decoded Google News URL is not absolute")
        return resolved_url

    @staticmethod
    def _parse_batchexecute_response(payload: str) -> str:
        for chunk in payload.split("\n\n"):
            chunk = chunk.strip()
            if not chunk:
                continue
            try:
                rows = json.loads(chunk)
            except json.JSONDecodeError:
                continue
            if not isinstance(rows, list):
                continue
            for row in rows:
                if not isinstance(row, list) or len(row) < 3 or not isinstance(row[2], str):
                    continue
                try:
                    decoded = json.loads(row[2])
                except json.JSONDecodeError:
                    continue
                if isinstance(decoded, list) and len(decoded) > 1 and isinstance(decoded[1], str):
                    return decoded[1]
        raise GoogleNewsResolutionError("unable to parse decoded Google News URL")
