from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import llm_client
from constants import FactKey, VACANCY_SCHEMA_VERSION
from llm_client import (
    OpenAIRuntimeConfig,
    build_need_analysis_prompt,
    generate_need_analysis_brief,
    generate_vacancy_brief,
)
from schemas import (
    CompanyWebsiteResearch,
    JobAdExtract,
    NeedAnalysisBrief,
    VacancyBrief,
    VacancyBriefLLM,
)
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
        esco_rag_max_results=5,
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


def test_build_need_analysis_prompt_uses_fixture_text_via_placeholders() -> None:
    jobspec_text = Path("tests/fixtures/need_analysis_jobspec.txt").read_text(
        encoding="utf-8"
    )

    instructions, user_input = build_need_analysis_prompt(
        jobspec_text=jobspec_text,
        locale="de",
    )

    assert instructions == "\n".join(
        [
            "# Identity",
            "You generate a structured recruiting need brief.",
            "# Instructions",
            "Return only schema-compliant JSON.",
            "Use only the supplied jobspec text.",
            "Mark uncertainty explicitly.",
            "# Locale",
            "de",
        ]
    )
    assert user_input == f"<JOBSPEC>\n{jobspec_text}\n</JOBSPEC>"


def test_generate_need_analysis_brief_smoke_uses_strict_schema_model(
    monkeypatch,
) -> None:
    captured: dict[str, Any] = {}

    def fake_parse_with_structured_outputs(**kwargs: Any):
        captured.update(kwargs)
        return (
            NeedAnalysisBrief(
                role_title="Senior Data Engineer",
                hiring_reason="Build a new analytics platform",
                must_have_skills=["Python", "SQL", "Airflow"],
                risk_flags=["unclear budget ownership", "on-call expectations"],
                confidence="high",
            ),
            {"total_tokens": 17},
        )

    monkeypatch.setattr(
        llm_client, "_resolve_runtime_config", lambda **_: _runtime_config()
    )
    monkeypatch.setattr(
        llm_client, "_parse_with_structured_outputs", fake_parse_with_structured_outputs
    )
    jobspec_text = Path("tests/fixtures/need_analysis_jobspec.txt").read_text(
        encoding="utf-8"
    )

    brief, usage = generate_need_analysis_brief(
        jobspec_text=jobspec_text,
        model="gpt-5-mini",
        locale="de",
    )

    assert captured["out_model"] is NeedAnalysisBrief
    assert captured["messages"] == [
        {
            "role": "system",
            "content": build_need_analysis_prompt(
                jobspec_text=jobspec_text,
                locale="de",
            )[0],
        },
        {
            "role": "user",
            "content": build_need_analysis_prompt(
                jobspec_text=jobspec_text,
                locale="de",
            )[1],
        },
    ]
    assert brief.role_title == "Senior Data Engineer"
    assert usage == {"total_tokens": 17}


def test_generate_vacancy_brief_uses_llm_parse_model_and_injects_structured_data(
    monkeypatch,
) -> None:
    captured: dict[str, Any] = {}

    def fake_parse_with_structured_outputs(**kwargs: Any):
        captured.update(kwargs)
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
    assert captured["responses_instructions"].startswith(
        "Du bist ein Recruiting Partner"
    )
    assert "Audience mode: recruiter" in captured["responses_instructions"]
    assert captured["responses_input"].startswith(
        "Erstelle jetzt den finalen VacancyBrief."
    )
    assert captured["store"] is False
    assert captured["include_response_metadata"] is True
    assert usage == {"total_tokens": 11}
    assert isinstance(brief, VacancyBrief)
    structured_data = brief.structured_data.model_dump(mode="json")
    assert structured_data["job_extract"] == job.model_dump()
    assert structured_data["answers"] == answers
    assert structured_data["selected_role_tasks"] is None
    assert structured_data["selected_skills"] is None
    assert structured_data["selected_benefits"] is None
    assert structured_data["company_website_research"] is None


