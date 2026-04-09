from __future__ import annotations

from typing import Any

import llm_client
from llm_client import (
    TASK_GENERATE_EMPLOYMENT_CONTRACT,
    OpenAICallError,
    OpenAIRuntimeConfig,
    TASK_GENERATE_BOOLEAN_SEARCH,
    TASK_GENERATE_INTERVIEW_SHEET_HM,
    TASK_GENERATE_INTERVIEW_SHEET_HR,
    generate_boolean_search_pack,
    generate_employment_contract_draft,
    generate_interview_sheet_hr,
    generate_interview_sheet_hm,
    resolve_model_for_task,
)
from schemas import VacancyBrief
from settings_openai import OpenAISettings


def _settings() -> OpenAISettings:
    return OpenAISettings(
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
        task_max_output_tokens={},
        task_max_bullets_per_field={},
        task_max_sentences_per_field={},
        resolved_from={},
    )


def _runtime_config(
    *,
    resolved_model: str = "gpt-5-mini",
    max_output_tokens: int | None = None,
    max_bullets_per_field: int | None = None,
    max_sentences_per_field: int | None = None,
) -> OpenAIRuntimeConfig:
    settings = _settings()
    return OpenAIRuntimeConfig(
        resolved_model=resolved_model,
        reasoning_effort=settings.reasoning_effort,
        verbosity=settings.verbosity,
        timeout_seconds=settings.openai_request_timeout,
        task_max_output_tokens=max_output_tokens,
        task_max_bullets_per_field=max_bullets_per_field,
        task_max_sentences_per_field=max_sentences_per_field,
        settings=settings,
    )


def _brief() -> VacancyBrief:
    return VacancyBrief(
        one_liner="Senior Data Engineer",
        hiring_context="Scale analytics platform",
        role_summary="Build and maintain data products.",
        top_responsibilities=["Build pipelines", "Own data models"],
        must_have=["Python", "SQL", "Airflow"],
        nice_to_have=["dbt"],
        dealbreakers=["No backend experience"],
        interview_plan=["HR screen", "Tech panel"],
        evaluation_rubric=["Problem solving", "Communication"],
        sourcing_channels=["LinkedIn"],
        risks_open_questions=["Notice period unknown"],
        job_ad_draft="Draft",
        structured_data={"answers": {}},
    )


def test_resolve_model_for_new_tasks_uses_expected_buckets() -> None:
    settings = _settings()

    assert (
        resolve_model_for_task(
            task_kind=TASK_GENERATE_INTERVIEW_SHEET_HR,
            session_override=None,
            settings=settings,
        )
        == settings.high_reasoning_model
    )
    assert (
        resolve_model_for_task(
            task_kind=TASK_GENERATE_INTERVIEW_SHEET_HM,
            session_override=None,
            settings=settings,
        )
        == settings.high_reasoning_model
    )
    assert (
        resolve_model_for_task(
            task_kind=TASK_GENERATE_BOOLEAN_SEARCH,
            session_override=None,
            settings=settings,
        )
        == settings.medium_reasoning_model
    )
    assert (
        resolve_model_for_task(
            task_kind=TASK_GENERATE_EMPLOYMENT_CONTRACT,
            session_override=None,
            settings=settings,
        )
        == settings.high_reasoning_model
    )


def test_generate_interview_sheet_hr_returns_deterministic_fallback_on_openai_error(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        llm_client,
        "_resolve_runtime_config",
        lambda **_: _runtime_config(),
    )

    def _raise_openai_error(**_: Any) -> tuple[Any, Any]:
        raise OpenAICallError(
            "OpenAI-Timeout (DE) / OpenAI timeout (EN). Bitte erneut versuchen.",
            error_code="OPENAI_TIMEOUT",
        )

    monkeypatch.setattr(
        llm_client, "_parse_with_structured_outputs", _raise_openai_error
    )

    result, usage = generate_interview_sheet_hr(brief=_brief(), model="gpt-5-mini")

    assert result.interview_stage == "HR Screen"
    assert usage["fallback"] is True
    assert usage["task_kind"] == TASK_GENERATE_INTERVIEW_SHEET_HR
    assert usage["error_code"] == "OPENAI_TIMEOUT"


def test_generate_boolean_search_appends_runtime_output_limits_to_system_prompt(
    monkeypatch,
) -> None:
    captured: dict[str, Any] = {}

    monkeypatch.setattr(
        llm_client,
        "_resolve_runtime_config",
        lambda **_: _runtime_config(
            max_output_tokens=200,
            max_bullets_per_field=2,
            max_sentences_per_field=1,
        ),
    )

    def _capture_parse(**kwargs: Any) -> tuple[Any, dict[str, Any]]:
        captured["messages"] = kwargs["messages"]
        return (
            kwargs["out_model"].model_validate(
                {
                    "role_title": "Senior Data Engineer",
                    "target_locations": [],
                    "seniority_terms": [],
                    "must_have_terms": ["Python"],
                    "exclusion_terms": [],
                    "google": {
                        "broad": ["Python"],
                        "focused": ["Python"],
                        "fallback": ["Python"],
                    },
                    "linkedin": {
                        "broad": ["Python"],
                        "focused": ["Python"],
                        "fallback": ["Python"],
                    },
                    "xing": {
                        "broad": ["Python"],
                        "focused": ["Python"],
                        "fallback": ["Python"],
                    },
                    "channel_limitations": [],
                    "usage_notes": [],
                }
            ),
            {"total_tokens": 9},
        )

    monkeypatch.setattr(llm_client, "_parse_with_structured_outputs", _capture_parse)

    generate_boolean_search_pack(brief=_brief(), model="gpt-5-mini")

    messages = captured["messages"]
    system_prompt = messages[0]["content"]
    assert "Zusätzliche Output-Limits" in system_prompt
    assert "Maximal 2 Bulletpoints" in system_prompt
    assert "Maximal 1 Sätze" in system_prompt
    assert "LinkedIn nur mit großgeschriebenen AND/OR/NOT" in system_prompt
    assert "kein Wildcard-Operator '*'" in system_prompt
    assert "Google darf site:-Operatoren" in system_prompt
    assert "XING nutzt AND/OR/NOT" in system_prompt


