from __future__ import annotations

from typing import Any

import llm_client
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
