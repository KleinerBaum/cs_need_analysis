from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import llm_client
from constants import LLM_RESPONSE_CACHE_MAX_ENTRIES, QUESTION_SCHEMA_VERSION, SSKey
from llm_client import OpenAIRuntimeConfig, generate_question_plan
from schemas import JobAdExtract, QuestionPlan
from settings_openai import OpenAISettings


def _runtime_config() -> OpenAIRuntimeConfig:
    settings = OpenAISettings(
        openai_api_key="test-key",
        openai_model="gpt-5-mini",
        openai_model_override=None,
        default_model="gpt-4o-mini",
        lightweight_model="gpt-4o-mini",
        medium_reasoning_model="gpt-5-mini",
        high_reasoning_model="o3-mini",
        reasoning_effort="medium",
        verbosity="medium",
        openai_request_timeout=30.0,
        esco_vector_store_id=None,
        esco_rag_enabled=False,
        esco_rag_max_results=5,
        task_max_output_tokens={},
        task_max_bullets_per_field={},
        task_max_sentences_per_field={},
        resolved_from={},
    )
    return OpenAIRuntimeConfig(
        resolved_model="gpt-5-mini",
        reasoning_effort=settings.reasoning_effort,
        verbosity=settings.verbosity,
        timeout_seconds=settings.openai_request_timeout,
        task_max_output_tokens=None,
        task_max_bullets_per_field=None,
        task_max_sentences_per_field=None,
        settings=settings,
    )


def test_generate_question_plan_prompt_encodes_section_group_contract(monkeypatch) -> None:
    captured: dict[str, Any] = {}

    def _capture_parse(**kwargs: Any) -> tuple[QuestionPlan, dict[str, int]]:
        captured["messages"] = kwargs["messages"]
        return QuestionPlan(steps=[]), {"total_tokens": 7}

    monkeypatch.setattr(
        llm_client,
        "_resolve_runtime_config",
        lambda **_kwargs: _runtime_config(),
    )
    monkeypatch.setattr(llm_client, "_get_session_response_cache", lambda: {})
    monkeypatch.setattr(llm_client, "_parse_with_structured_outputs", _capture_parse)

    plan, usage = generate_question_plan(
        JobAdExtract(job_title="Data Engineer"),
        model="gpt-5-mini",
    )

    prompt = "\n".join(message["content"] for message in captured["messages"])
    assert plan.steps == []
    assert usage == {"total_tokens": 7}
    assert "generische Base-QuestionPlan" in prompt
    assert "strikte Section-Routing-Grenzen" in prompt
    assert "company: employer_narrative, business_context" in prompt
    assert "role_tasks: role_purpose, top_deliverables" in prompt
    assert "skills: must_have, nice_to_have" in prompt
    assert "benefits: compensation, work_model" in prompt
    assert "interview: candidate_journey, stage_goals" in prompt
    assert "Reserviere IDs mit Prefix 'ctx_'" in prompt
    assert "ESCO/ISCO/NACE-/Regulierungsfragen" in prompt
    assert "fruehere Frage im selben Step" in prompt
    assert "brief, salary, skills, interview, export" in prompt
    assert "info_gain_score" in prompt


def test_session_response_cache_write_enforces_cap() -> None:
    cache = {
        f"key-{index}": {"result": {"value": index}}
        for index in range(LLM_RESPONSE_CACHE_MAX_ENTRIES)
    }

    llm_client._write_session_response_cache_entry(
        cache,
        "new-key",
        {"result": {"value": "new"}},
    )

    assert len(cache) == LLM_RESPONSE_CACHE_MAX_ENTRIES
    assert "key-0" not in cache
    assert list(cache)[-1] == "new-key"


def test_session_response_cache_touch_updates_recency_before_eviction() -> None:
    cache = {
        f"key-{index}": {"result": {"value": index}}
        for index in range(LLM_RESPONSE_CACHE_MAX_ENTRIES)
    }

    cached_entry = llm_client._get_session_response_cache_entry(cache, "key-0")
    assert cached_entry is not None
    llm_client._touch_session_response_cache_entry(cache, "key-0", cached_entry)
    llm_client._write_session_response_cache_entry(
        cache,
        "new-key",
        {"result": {"value": "new"}},
    )

    assert len(cache) == LLM_RESPONSE_CACHE_MAX_ENTRIES
    assert "key-0" in cache
    assert "key-1" not in cache
    assert list(cache)[-2:] == ["key-0", "new-key"]


def test_generate_question_plan_returns_cached_plan_without_parse(monkeypatch) -> None:
    runtime_config = _runtime_config()
    job = JobAdExtract(job_title="Data Engineer")
    cache_key = llm_client._build_llm_cache_key(
        task_kind=llm_client.TASK_GENERATE_QUESTION_PLAN,
        resolved_model=runtime_config.resolved_model,
        language="de",
        reasoning_effort=runtime_config.reasoning_effort,
        verbosity=runtime_config.verbosity,
        store=False,
        normalized_content=llm_client._canonicalize_for_cache(
            job.model_dump(mode="json")
        ),
        schema_version=QUESTION_SCHEMA_VERSION,
    )
    cache = {
        "older-key": {"result": {"steps": []}},
        cache_key: {"result": QuestionPlan(steps=[]).model_dump(mode="json")},
    }
    fake_session_state: dict[str, object] = {}

    def fail_parse(**_kwargs: Any) -> tuple[QuestionPlan, dict[str, int]]:
        raise AssertionError("parse should not be called on cache hit")

    monkeypatch.setattr(
        llm_client,
        "_resolve_runtime_config",
        lambda **_kwargs: runtime_config,
    )
    monkeypatch.setattr(llm_client, "_get_session_response_cache", lambda: cache)
    monkeypatch.setattr(llm_client, "_parse_with_structured_outputs", fail_parse)
    monkeypatch.setattr(
        llm_client,
        "st",
        SimpleNamespace(session_state=fake_session_state),
    )

    plan, usage = generate_question_plan(job, model="gpt-5-mini")

    assert plan.steps == []
    assert usage == {
        "cached": True,
        "cache_key": cache_key,
        "provider": "session_state",
    }
    assert list(cache)[-1] == cache_key
    assert fake_session_state[SSKey.USAGE_EVENTS.value][0]["event_type"] == (
        "openai_usage_recorded"
    )
    assert fake_session_state[SSKey.USAGE_EVENTS.value][0]["metadata"] == {
        "task_kind": llm_client.TASK_GENERATE_QUESTION_PLAN,
        "model": runtime_config.resolved_model,
        "endpoint": "session_state",
        "parse_status": "cache_hit",
        "cache_hit": True,
        "retry_category": "none",
    }
