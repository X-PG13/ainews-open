from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import List, Optional

from .models import ArticleRecord, SourceDefinition
from .utils import (
    canonicalize_url,
    make_content_hash,
    make_dedup_key,
    parse_datetime,
    strip_html,
    utc_now,
)


def _local_name(tag: str) -> str:
    return tag.split("}", 1)[-1]


def _find_child_text(element: ET.Element, names: List[str]) -> str:
    for child in list(element):
        if _local_name(child.tag) in names and child.text:
            return child.text.strip()
    return ""


def _find_link(element: ET.Element) -> str:
    for child in list(element):
        if _local_name(child.tag) != "link":
            continue
        href = child.attrib.get("href")
        if href:
            return href.strip()
        if child.text:
            return child.text.strip()
    return ""


def _build_article(source: SourceDefinition, item: ET.Element) -> Optional[ArticleRecord]:
    title = _find_child_text(item, ["title"])
    link = _find_link(item)
    summary = _find_child_text(item, ["description", "summary", "content", "encoded"])
    published_at = parse_datetime(
        _find_child_text(item, ["pubDate", "published", "updated", "date"])
    )

    if not title or not link:
        return None

    canonical_url = canonicalize_url(link)
    return ArticleRecord(
        source_id=source.id,
        source_name=source.name,
        title=strip_html(title),
        url=link.strip(),
        canonical_url=canonical_url,
        summary=strip_html(summary),
        published_at=published_at,
        discovered_at=utc_now(),
        language=source.language,
        region=source.region,
        country=source.country,
        topic=source.topic,
        content_hash=make_content_hash(title, summary),
        dedup_key=make_dedup_key(title),
        raw_payload={
            "title": title,
            "link": link,
            "summary": summary,
        },
    )


def parse_feed_document(xml_text: str, source: SourceDefinition) -> List[ArticleRecord]:
    stripped = xml_text.lstrip().lower()
    if stripped.startswith("<!doctype html") or stripped.startswith("<html"):
        raise ValueError("response is HTML, not RSS/Atom feed")

    root = ET.fromstring(xml_text)
    tag_name = _local_name(root.tag)
    nodes: List[ET.Element] = []

    if tag_name == "rss":
        channel = next((child for child in list(root) if _local_name(child.tag) == "channel"), None)
        if channel is not None:
            nodes = [child for child in list(channel) if _local_name(child.tag) == "item"]
    elif tag_name == "feed":
        nodes = [child for child in list(root) if _local_name(child.tag) == "entry"]
    else:
        nodes = [child for child in list(root) if _local_name(child.tag) in {"item", "entry"}]

    articles = []
    for node in nodes[: source.max_items]:
        article = _build_article(source, node)
        if article is not None:
            articles.append(article)

    return articles
