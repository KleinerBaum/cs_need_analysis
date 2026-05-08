from __future__ import annotations

from typing import Any

import pytest
import llm_client
from llm_client import OpenAIRuntimeConfig, generate_vacancy_brief
from schemas import CompanyWebsiteResearch, JobAdExtract, VacancyBrief, VacancyBriefLLM
from settings_openai import OpenAISettings


def _runtime_config() -> OpenAIRuntimeConfig:
    settings = OpenAISettings(
        openai_api_key="test-key",
        openai_model="gpt-5-mini",
        openai_model_override=None,
        default_model="gpt-4o-mini",
        lightweight_model="gpt-4o-mini",
        medium_reasoning_model="gpt-4.1-mini",
        high_reasoning_model="o3-mini",
        reasoning_effort="medium",
        verbosity="medium",
        openai_request_timeout=30.0,
        task_max_output_tokens={},
        task_max_bullets_per_field={},
        task_max_sentences_per_field={},
        resolved_from={},
        esco_vector_store_id=None,
        esco_rag_enabled=False,
        esco_rag_max_results=3,
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


def test_generate_vacancy_brief_uses_llm_parse_model_and_injects_structured_data(
    monkeypatch,
) -> None:
    captured: dict[str, Any] = {}

    def fake_parse_with_structured_outputs(**kwargs: Any):
        captured["out_model"] = kwargs["out_model"]
        return (
            VacancyBriefLLM(
                one_liner="One line",
                hiring_context="Context",
                role_summary="Summary",
                top_responsibilities=["Resp"],
                must_have=["Must"],
                nice_to_have=["Nice"],
                dealbreakers=["Deal"],
                interview_plan=["Interview"],
                evaluation_rubric=["Rubric"],
                sourcing_channels=["Channel"],
                risks_open_questions=["Risk"],
                job_ad_draft="Draft",
            ),
            {"total_tokens": 11},
        )

    monkeypatch.setattr(
        llm_client, "_resolve_runtime_config", lambda **_: _runtime_config()
    )
    monkeypatch.setattr(
        llm_client, "_parse_with_structured_outputs", fake_parse_with_structured_outputs
    )
    monkeypatch.setattr(llm_client, "_get_session_response_cache", lambda: {})

    job = JobAdExtract(job_title="Engineer")
    answers = {"team": {"headcount": 3}}

    brief, usage = generate_vacancy_brief(job, answers, model="gpt-5-mini")

    assert captured["out_model"] is VacancyBriefLLM
    assert usage == {"total_tokens": 11}
    assert isinstance(brief, VacancyBrief)
    structured_data = brief.structured_data.model_dump(mode="json")
    assert structured_data["job_extract"] == job.model_dump()
    assert structured_data["answers"] == answers
    assert structured_data["selected_role_tasks"] is None
    assert structured_data["selected_skills"] is None
    assert structured_data["company_website_research"] is None


def test_generate_vacancy_brief_includes_selected_role_tasks_and_skills(
    monkeypatch,
) -> None:
    def fake_parse_with_structured_outputs(**kwargs: Any):
        return (
            VacancyBriefLLM(
                one_liner="One line",
                hiring_context="Context",
                role_summary="Summary",
                top_responsibilities=["Resp"],
                must_have=["Must"],
                nice_to_have=["Nice"],
                dealbreakers=["Deal"],
                interview_plan=["Interview"],
                evaluation_rubric=["Rubric"],
                sourcing_channels=["Channel"],
                risks_open_questions=["Risk"],
                job_ad_draft="Draft",
            ),
            {},
        )

    monkeypatch.setattr(
        llm_client, "_resolve_runtime_config", lambda **_: _runtime_config()
    )
    monkeypatch.setattr(
        llm_client, "_parse_with_structured_outputs", fake_parse_with_structured_outputs
    )
    monkeypatch.setattr(llm_client, "_get_session_response_cache", lambda: {})

    brief, _ = generate_vacancy_brief(
        JobAdExtract(job_title="Engineer"),
        {"team": {"headcount": 3}},
        model="gpt-5-mini",
        selected_role_tasks=["Build ETL pipelines"],
        selected_skills=["Python", "SQL"],
    )

    assert brief.structured_data.selected_role_tasks == ["Build ETL pipelines"]
    assert brief.structured_data.selected_skills == ["Python", "SQL"]



def test_generate_vacancy_brief_serializes_valid_company_website_research(
    monkeypatch,
) -> None:
    captured: dict[str, Any] = {}

    def fake_parse_with_structured_outputs(**kwargs: Any):
        captured["messages"] = kwargs["messages"]
        return (
            VacancyBriefLLM(
                one_liner="One line",
                hiring_context="Context",
                role_summary="Summary",
                top_responsibilities=["Resp"],
                must_have=["Must"],
                nice_to_have=["Nice"],
                dealbreakers=["Deal"],
                interview_plan=["Interview"],
                evaluation_rubric=["Rubric"],
                sourcing_channels=["Channel"],
                risks_open_questions=["Risk"],
                job_ad_draft="Draft",
            ),
            {},
        )

    monkeypatch.setattr(
        llm_client, "_resolve_runtime_config", lambda **_: _runtime_config()
    )
    monkeypatch.setattr(
        llm_client, "_parse_with_structured_outputs", fake_parse_with_structured_outputs
    )
    monkeypatch.setattr(llm_client, "_get_session_response_cache", lambda: {})

    website_research = CompanyWebsiteResearch.model_validate(
        {
            "homepage_url": "https://example.com",
            "sections": {
                "about": {
                    "source_url": "https://example.com/about",
                    "summary": ["Founded in 2020"],
                    "facts": {"hq": "Berlin"},
                    "fetched_at": "2026-05-08T00:00:00Z",
                }
            },
            "open_question_matches": [],
        }
    )

    brief, _ = generate_vacancy_brief(
        JobAdExtract(job_title="Engineer"),
        {"team": {"headcount": 3}},
        model="gpt-5-mini",
        company_website_research=website_research,
    )

    assert brief.structured_data.company_website_research is not None
    assert (
        brief.structured_data.company_website_research.model_dump(mode="json")
        == website_research.model_dump(mode="json")
    )
    assert "https://example.com/about" in captured["messages"][1]["content"]


def test_generate_vacancy_brief_rejects_invalid_company_website_research_type(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        llm_client, "_resolve_runtime_config", lambda **_: _runtime_config()
    )
    monkeypatch.setattr(llm_client, "_get_session_response_cache", lambda: {})

    def fake_parse_with_structured_outputs(**kwargs: Any):
        return (
            VacancyBriefLLM(
                one_liner="One line",
                hiring_context="Context",
                role_summary="Summary",
                top_responsibilities=["Resp"],
                must_have=["Must"],
                nice_to_have=["Nice"],
                dealbreakers=["Deal"],
                interview_plan=["Interview"],
                evaluation_rubric=["Rubric"],
                sourcing_channels=["Channel"],
                risks_open_questions=["Risk"],
                job_ad_draft="Draft",
            ),
            {},
        )

    monkeypatch.setattr(
        llm_client, "_parse_with_structured_outputs", fake_parse_with_structured_outputs
    )

    with pytest.raises(AttributeError, match="model_dump"):
        generate_vacancy_brief(
            JobAdExtract(job_title="Engineer"),
            {"team": {"headcount": 3}},
            model="gpt-5-mini",
            company_website_research={"sections": []},  # type: ignore[arg-type]
        )
