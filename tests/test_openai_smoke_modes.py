from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
from typing import Any

import settings_openai
from llm_client import (
    TASK_EXTRACT_JOB_AD,
    TASK_GENERATE_BENEFIT_SUGGESTIONS,
    TASK_GENERATE_QUESTION_PLAN,
    TASK_GENERATE_VACANCY_BRIEF,
    _build_llm_cache_key,
    build_extract_job_ad_messages,
    build_small_model_guardrails,
    build_chat_parse_request_kwargs,
    build_responses_request_kwargs,
    build_task_prompt_limits_suffix,
    normalize_reasoning_effort,
    is_nano_model,
    resolve_model_for_task,
    supports_reasoning,
    supports_temperature,
    supports_verbosity,
)
from scripts.openai_smoke_test import (
    CONFIGURED_MODEL_SLOTS,
    SMOKE_MODES,
    build_configured_model_request_shapes,
    run_mode,
)
from settings_openai import OpenAISettings

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_gpt54_nano_sends_none_reasoning_low_verbosity_and_temperature() -> None:
    responses_kwargs = build_responses_request_kwargs(
        model="gpt-5.4-nano",
        store=False,
        maybe_temperature=0.0,
        reasoning_effort="none",
        verbosity="low",
        max_output_tokens=333,
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
    assert responses_kwargs["max_output_tokens"] == 333
    assert chat_kwargs == {
        "model": "gpt-5.4-nano",
        "reasoning_effort": "none",
        "verbosity": "low",
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


def test_gpt55_family_detection_and_capabilities() -> None:
    kwargs = build_responses_request_kwargs(
        model="gpt-5.5-pro-2026-06-10",
        store=False,
        maybe_temperature=0.5,
        reasoning_effort="high",
        verbosity="medium",
    )

    assert supports_reasoning("gpt-5.5-pro")
    assert supports_verbosity("gpt-5.5-pro")
    assert kwargs["reasoning"] == {"effort": "high"}
    assert kwargs["text"] == {"verbosity": "medium"}
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


def test_responses_request_kwargs_can_forward_previous_response_id() -> None:
    kwargs = build_responses_request_kwargs(
        model="gpt-5.4-mini",
        store=False,
        maybe_temperature=None,
        reasoning_effort="none",
        verbosity="low",
        previous_response_id="resp_previous",
    )

    assert kwargs["previous_response_id"] == "resp_previous"
    assert kwargs["store"] is False


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
            {"reasoning_effort": "low", "verbosity": "low"},
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
            {
                "reasoning_effort": "none",
                "verbosity": "low",
                "temperature": 0.0,
            },
        ),
        (
            "gpt-4o-mini",
            "high",
            "medium",
            0.3,
            {"temperature": 0.3},
            {"temperature": 0.3},
        ),
    ]

    for (
        model,
        reasoning,
        verbosity,
        temperature,
        expected_responses_fields,
        expected_chat_fields,
    ) in matrix:
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

        for key, expected_value in expected_responses_fields.items():
            assert responses_kwargs[key] == expected_value
        for key, expected_value in expected_chat_fields.items():
            assert chat_kwargs[key] == expected_value
        assert "text" not in chat_kwargs
        assert "reasoning" not in chat_kwargs


def test_reasoning_effort_normalization_accepts_new_values() -> None:
    assert normalize_reasoning_effort("gpt-5", "minimal") == "minimal"
    assert normalize_reasoning_effort("gpt-5-mini", "xhigh") == "xhigh"
    assert normalize_reasoning_effort("gpt-5.4", "none") == "none"
    assert normalize_reasoning_effort("gpt-5.5", "none") == "none"
    assert normalize_reasoning_effort("gpt-5.5-pro", "high") == "high"
    assert normalize_reasoning_effort("gpt-5", "none") is None
    assert normalize_reasoning_effort("gpt-4o-mini", "high") is None


def test_nano_helpers_detect_supported_models() -> None:
    assert is_nano_model("gpt-5-nano")
    assert is_nano_model("gpt-5.4-nano")
    assert is_nano_model("gpt-5.5-nano-2026-06-10")
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