def test_generate_interview_sheet_hm_returns_validated_payload(monkeypatch) -> None:
    monkeypatch.setattr(
        llm_client,
        "_resolve_runtime_config",
        lambda **_: _runtime_config(),
    )

    def _parse_success(**kwargs: Any) -> tuple[Any, dict[str, Any]]:
        payload = {
            "role_title": "Senior Data Engineer",
            "interview_stage": "Fachinterview",
            "duration_minutes": 60,
            "competencies_to_validate": ["Systemdesign"],
            "question_blocks": [],
            "technical_deep_dive_topics": ["Data Modelling"],
            "case_or_task_prompt": None,
            "evaluation_rubric": [],
            "hiring_signal_summary": ["Strong ownership"],
            "debrief_questions": ["Would you hire this candidate?"],
        }
        return kwargs["out_model"].model_validate(payload), {"total_tokens": 23}

    monkeypatch.setattr(llm_client, "_parse_with_structured_outputs", _parse_success)

    result, usage = generate_interview_sheet_hm(brief=_brief(), model="gpt-5-mini")

    assert result.interview_stage == "Fachinterview"
    assert usage["total_tokens"] == 23


def test_generate_interview_sheet_hm_fallback_on_validation_error(monkeypatch) -> None:
    monkeypatch.setattr(
        llm_client,
        "_resolve_runtime_config",
        lambda **_: _runtime_config(),
    )

    def _raise_validation_error(**_: Any) -> tuple[Any, Any]:
        try:
            llm_client.InterviewPrepSheetHiringManager.model_validate({})
        except llm_client.ValidationError as exc:
            raise exc
        raise AssertionError("ValidationError expected")

    monkeypatch.setattr(
        llm_client, "_parse_with_structured_outputs", _raise_validation_error
    )

    result, usage = generate_interview_sheet_hm(brief=_brief(), model="gpt-5-mini")

    assert result.role_title == "Senior Data Engineer"
    assert usage["fallback"] is True
    assert usage["task_kind"] == TASK_GENERATE_INTERVIEW_SHEET_HM
    assert usage["error_code"] == "OPENAI_PARSE"


def test_generate_employment_contract_fallback_on_missing_key_error(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        llm_client,
        "_resolve_runtime_config",
        lambda **_: _runtime_config(),
    )

    def _raise_missing_key(**_: Any) -> tuple[Any, Any]:
        raise OpenAICallError(
            "OpenAI API Key fehlt.",
            error_code="OPENAI_MISSING_API_KEY",
        )

    monkeypatch.setattr(
        llm_client, "_parse_with_structured_outputs", _raise_missing_key
    )

    result, usage = generate_employment_contract_draft(
        brief=_brief(), model="gpt-5-mini"
    )

    assert result.role_title == "Senior Data Engineer"
    assert result.salary.min == 0
    assert usage["fallback"] is True
    assert usage["task_kind"] == TASK_GENERATE_EMPLOYMENT_CONTRACT
    assert usage["error_code"] == "OPENAI_MISSING_API_KEY"


def test_generate_employment_contract_prompt_enforces_template_guardrails(
    monkeypatch,
) -> None:
    captured: dict[str, Any] = {}
    monkeypatch.setattr(
        llm_client,
        "_resolve_runtime_config",
        lambda **_: _runtime_config(),
    )

    def _capture_parse(**kwargs: Any) -> tuple[Any, dict[str, Any]]:
        captured["messages"] = kwargs["messages"]
        payload = {
            "contract_language": "de",
            "jurisdiction": "Deutschland",
            "role_title": "Senior Data Engineer",
            "employment_type": "Vollzeit",
            "contract_type": "Unbefristet",
            "start_date": None,
            "probation_period_months": None,
            "salary": {
                "min": 0,
                "max": 0,
                "currency": "EUR",
                "period": "yearly",
                "notes": "Bitte Vergütung ergänzen.",
            },
            "working_hours_per_week": None,
            "vacation_days_per_year": None,
            "place_of_work": None,
            "notice_period": None,
            "clauses": [],
            "signature_requirements": ["Vertrag vor Unterzeichnung rechtlich prüfen."],
            "missing_inputs": ["Salary"],
        }
        return kwargs["out_model"].model_validate(payload), {"total_tokens": 11}

    monkeypatch.setattr(llm_client, "_parse_with_structured_outputs", _capture_parse)

    generate_employment_contract_draft(brief=_brief(), model="gpt-5-mini")

    system_prompt = captured["messages"][0]["content"]
    assert "kein finaler Vertrag und keine Rechtsberatung" in system_prompt
    assert "Platzhalter für Mitarbeiter-/Arbeitgeber-Namen" in system_prompt
    assert "Erfinde keine fehlenden Vertragsbedingungen" in system_prompt
    assert "Nachweisgesetz" in system_prompt
    assert "§ 622 BGB" in system_prompt
