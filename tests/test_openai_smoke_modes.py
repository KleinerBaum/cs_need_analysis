from __future__ import annotations

from llm_client import (
    TASK_EXTRACT_JOB_AD,
    TASK_GENERATE_QUESTION_PLAN,
    TASK_GENERATE_VACANCY_BRIEF,
    _build_llm_cache_key,
    build_extract_job_ad_messages,
    build_small_model_guardrails,
    build_chat_parse_request_kwargs,
    build_responses_request_kwargs,
    normalize_reasoning_effort,
    is_nano_model,
    resolve_model_for_task,
    supports_reasoning,
    supports_temperature,
    supports_verbosity,
)
from settings_openai import OpenAISettings


def test_gpt54_nano_sends_none_reasoning_low_verbosity_and_temperature() -> None:
    responses_kwargs = build_responses_request_kwargs(
        model="gpt-5.4-nano",
        store=False,
        maybe_temperature=0.0,
        reasoning_effort="none",
        verbosity="low",
    )
    chat_kwargs = build_chat_parse_request_kwargs(
        model="gpt-5.4-nano",
        maybe_temperature=0.0,
        reasoning_effort="none",
        verbosity="low",
    )

    assert responses_kwargs["model"] == "gpt-5.4-nano"
    assert responses_kwargs["store"] is False
    assert responses_kwargs["reasoning"] == {"effort": "none"}
    assert responses_kwargs["text"] == {"verbosity": "low"}
    assert responses_kwargs["temperature"] == 0.0
    assert chat_kwargs == {
        "model": "gpt-5.4-nano",
        "reasoning": {"effort": "none"},
        "text": {"verbosity": "low"},
        "temperature": 0.0,
    }


def test_gpt5_nano_drops_temperature_but_keeps_compatible_reasoning() -> None:
    kwargs = build_responses_request_kwargs(
        model="gpt-5-nano",
        store=False,
        maybe_temperature=0.7,
        reasoning_effort="low",
        verbosity="low",
    )

    assert kwargs["model"] == "gpt-5-nano"
    assert kwargs["reasoning"] == {"effort": "low"}
    assert kwargs["text"] == {"verbosity": "low"}
    assert "temperature" not in kwargs


def test_gpt5_snapshot_detection_and_capabilities() -> None:
    kwargs = build_responses_request_kwargs(
        model="gpt-5-mini-2026-01-15",
        store=False,
        maybe_temperature=0.5,
        reasoning_effort="xhigh",
        verbosity="high",
    )

    assert supports_reasoning("gpt-5-mini-2026-01-15")
    assert supports_verbosity("gpt-5-mini-2026-01-15")
    assert kwargs["reasoning"] == {"effort": "xhigh"}
    assert kwargs["text"] == {"verbosity": "high"}
    assert "temperature" not in kwargs


def test_non_gpt5_fallback_does_not_get_gpt5_only_fields() -> None:
    kwargs = build_responses_request_kwargs(
        model="gpt-4o-mini",
        store=False,
        maybe_temperature=0.3,
        reasoning_effort="high",
        verbosity="medium",
    )

    assert not supports_reasoning("gpt-4o-mini")
    assert not supports_verbosity("gpt-4o-mini")
    assert kwargs["temperature"] == 0.3
    assert "reasoning" not in kwargs
    assert "text" not in kwargs


def test_smoke_invalid_reasoning_and_temperature_are_safely_filtered() -> None:
    kwargs = build_responses_request_kwargs(
        model="gpt-5-mini",
        store=False,
        maybe_temperature=0.9,
        reasoning_effort="invalid-effort",
        verbosity="medium",
    )

    assert kwargs["model"] == "gpt-5-mini"
    assert "reasoning" not in kwargs
    assert "temperature" not in kwargs
    assert kwargs["text"] == {"verbosity": "medium"}


def test_request_builder_matrix_for_primary_models() -> None:
    matrix = [
        (
            "gpt-5-nano",
            "low",
            "low",
            0.7,
            {"reasoning": {"effort": "low"}, "text": {"verbosity": "low"}},
        ),
        (
            "gpt-5.4-nano",
            "none",
            "low",
            0.0,
            {
                "reasoning": {"effort": "none"},
                "text": {"verbosity": "low"},
                "temperature": 0.0,
            },
        ),
        ("gpt-4o-mini", "high", "medium", 0.3, {"temperature": 0.3}),
    ]

    for model, reasoning, verbosity, temperature, expected_fields in matrix:
        responses_kwargs = build_responses_request_kwargs(
            model=model,
            store=False,
            maybe_temperature=temperature,
            reasoning_effort=reasoning,
            verbosity=verbosity,
        )
        chat_kwargs = build_chat_parse_request_kwargs(
            model=model,
            maybe_temperature=temperature,
            reasoning_effort=reasoning,
            verbosity=verbosity,
        )

        assert responses_kwargs["model"] == model
        assert responses_kwargs["store"] is False
        assert chat_kwargs["model"] == model
        assert "store" not in chat_kwargs

        for key, expected_value in expected_fields.items():
            assert responses_kwargs[key] == expected_value
            assert chat_kwargs[key] == expected_value