def test_generate_vacancy_brief_returns_cached_brief_without_parse(
    monkeypatch,
) -> None:
    runtime_config = _runtime_config()
    job = JobAdExtract(job_title="Engineer")
    answers = {"team": {"headcount": 3}}
    cached_brief = VacancyBrief(
        one_liner="Cached line",
        hiring_context="Cached context",
        role_summary="Cached summary",
        top_responsibilities=["Cached responsibility"],
        must_have=["Cached must"],
        nice_to_have=[],
        dealbreakers=[],
        interview_plan=[],
        evaluation_rubric=[],
        sourcing_channels=[],
        risks_open_questions=[],
        job_ad_draft="Cached draft",
        structured_data={
            "job_extract": job.model_dump(),
            "answers": answers,
        },
    )
    cache_key = llm_client._build_llm_cache_key(
        task_kind=llm_client.TASK_GENERATE_VACANCY_BRIEF,
        resolved_model=runtime_config.resolved_model,
        language="de",
        reasoning_effort=runtime_config.reasoning_effort,
        verbosity=runtime_config.verbosity,
        store=False,
        normalized_content=llm_client._canonicalize_for_cache(
            {
                "job": job.model_dump(mode="json"),
                "answers": answers,
                "normalized_structured_fields": llm_client._normalized_structured_fields(
                    answers
                ),
                "selected_role_tasks": [],
                "selected_skills": [],
                "selected_benefits": [],
                "offer_positioning": {},
                "salary_forecast": {},
                "interview_process": {},
                "audience_mode": "recruiter",
                "company_website_research": {},
            }
        ),
        schema_version=VACANCY_SCHEMA_VERSION,
    )
    cache = {
        "older-key": {"result": {"one_liner": "old"}},
        cache_key: {"result": cached_brief.model_dump(mode="json")},
    }

    def fail_parse(**_kwargs: Any) -> tuple[VacancyBriefLLM, dict[str, int]]:
        raise AssertionError("parse should not be called on cache hit")

    monkeypatch.setattr(
        llm_client, "_resolve_runtime_config", lambda **_: runtime_config
    )
    monkeypatch.setattr(llm_client, "_get_session_response_cache", lambda: cache)
    monkeypatch.setattr(llm_client, "_parse_with_structured_outputs", fail_parse)

    brief, usage = generate_vacancy_brief(job, answers, model="gpt-5-mini")

    assert brief.one_liner == "Cached line"
    assert usage == {
        "cached": True,
        "cache_key": cache_key,
        "provider": "session_state",
    }
    assert list(cache)[-1] == cache_key


def test_generate_vacancy_brief_normalizes_legacy_candidate_audience_mode(
    monkeypatch,
) -> None:
    captured: dict[str, Any] = {}

    def fake_parse_with_structured_outputs(**kwargs: Any):
        captured.update(kwargs)
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

    generate_vacancy_brief(
        JobAdExtract(job_title="Engineer"),
        {"team": {"headcount": 3}},
        model="gpt-5-mini",
        audience_mode="candidate",
    )

    system_prompt = captured["messages"][0]["content"]
    assert "Audience mode: recruiter" in system_prompt
    assert "avoid internal scoring language" not in system_prompt


def test_generate_vacancy_brief_includes_selected_role_tasks_skills_and_benefits(
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
        selected_benefits=["Mentoring"],
        offer_positioning={
            "salary_decision": {"salary_claim_status": "notes_only"},
            "candidate_value": ["Mentoring"],
        },
        salary_forecast={"forecast": {"p50": 90000}, "orientation_only": True},
        interview_process={"evaluation_plan": {"core_questions": ["Warum diese Rolle?"]}},
    )

    assert brief.structured_data.selected_role_tasks == ["Build ETL pipelines"]
    assert brief.structured_data.selected_skills == ["Python", "SQL"]
    assert brief.structured_data.selected_benefits == ["Mentoring"]
    assert brief.structured_data.offer_positioning == {
        "salary_decision": {"salary_claim_status": "notes_only"},
        "candidate_value": ["Mentoring"],
    }
    assert brief.structured_data.salary_forecast == {
        "forecast": {"p50": 90000},
        "orientation_only": True,
    }
    assert brief.structured_data.interview_process == {
        "evaluation_plan": {"core_questions": ["Warum diese Rolle?"]}
    }


def test_generate_vacancy_brief_embeds_normalized_structured_objects(
    monkeypatch,
) -> None:
    captured: dict[str, Any] = {}

    def fake_parse_with_structured_outputs(**kwargs: Any):
        captured.update(kwargs)
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

    answers = {
        FactKey.SKILLS_ITEMS.value: [
            {"label": "Python", "status": "must", "readiness_timing": "start"}
        ],
        FactKey.BENEFITS_VARIABLE_PAY.value: {
            "eligible": True,
            "ote_min": 90000,
            "currency": "EUR",
        },
        FactKey.ROLE_TRAVEL_PROFILE.value: {"required": False, "percent": 0},
        FactKey.INTERVIEW_SCORECARD_TEMPLATE.value: {
            "stage": "Fachinterview",
            "criteria": [{"title": "Python", "weight_percent": 50}],
        },
    }

    brief, _ = generate_vacancy_brief(
        JobAdExtract(job_title="Engineer"),
        answers,
        model="gpt-5-mini",
    )

    assert brief.structured_data.skill_items is not None
    assert brief.structured_data.skill_items[0].label == "Python"
    assert brief.structured_data.variable_pay is not None
    assert brief.structured_data.variable_pay.currency == "EUR"
    assert brief.structured_data.travel_profile is not None
    assert brief.structured_data.travel_profile.required is False
    assert brief.structured_data.interview_scorecard_template is not None
    assert "Normalisierte strukturierte Felder" in captured["responses_input"]
    assert "Fachinterview" in captured["responses_input"]



def test_generate_vacancy_brief_serializes_valid_company_website_research(
    monkeypatch,
) -> None:
    captured: dict[str, Any] = {}

    def fake_parse_with_structured_outputs(**kwargs: Any):
        captured.update(kwargs)
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
    assert "https://example.com/about" in captured["responses_input"]


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
