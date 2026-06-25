from __future__ import annotations

from scripts.ci_observability_report import build_events


def test_ci_observability_report_flags_latency_cost_and_failure_alerts() -> None:
    events = build_events(
        eval_report={
            "fixture_count": 2,
            "summaries": [
                {
                    "scope": "overall",
                    "avg_latency_ms": 9000,
                    "avg_cost_usd": 0.02,
                    "passed_thresholds": False,
                }
            ],
        },
        smoke_report={
            "modes": [
                {"actual_response_metadata": {"parse_status": "ok", "latency_ms": 100}},
                {
                    "actual_response_metadata": {
                        "parse_status": "error",
                        "latency_ms": 12_000,
                    }
                },
            ]
        },
        latency_alert_ms=8000,
        cost_alert_usd=0.01,
        failure_rate_alert=0.03,
    )

    by_metric = {
        event["metric"]: event
        for event in events
        if event["event_type"] == "alert_condition"
    }

    assert events[0]["event_type"] == "deployment_event"
    assert events[0]["smoke_modes"] == 2
    assert events[0]["eval_fixture_count"] == 2
    assert events[0]["eval_passed"] is False
    assert by_metric["smoke_p95_latency_ms"]["triggered"] is True
    assert by_metric["eval_avg_latency_ms"]["triggered"] is True
    assert by_metric["eval_avg_cost_usd"]["triggered"] is True
    assert by_metric["smoke_failure_rate"]["triggered"] is True
