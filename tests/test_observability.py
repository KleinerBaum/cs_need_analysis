from __future__ import annotations

import logging

from observability import log_model_call


def test_log_model_call_emits_only_safe_aggregate_metadata(caplog) -> None:
    caplog.set_level(logging.INFO, logger="need_analysis")

    payload = log_model_call(
        task_kind="extract_job_ad",
        model="ft:gpt-4o-mini:private-company:secret-id",
        latency_ms="123",
        prompt_tokens=100,
        completion_tokens=25,
        cache_hit=False,
        endpoint="responses.parse",
        estimated_cost_usd="0.00012",
    )

    assert payload == {
        "task_kind": "extract_job_ad",
        "model": "fine_tuned_model",
        "latency_ms": 123,
        "prompt_tokens": 100,
        "completion_tokens": 25,
        "cache_hit": False,
        "endpoint": "responses.parse",
        "estimated_cost_usd": 0.00012,
        "status": "ok",
    }
    assert "model_call task=extract_job_ad" in caplog.text
    assert "fine_tuned_model" in caplog.text
    assert "private-company" not in caplog.text
    assert "secret-id" not in caplog.text
    assert "sk-" not in caplog.text