def test_reasoning_effort_normalization_accepts_new_values() -> None:
    assert normalize_reasoning_effort("gpt-5", "minimal") == "minimal"
    assert normalize_reasoning_effort("gpt-5-mini", "xhigh") == "xhigh"
    assert normalize_reasoning_effort("gpt-5.4", "none") == "none"
    assert normalize_reasoning_effort("gpt-5", "none") is None
    assert normalize_reasoning_effort("gpt-4o-mini", "high") is None


def test_nano_helpers_detect_supported_models() -> None:
    assert is_nano_model("gpt-5-nano")
    assert is_nano_model("gpt-5.4-nano")
    assert not is_nano_model("gpt-5-mini")


def test_small_model_guardrails_only_added_for_selected_nano_models() -> None:
    assert "Kein Zusatztext außerhalb des Schemas." in build_small_model_guardrails(
        "gpt-5.4-nano"
    )
    assert build_small_model_guardrails("gpt-5-mini") == ""


def test_extract_messages_include_guardrails_for_selected_nano_models() -> None:
    nano_messages = build_extract_job_ad_messages(
        "sample",
        language="de",
        model="gpt-5-nano",
    )
    regular_messages = build_extract_job_ad_messages(
        "sample",
        language="de",
        model="gpt-4o-mini",
    )

    assert "Nur strukturierte Ausgabe gemäß Schema." in nano_messages[0]["content"]
    assert "Fehlende Infos leer/null statt geraten." in nano_messages[0]["content"]
    assert (
        "Nur strukturierte Ausgabe gemäß Schema." not in regular_messages[0]["content"]
    )


def test_supports_temperature_for_gpt54_depends_on_none_reasoning() -> None:
    assert supports_temperature("gpt-5.4-mini", "none")
    assert not supports_temperature("gpt-5.4-mini", "low")


def _build_settings(*, openai_model_override: str | None) -> OpenAISettings:
    return OpenAISettings(
        openai_api_key=None,
        openai_model=(openai_model_override or "gpt-4o-mini"),
        openai_model_override=openai_model_override,
        default_model="gpt-4o-mini",
        lightweight_model="gpt-4o-mini",
        medium_reasoning_model="gpt-4.1-mini",
        high_reasoning_model="o3-mini",
        reasoning_effort="medium",
        verbosity="medium",
        openai_request_timeout=120.0,
        resolved_from={},
    )


def test_model_routing_prefers_ui_override() -> None:
    settings = _build_settings(openai_model_override="gpt-4.1-mini")

    model = resolve_model_for_task(
        task_kind=TASK_GENERATE_QUESTION_PLAN,
        session_override="o3-mini",
        settings=settings,
    )

    assert model == "o3-mini"


def test_model_routing_uses_openai_model_override_before_task_models() -> None:
    settings = _build_settings(openai_model_override="gpt-4.1-mini")

    model = resolve_model_for_task(
        task_kind=TASK_GENERATE_VACANCY_BRIEF,
        session_override="",
        settings=settings,
    )

    assert model == "gpt-4.1-mini"


def test_model_routing_uses_task_specific_models_without_openai_override() -> None:
    settings = _build_settings(openai_model_override=None)

    assert (
        resolve_model_for_task(
            task_kind=TASK_EXTRACT_JOB_AD,
            session_override="",
            settings=settings,
        )
        == "gpt-4o-mini"
    )
    assert (
        resolve_model_for_task(
            task_kind=TASK_GENERATE_QUESTION_PLAN,
            session_override="",
            settings=settings,
        )
        == "gpt-4.1-mini"
    )
    assert (
        resolve_model_for_task(
            task_kind=TASK_GENERATE_VACANCY_BRIEF,
            session_override="",
            settings=settings,
        )
        == "o3-mini"
    )


def test_llm_cache_key_changes_for_model_relevant_inputs() -> None:
    base = _build_llm_cache_key(
        task_kind=TASK_EXTRACT_JOB_AD,
        resolved_model="gpt-4o-mini",
        language="de",
        reasoning_effort="medium",
        verbosity="low",
        store=False,
        normalized_content='{"job_text":"abc"}',
        schema_version=None,
    )
    changed_language = _build_llm_cache_key(
        task_kind=TASK_EXTRACT_JOB_AD,
        resolved_model="gpt-4o-mini",
        language="en",
        reasoning_effort="medium",
        verbosity="low",
        store=False,
        normalized_content='{"job_text":"abc"}',
        schema_version=None,
    )
    changed_store = _build_llm_cache_key(
        task_kind=TASK_EXTRACT_JOB_AD,
        resolved_model="gpt-4o-mini",
        language="de",
        reasoning_effort="medium",
        verbosity="low",
        store=True,
        normalized_content='{"job_text":"abc"}',
        schema_version=None,
    )

    assert base != changed_language
    assert base != changed_store
