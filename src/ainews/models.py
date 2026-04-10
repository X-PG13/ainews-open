from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Dict, List


@dataclass
class SourceDefinition:
    id: str
    name: str
    url: str
    region: str
    language: str
    country: str
    topic: str
    kind: str = "rss"
    enabled: bool = True
    max_items: int = 50
    include_keywords: List[str] = field(default_factory=list)
    exclude_keywords: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


@dataclass
class ArticleRecord:
    source_id: str
    source_name: str
    title: str
    url: str
    canonical_url: str
    summary: str
    published_at: datetime
    discovered_at: datetime
    language: str
    region: str
    country: str
    topic: str
    content_hash: str
    dedup_key: str
    normalized_title: str = ""
    resolved_target: str = ""
    content_fingerprint: str = ""
    raw_payload: Dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, object]:
        data = asdict(self)
        data["published_at"] = self.published_at.isoformat()
        data["discovered_at"] = self.discovered_at.isoformat()
        return data


@dataclass
class ArticleEnrichment:
    title_zh: str
    summary_zh: str
    importance_zh: str
    provider: str
    model: str

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


@dataclass
class DailyDigest:
    title: str
    overview: str
    highlights: List[str]
    sections: List[Dict[str, object]]
    closing: str
    provider: str = ""
    model: str = ""

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)
