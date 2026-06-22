from __future__ import annotations

from constants import SSKey, UsageEventType
from usage_events import (
    MAX_USAGE_EVENTS,
    append_usage_event,
    get_usage_events,
    record_artifact_generated,
    record_enrichment_timed,
    record_evaluation_run_completed,
    record_fact_confirmed,
    record_fact_corrected,
    record_fact_rejected,
    record_fallback_model_used,
    record_homepage_fetch_failed,
    record_step_entered,
    record_step_submitted,
    reset_usage_events,
)


def test_append_usage_event_sanitizes_sensitive_metadata() -> None:
    session_state: dict[str, object] = {}

    append_usage_event(
        session_state,
        UsageEventType.ARTIFACT_GENERATED,
        metadata={
            "artifact_id": "brief",
            "cache_hit": False,
            "api_key": "sk-secret",
            "domain": "example.com",
            "hostname": "www.example.com",
            "source_url": "https://example.com/private",
            "prompt_text": "contains PII",
            "long_value": "x" * 140,
        },
        occurred_at="2026-06-10T00:00:00+00:00",
    )

    assert session_state[SSKey.USAGE_EVENTS.value] == [
        {
            "event_type": "artifact_generated",
            "occurred_at": "2026-06-10T00:00:00+00:00",
            "metadata": {
                "artifact_id": "brief",
                "cache_hit": False,
                "long_value": f"{'x' * 119}…",
            },
        }
    ]


def test_usage_events_are_bounded() -> None:
    session_state: dict[str, object] = {}

    for index in range(MAX_USAGE_EVENTS + 5):
        append_usage_event(
            session_state,
            "step_entered",
            metadata={"step_key": f"step_{index}"},
            occurred_at=f"2026-06-10T00:00:{index:02d}+00:00",
        )

    events = get_usage_events(session_state)
    assert len(events) == MAX_USAGE_EVENTS
    assert events[0]["metadata"]["step_key"] == "step_5"


def test_record_helpers_write_expected_event_types() -> None:
    session_state: dict[str, object] = {}

    record_homepage_fetch_failed(
        session_state,
        topic_key="about",
        error_type="HomepageFetchError",
    )
    record_enrichment_timed(
        session_state,
        stage="esco_rag",
        path="skills",
        duration_ms=42,
        cache_hit=False,
        result_count=3,
    )
    record_artifact_generated(
        session_state,
        artifact_id="job_ad",
        cache_hit=True,
        mode="from_brief",
    )

    events = get_usage_events(session_state)
    assert [event["event_type"] for event in events] == [
        "homepage_fetch_failed",
        "enrichment_timed",
        "artifact_generated",
    ]
    assert events[0]["metadata"] == {
        "topic_key": "about",
        "error_type": "HomepageFetchError",
    }
    assert events[1]["metadata"] == {
        "stage": "esco_rag",
        "path": "skills",
        "duration_ms": 42,
        "status": "success",
        "cache_hit": False,
        "result_count": 3,
    }
    assert events[2]["metadata"] == {
        "artifact_id": "job_ad",
        "cache_hit": True,
        "mode": "from_brief",
    }


def test_record_evaluation_run_completed_writes_only_safe_aggregates() -> None:
    session_state: dict[str, object] = {}

    record_evaluation_run_completed(
        session_state,
        run_id="offline_deterministic_2026_06_19",
        scenario_count=5,
        combination_count=5,
        best_combination_id="balanced",
        best_score=4.12345,
        passed_success_criteria=True,
    )

    events = get_usage_events(session_state)
    assert events == [
        {
            "event_type": "evaluation_run_completed",
            "occurred_at": events[0]["occurred_at"],
            "metadata": {
                "run_id": "offline_deterministic_2026_06_19",
                "scenario_count": 5,
                "combination_count": 5,
                "best_combination_id": "balanced",
                "best_score": 4.123,
                "passed_success_criteria": True,
            },
        }
    ]


def test_record_step_fact_and_fallback_helpers_write_safe_metadata() -> None:
    session_state: dict[str, object] = {}

    record_step_entered(session_state, step_key="company")
    record_step_submitted(session_state, step_key="company", action="next")
    record_fact_confirmed(
        session_state,
        fact_key="role.job_title",
        source_type="manual",
    )
    record_fact_corrected(
        session_state,
        fact_key="role.job_title",
        source_type="manual",
    )
    record_fact_rejected(
        session_state,
        fact_key="role.job_title",
        source_type="manual",
    )
    record_fallback_model_used(
        session_state,
        task_kind="generate_job_ad",
        requested_model="o3-mini",
        final_model="gpt-4o-mini",
        fallback_kind="fallback_model",
        endpoint="responses.parse",
        error_code="OPENAI_BAD_REQUEST_MODEL_CAPABILITY",
    )

    events = get_usage_events(session_state)
    assert [event["event_type"] for event in events] == [
        "step_entered",
        "step_submitted",
        "fact_confirmed",
        "fact_corrected",
        "fact_rejected",
        "fallback_model_used",
    ]
    assert events[0]["metadata"] == {"step_key": "company"}
    assert events[1]["metadata"] == {"step_key": "company", "action": "next"}
    assert events[2]["metadata"] == {
        "fact_key": "role.job_title",
        "source_type": "manual",
    }
    assert events[5]["metadata"] == {
        "task_kind": "generate_job_ad",
        "requested_model": "o3-mini",
        "final_model": "gpt-4o-mini",
        "fallback_kind": "fallback_model",
        "endpoint": "responses.parse",
        "error_code": "OPENAI_BAD_REQUEST_MODEL_CAPABILITY",
    }


def test_reset_usage_events_clears_state() -> None:
    session_state: dict[str, object] = {
        SSKey.USAGE_EVENTS.value: [{"event_type": "step_entered"}]
    }

    reset_usage_events(session_state)

    assert session_state[SSKey.USAGE_EVENTS.value] == []
