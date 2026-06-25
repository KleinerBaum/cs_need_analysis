"""Emit CI/CD observability events and alert conditions from local reports."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
import os
from pathlib import Path
import statistics
from typing import Any, Iterable, Mapping


DEFAULT_LATENCY_ALERT_MS = 8_000.0
DEFAULT_COST_ALERT_USD = 0.01
DEFAULT_FAILURE_RATE_ALERT = 0.03


def _read_json(path: Path) -> Any:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _float_env(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _number(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def _json_event(event_type: str, **payload: Any) -> dict[str, Any]:
    return {
        "event_type": event_type,
        "occurred_at": datetime.now(UTC).isoformat(),
        **payload,
    }


def _smoke_modes(smoke_report: Any) -> list[Mapping[str, Any]]:
    if not isinstance(smoke_report, Mapping):
        return []
    modes = smoke_report.get("modes")
    if not isinstance(modes, list):
        return []
    return [mode for mode in modes if isinstance(mode, Mapping)]


def _smoke_failure_rate(smoke_report: Any) -> float | None:
    modes = _smoke_modes(smoke_report)
    if not modes:
        return None
    failures = 0
    for mode in modes:
        metadata = mode.get("actual_response_metadata")
        status = metadata.get("parse_status") if isinstance(metadata, Mapping) else None
        if status == "error":
            failures += 1
    return failures / len(modes)


def _smoke_latencies(smoke_report: Any) -> list[float]:
    latencies: list[float] = []
    for mode in _smoke_modes(smoke_report):
        metadata = mode.get("actual_response_metadata")
        if not isinstance(metadata, Mapping):
            continue
        latency = _number(metadata.get("latency_ms"))
        if latency is not None:
            latencies.append(latency)
    return latencies


def _eval_summaries(eval_report: Any) -> list[Mapping[str, Any]]:
    if not isinstance(eval_report, Mapping):
        return []
    summaries = eval_report.get("summaries")
    if not isinstance(summaries, list):
        return []
    return [summary for summary in summaries if isinstance(summary, Mapping)]


def _eval_overall(eval_report: Any) -> Mapping[str, Any] | None:
    for summary in _eval_summaries(eval_report):
        if summary.get("scope") == "overall":
            return summary
    return None


def _alert_condition(
    *,
    metric: str,
    value: float | None,
    threshold: float,
    comparison: str,
    source: str,
) -> dict[str, Any]:
    triggered = False
    if value is not None:
        if comparison == "gt":
            triggered = value > threshold
        elif comparison == "lt":
            triggered = value < threshold
    return _json_event(
        "alert_condition",
        metric=metric,
        value=value,
        threshold=threshold,
        comparison=comparison,
        source=source,
        triggered=triggered,
    )


def build_events(
    *,
    eval_report: Any,
    smoke_report: Any,
    latency_alert_ms: float,
    cost_alert_usd: float,
    failure_rate_alert: float,
) -> list[dict[str, Any]]:
    latencies = _smoke_latencies(smoke_report)
    smoke_p95 = statistics.quantiles(latencies, n=20)[-1] if len(latencies) >= 2 else (
        latencies[0] if latencies else None
    )
    failure_rate = _smoke_failure_rate(smoke_report)
    overall = _eval_overall(eval_report)
    avg_cost = _number(overall.get("avg_cost_usd")) if overall else None
    avg_latency = _number(overall.get("avg_latency_ms")) if overall else None

    events = [
        _json_event(
            "deployment_event",
            status="observed",
            smoke_modes=len(_smoke_modes(smoke_report)),
            eval_fixture_count=eval_report.get("fixture_count")
            if isinstance(eval_report, Mapping)
            else None,
            eval_passed=all(
                bool(summary.get("passed_thresholds"))
                for summary in _eval_summaries(eval_report)
            )
            if _eval_summaries(eval_report)
            else None,
        ),
        _alert_condition(
            metric="smoke_p95_latency_ms",
            value=smoke_p95,
            threshold=latency_alert_ms,
            comparison="gt",
            source="openai_smoke",
        ),
        _alert_condition(
            metric="eval_avg_latency_ms",
            value=avg_latency,
            threshold=latency_alert_ms,
            comparison="gt",
            source="quality_evals",
        ),
        _alert_condition(
            metric="eval_avg_cost_usd",
            value=avg_cost,
            threshold=cost_alert_usd,
            comparison="gt",
            source="quality_evals",
        ),
        _alert_condition(
            metric="smoke_failure_rate",
            value=failure_rate,
            threshold=failure_rate_alert,
            comparison="gt",
            source="openai_smoke",
        ),
    ]
    return events


def _write_events(path: Path, events: Iterable[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for event in events:
            handle.write(json.dumps(event, sort_keys=True, ensure_ascii=False))
            handle.write("\n")


def _append_step_summary(events: list[Mapping[str, Any]]) -> None:
    summary_path = os.getenv("GITHUB_STEP_SUMMARY")
    if not summary_path:
        return
    triggered = [event for event in events if event.get("triggered") is True]
    lines = [
        "### Deployment observability",
        "",
        "| Metric | Value | Threshold | Triggered |",
        "| --- | ---: | ---: | --- |",
    ]
    for event in events:
        if event.get("event_type") != "alert_condition":
            continue
        lines.append(
            f"| {event.get('metric')} | {event.get('value')} | "
            f"{event.get('threshold')} | {event.get('triggered')} |"
        )
    lines.append("")
    lines.append(f"Triggered alerts: {len(triggered)}")
    with Path(summary_path).open("a", encoding="utf-8") as handle:
        handle.write("\n".join(lines))
        handle.write("\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--eval-json", default="reports/evals/summary.json")
    parser.add_argument("--openai-smoke-json", default="reports/openai-smoke.json")
    parser.add_argument(
        "--output",
        default="reports/observability/deployment-events.jsonl",
    )
    parser.add_argument("--enforce-alerts", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    events = build_events(
        eval_report=_read_json(Path(args.eval_json)),
        smoke_report=_read_json(Path(args.openai_smoke_json)),
        latency_alert_ms=_float_env("CS_ALERT_P95_LATENCY_MS", DEFAULT_LATENCY_ALERT_MS),
        cost_alert_usd=_float_env("CS_ALERT_AVG_COST_USD", DEFAULT_COST_ALERT_USD),
        failure_rate_alert=_float_env(
            "CS_ALERT_FAILURE_RATE",
            DEFAULT_FAILURE_RATE_ALERT,
        ),
    )
    _write_events(Path(args.output), events)
    for event in events:
        print(json.dumps(event, sort_keys=True, ensure_ascii=False))
    _append_step_summary(events)
    if args.enforce_alerts and any(event.get("triggered") is True for event in events):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
