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
        cached_tokens=10,
        cache_hit=False,
        endpoint="responses.parse",
        estimated_cost_usd="0.00012",
        retry_category="reduced_request",
        error_category="OPENAI_TIMEOUT",
    )

    assert payload == {
        "task_kind": "extract_job_ad",
        "model": "fine_tuned_model",
        "latency_ms": 123,
        "prompt_tokens": 100,
        "completion_tokens": 25,
        "cached_tokens": 10,
        "cache_hit": False,
        "endpoint": "responses.parse",
        "estimated_cost_usd": 0.00012,
        "status": "ok",
        "retry_category": "reduced_request",
        "error_category": "OPENAI_TIMEOUT",
    }
    assert "model_call task=extract_job_ad" in caplog.text
    assert "fine_tuned_model" in caplog.text
    assert "private-company" not in caplog.text
    assert "secret-id" not in caplog.text
    assert "sk-" not in caplog.text


def test_log_model_call_buckets_sensitive_categories(caplog) -> None:
    caplog.set_level(logging.INFO, logger="need_analysis")

    payload = log_model_call(
        task_kind="https://example.com/private-job-spec",
        model="gpt-5-mini",
        latency_ms=1,
        endpoint="api.openai.com",
        status="candidate@example.com",
        retry_category="Jane Doe",
        error_category="sk-test-secret",
    )

    assert payload["task_kind"] == "other"
    assert payload["endpoint"] == "other"
    assert payload["status"] == "other"
    assert payload["retry_category"] == "other"
    assert payload["error_category"] == "other"
    assert "private-job-spec" not in caplog.text
    assert "candidate@example.com" not in caplog.text
    assert "Jane Doe" not in caplog.text
    assert "sk-test-secret" not in caplog.text
