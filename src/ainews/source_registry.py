from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, List, Optional

from .models import SourceDefinition


class SourceRegistry:
    def __init__(self, source_file: Path):
        self.source_file = source_file

    def load(self) -> List[SourceDefinition]:
        payload = json.loads(self.source_file.read_text(encoding="utf-8"))
        return [SourceDefinition(**item) for item in payload.get("sources", [])]

    def list_sources(
        self,
        *,
        enabled_only: bool = True,
        source_ids: Optional[Iterable[str]] = None,
    ) -> List[SourceDefinition]:
        allowed = set(source_ids or [])
        sources = []
        for source in self.load():
            if enabled_only and not source.enabled:
                continue
            if allowed and source.id not in allowed:
                continue
            sources.append(source)
        return sources