def test_extract_messages_prioritize_job_title_and_no_hallucinated_requirements() -> (
    None
):
    messages = build_extract_job_ad_messages(
        "sample",
        language="de",
        model="gpt-5-mini",
    )

    combined = "\n".join(message["content"] for message in messages)

    assert "Setze job_title auf die kandidatensichtbare Rollenbezeichnung" in combined
    assert "Priorität 1: finde den Jobtitel" in combined
    assert "Erfinde keine Skills, Zertifikate, Success Metrics" in combined
    assert "Fülle field_evidence[]" in combined
    assert (
        "Speichere keine personenbezogenen Kontaktdaten als evidence_snippet"
        in combined
    )


def test_extract_messages_map_offer_sections_to_benefits() -> None:
    messages = build_extract_job_ad_messages(
        "Was wir dir bieten: Trainings, Mentoring und flexible Arbeitsmodelle",
        language="de",
        model="gpt-5-mini",
    )

    combined = "\n".join(message["content"] for message in messages)

    assert "Was wir dir bieten" in combined
    assert "explizit nach benefits[]" in combined
    assert "flexible Arbeitsmodelle" in combined


def test_supports_temperature_for_gpt54_depends_on_none_reasoning() -> None:
    assert supports_temperature("gpt-5.4-mini", "none")
    assert not supports_temperature("gpt-5.4-mini", "low")


def test_openai_smoke_modes_cover_capability_gate_edges_without_live_calls() -> None:
    assert set(SMOKE_MODES) == {
        "gpt-5.4-nano",
        "gpt-5-nano",
        "invalid-reasoning-effort",
        "unsupported-temperature",
    }

    results = {
        mode_name: run_mode(mode, dry_run=True)
        for mode_name, mode in SMOKE_MODES.items()
    }

    gpt54_kwargs = results["gpt-5.4-nano"].effective_request_kwargs
    gpt54_shape = results["gpt-5.4-nano"].request_shape_metadata
    assert gpt54_kwargs["reasoning"] == {"effort": "none"}
    assert gpt54_kwargs["text"] == {"verbosity": "low"}
    assert gpt54_kwargs["temperature"] == 0.0
    assert gpt54_shape["optional_request_fields"] == {
        "temperature": True,
        "reasoning": True,
        "text.verbosity": True,
    }
    assert gpt54_shape["included_optional_fields"] == [
        "temperature",
        "reasoning",
        "text.verbosity",
    ]

    gpt5_kwargs = results["gpt-5-nano"].effective_request_kwargs
    gpt5_shape = results["gpt-5-nano"].request_shape_metadata
    assert gpt5_kwargs["reasoning"] == {"effort": "low"}
    assert gpt5_kwargs["text"] == {"verbosity": "low"}
    assert "temperature" not in gpt5_kwargs
    assert gpt5_shape["optional_request_fields"] == {
        "temperature": False,
        "reasoning": True,
        "text.verbosity": True,
    }
    assert gpt5_shape["omitted_optional_fields"] == ["temperature"]

    invalid_kwargs = results["invalid-reasoning-effort"].effective_request_kwargs
    invalid_shape = results["invalid-reasoning-effort"].request_shape_metadata
    assert "reasoning" not in invalid_kwargs
    assert invalid_kwargs["text"] == {"verbosity": "low"}
    assert "temperature" not in invalid_kwargs
    assert invalid_shape["optional_request_fields"] == {
        "temperature": False,
        "reasoning": False,
        "text.verbosity": True,
    }

    for result in results.values():
        assert result.actual_response_metadata["parse_status"] == "dry_run"
        assert result.actual_response_metadata["request_id"] is None
        assert result.actual_response_metadata["response_id"] is None
        assert result.actual_response_metadata["latency_ms"] is None
        assert result.fields_preview is None


def _isolate_openai_settings_sources(monkeypatch) -> None:
    monkeypatch.setattr(settings_openai.st, "secrets", {})
    for key in (*settings_openai._HARD_DEFAULTS, "REASONING_EFFORT", "VERBOSITY"):
        monkeypatch.delenv(key, raising=False)


