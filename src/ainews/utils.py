from __future__ import annotations

import hashlib
import html
import json
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Dict, Iterable, Optional
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

TRACKING_QUERY_PREFIXES = ("utm_", "fbclid", "gclid", "mc_", "ref", "spm")
WHITESPACE_RE = re.compile(r"\s+")
TAG_RE = re.compile(r"<[^>]+>")
NON_WORD_RE = re.compile(r"[^0-9A-Za-z\u4e00-\u9fff]+")
ASCII_KEYWORD_RE = re.compile(r"^[a-z0-9][a-z0-9\s\-\+\.]*$")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def strip_html(value: str) -> str:
    return WHITESPACE_RE.sub(" ", html.unescape(TAG_RE.sub(" ", value or ""))).strip()


def clean_text(value: str) -> str:
    return WHITESPACE_RE.sub(" ", (value or "").strip())


def canonicalize_url(url: str) -> str:
    parsed = urlparse(url.strip())
    query_pairs = [
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if not key.lower().startswith(TRACKING_QUERY_PREFIXES)
    ]
    normalized_path = parsed.path.rstrip("/") or "/"
    normalized_query = urlencode(query_pairs)

    return urlunparse(
        (
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            normalized_path,
            "",
            normalized_query,
            "",
        )
    )


def normalize_title(title: str) -> str:
    normalized = NON_WORD_RE.sub("", strip_html(title).lower())
    return normalized[:240]


def build_hash(parts: Iterable[str]) -> str:
    value = "||".join(clean_text(part).lower() for part in parts if part)
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def make_dedup_key(title: str) -> str:
    return build_hash([normalize_title(title)])


def make_content_hash(title: str, summary: str) -> str:
    return build_hash([normalize_title(title), strip_html(summary)])


def make_content_fingerprint(title: str, summary: str = "", body: str = "") -> str:
    text = strip_html(body or summary)[:1000]
    return build_hash([normalize_title(title), text])


def make_resolved_target(url: str, canonical_url: str = "") -> str:
    return canonicalize_url(canonical_url or url)


def url_host(url: str) -> str:
    return urlparse(clean_text(url)).netloc.lower()


def parse_datetime(value: Optional[str]) -> datetime:
    if not value:
        return utc_now()

    text = value.strip()
    try:
        if text.endswith("Z"):
            return datetime.fromisoformat(text.replace("Z", "+00:00")).astimezone(
                timezone.utc
            )
        parsed = datetime.fromisoformat(text)
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except ValueError:
        pass

    try:
        parsed = parsedate_to_datetime(text)
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except (TypeError, ValueError):
        return utc_now()


def matches_keywords(text: str, keywords: Iterable[str]) -> bool:
    haystack = clean_text(text).lower()
    terms = [keyword.strip().lower() for keyword in keywords if keyword.strip()]
    if not terms:
        return True
    for term in terms:
        if ASCII_KEYWORD_RE.fullmatch(term):
            pattern = re.compile(r"(?<![a-z0-9])" + re.escape(term) + r"(?![a-z0-9])")
            if pattern.search(haystack):
                return True
            continue
        if term in haystack:
            return True
    return False


def extract_json_object(value: str) -> Dict[str, Any]:
    text = clean_text(value)
    if not text:
        raise ValueError("empty JSON payload")

    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise ValueError("response did not contain a JSON object")
        parsed = json.loads(text[start : end + 1])

    if not isinstance(parsed, dict):
        raise ValueError("response JSON must be an object")
    return parsed


def format_local_date(value: Optional[datetime] = None) -> str:
    current = value or datetime.now().astimezone()
    return current.strftime("%Y-%m-%d")


def truncate_text(value: str, max_chars: int = 280) -> str:
    text = clean_text(value)
    if len(text) <= max_chars:
        return text

    for separator in ("。", ".", "！", "?", "？", "；", ";"):
        index = text.rfind(separator, 0, max_chars)
        if index >= max_chars // 2:
            return text[: index + 1].strip()

    return text[:max_chars].rstrip() + "..."
