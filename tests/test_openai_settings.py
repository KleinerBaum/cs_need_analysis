from __future__ import annotations

import pytest

import llm_client
import settings_openai
from settings_openai import DEFAULT_TIMEOUT_SECONDS, load_openai_settings


@pytest.fixture(autouse=True)
def _isolate_openai_settings_sources(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings_openai.st, "secrets", {})
    for key in settings_openai._HARD_DEFAULTS:
        monkeypatch.delenv(key, raising=False)


def test_openai_settings_esco_rag_defaults_without_env(monkeypatch) -> None:
    monkeypatch.delenv("ESCO_VECTOR_STORE_ID", raising=False)
    monkeypatch.delenv("ESCO_RAG_ENABLED", raising=False)
    monkeypatch.delenv("ESCO_RAG_MAX_RESULTS", raising=False)

    settings = load_openai_settings()

    assert settings.esco_vector_store_id is None
    assert settings.esco_rag_enabled is False
    assert settings.esco_rag_max_results == 8


def test_openai_settings_esco_rag_env_resolution(monkeypatch) -> None:
    monkeypatch.setenv("ESCO_VECTOR_STORE_ID", "vs_abc123")
    monkeypatch.setenv("ESCO_RAG_ENABLED", "true")
    monkeypatch.setenv("ESCO_RAG_MAX_RESULTS", "12")

    settings = load_openai_settings()

    assert settings.esco_vector_store_id == "vs_abc123"
    assert settings.esco_rag_enabled is True
    assert settings.esco_rag_max_results == 12


def test_openai_settings_esco_rag_disabled_when_vector_store_missing(monkeypatch) -> None:
    monkeypatch.delenv("ESCO_VECTOR_STORE_ID", raising=False)
    monkeypatch.setenv("ESCO_RAG_ENABLED", "true")

    settings = load_openai_settings()

    assert settings.esco_vector_store_id is None
    assert settings.esco_rag_enabled is False


def test_openai_settings_timeout_still_uses_default(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_REQUEST_TIMEOUT", "")

    settings = load_openai_settings()

    assert settings.openai_request_timeout == DEFAULT_TIMEOUT_SECONDS


def test_all_llm_task_kinds_have_limit_settings() -> None:
    configured_task_kinds = set(settings_openai._TASK_KINDS)
    llm_task_kinds = {
        value
        for name, value in vars(llm_client).items()
        if name.startswith("TASK_") and isinstance(value, str)
    }

    assert llm_task_kinds <= configured_task_kinds


def test_openai_task_kind_contract_is_explicit() -> None:
    expected_task_kinds = {
        "extract_job_ad",
        "generate_question_plan",
        "generate_vacancy_brief",
        "generate_job_ad",
        "generate_interview_sheet_hr",
        "generate_interview_sheet_hm",
        "generate_boolean_search",
        "generate_employment_contract",
        "generate_requirement_gap_suggestions",
        "generate_benefit_suggestions",
        "generate_role_tasks_salary_forecast",
    }
    llm_task_kinds = {
        value
        for name, value in vars(llm_client).items()
        if name.startswith("TASK_") and isinstance(value, str)
    }

    assert set(settings_openai._TASK_KINDS) == expected_task_kinds
    assert llm_task_kinds == expected_task_kinds


def test_role_tasks_salary_forecast_limit_settings_resolve_from_env(
    monkeypatch,
) -> None:
    task_upper = llm_client.TASK_GENERATE_ROLE_TASKS_SALARY_FORECAST.upper()
    monkeypatch.setenv(f"{task_upper}_MAX_OUTPUT_TOKENS", "900")
    monkeypatch.setenv(f"{task_upper}_MAX_BULLETS_PER_FIELD", "4")
    monkeypatch.setenv(f"{task_upper}_MAX_SENTENCES_PER_FIELD", "2")

    settings = load_openai_settings()

    task_kind = llm_client.TASK_GENERATE_ROLE_TASKS_SALARY_FORECAST
    assert settings.task_max_output_tokens[task_kind] == 900
    assert settings.task_max_bullets_per_field[task_kind] == 4
    assert settings.task_max_sentences_per_field[task_kind] == 2