def _configured_shapes_by_slot() -> dict[str, dict[str, Any]]:
    return {shape["slot"]: shape for shape in build_configured_model_request_shapes()}


def test_configured_request_shapes_cover_current_default_model_slots(
    monkeypatch,
) -> None:
    _isolate_openai_settings_sources(monkeypatch)

    shapes_by_slot = _configured_shapes_by_slot()

    assert set(shapes_by_slot) == {slot for slot, _ in CONFIGURED_MODEL_SLOTS}
    assert shapes_by_slot["OPENAI_MODEL"]["model"] == "gpt-4o-mini"
    assert shapes_by_slot["DEFAULT_MODEL"]["model"] == "gpt-4o-mini"
    assert shapes_by_slot["LIGHTWEIGHT_MODEL"]["model"] == "gpt-4o-mini"
    assert shapes_by_slot["MEDIUM_REASONING_MODEL"]["model"] == "gpt-4o-mini"
    assert shapes_by_slot["HIGH_REASONING_MODEL"]["model"] == "o3-mini"

    for shape in shapes_by_slot.values():
        metadata = shape["request_shape_metadata"]
        assert metadata["optional_request_fields"] == {
            "temperature": True,
            "reasoning": False,
            "text.verbosity": False,
        }


def test_configured_request_shapes_follow_model_capabilities(monkeypatch) -> None:
    _isolate_openai_settings_sources(monkeypatch)
    slot_models = {
        "OPENAI_MODEL": "gpt-5.4-nano",
        "DEFAULT_MODEL": "gpt-4o-mini",
        "LIGHTWEIGHT_MODEL": "gpt-5-nano",
        "MEDIUM_REASONING_MODEL": "gpt-5.4-mini",
        "HIGH_REASONING_MODEL": "gpt-5.5-pro",
    }
    for slot, model in slot_models.items():
        monkeypatch.setenv(slot, model)
    monkeypatch.setenv("REASONING_EFFORT", "none")
    monkeypatch.setenv("VERBOSITY", "low")

    shapes_by_slot = _configured_shapes_by_slot()

    assert set(shapes_by_slot) == set(slot_models)
    for slot, model in slot_models.items():
        normalized_effort = normalize_reasoning_effort(model, "none")
        metadata = shapes_by_slot[slot]["request_shape_metadata"]
        assert metadata["optional_request_fields"] == {
            "temperature": supports_temperature(model, normalized_effort),
            "reasoning": supports_reasoning(model) and normalized_effort is not None,
            "text.verbosity": supports_verbosity(model),
        }


def test_openai_smoke_script_dry_run_reports_request_shape_metadata() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/openai_smoke_test.py",
            "--mode",
            "gpt-5-nano",
            "--dry-run",
            "--json-only",
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    report = json.loads(completed.stdout)

    assert report["dry_run"] is True
    assert report["modes"][0]["request_shape_metadata"]["optional_request_fields"] == {
        "temperature": False,
        "reasoning": True,
        "text.verbosity": True,
    }
    assert report["configured_model_request_shapes"]
    for configured_shape in report["configured_model_request_shapes"]:
        assert "effective_request_kwargs" not in configured_shape
        assert "request_shape_metadata" in configured_shape


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
        esco_vector_store_id=None,
        esco_rag_enabled=False,
        esco_rag_max_results=5,
        task_max_output_tokens={},
        task_max_bullets_per_field={},
        task_max_sentences_per_field={},
        resolved_from={},
    )


def test_prompt_limits_suffix_includes_all_constraints() -> None:
    suffix = build_task_prompt_limits_suffix(
        max_bullets_per_field=5,
        max_sentences_per_field=2,
        max_output_tokens=700,
    )

    assert "Maximal 5 Bulletpoints pro Listenfeld." in suffix
    assert "Maximal 2 Sätze pro Textfeld." in suffix
    assert "priorisiere Pflichtfelder" in suffix


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
        == "gpt-4.1-mini"
    )
    assert (
        resolve_model_for_task(
            task_kind=TASK_GENERATE_BENEFIT_SUGGESTIONS,
            session_override="",
            settings=settings,
        )
        == "gpt-4.1-mini"
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
