from __future__ import annotations

import time
import uuid
from collections import Counter
from dataclasses import dataclass
from threading import Lock
from typing import Dict, Optional

from .utils import utc_now


@dataclass
class OperationToken:
    name: str
    operation_id: str
    started_at: str
    started_perf: float
    context: Dict[str, object]


class OperationTracker:
    def __init__(self) -> None:
        self._lock = Lock()
        self._operations: Dict[str, Dict[str, object]] = {}
        self._failure_categories: Counter[str] = Counter()
        self._operation_totals: Dict[str, Counter[str]] = {}

    def start(self, name: str, *, context: Optional[Dict[str, object]] = None) -> OperationToken:
        return OperationToken(
            name=name,
            operation_id=uuid.uuid4().hex[:12],
            started_at=utc_now().isoformat(),
            started_perf=time.perf_counter(),
            context=dict(context or {}),
        )

    def finish(
        self,
        token: OperationToken,
        *,
        status: str,
        metrics: Optional[Dict[str, object]] = None,
        error_category: str = "",
    ) -> Dict[str, object]:
        finished_at = utc_now().isoformat()
        duration_ms = round((time.perf_counter() - token.started_perf) * 1000, 2)
        record = {
            "operation_id": token.operation_id,
            "name": token.name,
            "status": status,
            "started_at": token.started_at,
            "finished_at": finished_at,
            "duration_ms": duration_ms,
            "context": dict(token.context),
            "metrics": dict(metrics or {}),
        }
        if error_category:
            record["error_category"] = error_category

        with self._lock:
            self._operations[token.name] = record
            if error_category:
                self._failure_categories[error_category] += 1
            totals = self._operation_totals.setdefault(token.name, Counter())
            totals[status] += 1
        return dict(record)

    def snapshot(self) -> Dict[str, object]:
        with self._lock:
            return {
                "operations": {name: dict(payload) for name, payload in self._operations.items()},
                "failure_categories": dict(self._failure_categories),
                "operation_totals": {
                    name: dict(counter) for name, counter in self._operation_totals.items()
                },
            }
