from __future__ import annotations

from typing import Dict, Iterable, Tuple


def _escape_label_value(value: object) -> str:
    text = str(value)
    return text.replace("\\", "\\\\").replace("\n", "\\n").replace('"', '\\"')


def _metric_line(name: str, value: object, labels: Iterable[Tuple[str, object]] | None = None) -> str:
    if labels:
        rendered = ",".join(
            f'{key}="{_escape_label_value(label_value)}"' for key, label_value in labels
        )
        return f"{name}{{{rendered}}} {value}"
    return f"{name} {value}"


def render_metrics(snapshot: Dict[str, object]) -> str:
    lines = [
        "# HELP ainews_build_info Build info for AI News Open.",
        "# TYPE ainews_build_info gauge",
        _metric_line(
            "ainews_build_info",
            1,
            labels=[("version", snapshot.get("build_version", "unknown"))],
        ),
        "# HELP ainews_pipeline_runs_total Total completed pipeline runs by status since process start.",
        "# TYPE ainews_pipeline_runs_total counter",
    ]
    pipeline_totals = snapshot.get("pipeline_runs_total")
    if isinstance(pipeline_totals, dict) and pipeline_totals:
        for status in sorted(pipeline_totals):
            lines.append(
                _metric_line(
                    "ainews_pipeline_runs_total",
                    int(pipeline_totals.get(status) or 0),
                    labels=[("status", status)],
                )
            )
    else:
        lines.append(_metric_line("ainews_pipeline_runs_total", 0, labels=[("status", "ok")]))

    lines.extend(
        [
            "# HELP ainews_extract_failures_total Total extraction failures grouped by category.",
            "# TYPE ainews_extract_failures_total counter",
        ]
    )
    extract_failures = snapshot.get("extract_failures_total")
    if isinstance(extract_failures, dict) and extract_failures:
        for category in sorted(extract_failures):
            lines.append(
                _metric_line(
                    "ainews_extract_failures_total",
                    int(extract_failures.get(category) or 0),
                    labels=[("category", category)],
                )
            )
    else:
        lines.append(
            _metric_line(
                "ainews_extract_failures_total",
                0,
                labels=[("category", "none")],
            )
        )

    lines.extend(
        [
            "# HELP ainews_source_cooldowns_active Current number of active source cooldowns.",
            "# TYPE ainews_source_cooldowns_active gauge",
            _metric_line(
                "ainews_source_cooldowns_active",
                int(snapshot.get("source_cooldowns_active") or 0),
            ),
            "# HELP ainews_source_recoveries_total Total recovered source cooldown incidents.",
            "# TYPE ainews_source_recoveries_total counter",
            _metric_line(
                "ainews_source_recoveries_total",
                int(snapshot.get("source_recoveries_total") or 0),
            ),
            "# HELP ainews_alert_sends_total Total successful alert deliveries and recoveries.",
            "# TYPE ainews_alert_sends_total counter",
            _metric_line(
                "ainews_alert_sends_total",
                int(snapshot.get("alert_sends_total") or 0),
            ),
        ]
    )

    operation_totals = snapshot.get("operation_totals")
    if isinstance(operation_totals, dict):
        lines.extend(
            [
                "# HELP ainews_operation_runs_total Total completed operations by name and status since process start.",
                "# TYPE ainews_operation_runs_total counter",
            ]
        )
        emitted = False
        for name in sorted(operation_totals):
            statuses = operation_totals.get(name)
            if not isinstance(statuses, dict):
                continue
            for status in sorted(statuses):
                lines.append(
                    _metric_line(
                        "ainews_operation_runs_total",
                        int(statuses.get(status) or 0),
                        labels=[("name", name), ("status", status)],
                    )
                )
                emitted = True
        if not emitted:
            lines.append(
                _metric_line(
                    "ainews_operation_runs_total",
                    0,
                    labels=[("name", "pipeline"), ("status", "ok")],
                )
            )

    lines.append("")
    return "\n".join(lines)
