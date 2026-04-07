from __future__ import annotations

from llm_client import (
    TASK_HIGH_REASONING,
    TASK_LIGHTWEIGHT,
    TASK_MEDIUM_REASONING,
    _nano_closed_output_suffix,
    build_openai_request_kwargs,
    normalize_reasoning_effort,
    is_nano_model,
    resolve_model_for_task,
    supports_reasoning,
    supports_temperature,
    supports_verbosity,
)
from settings_openai import OpenAISettings


def test_gpt54_nano_sends_none_reasoning_low_verbosity_and_temperature() -> None:
    kwargs = build_openai_request_kwargs(
        model="gpt-5.4-nano",
        store=False,
        maybe_temperature=0.0,
        reasoning_effort="none",
        verbosity="low",
    )

    assert kwargs["model"] == "gpt-5.4-nano"
    assert kwargs["reasoning"] == {"effort": "none"}
    assert kwargs["text"] == {"verbosity": "low"}
    assert kwargs["temperature"] == 0.0


def test_gpt5_nano_drops_temperature_but_keeps_compatible_reasoning() -> None:
    kwargs = build_openai_request_kwargs(
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
    kwargs = build_openai_request_kwargs(
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
    kwargs = build_openai_request_kwargs(
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


def test_nano_closed_output_suffix_is_only_added_for_nano() -> None:
    assert "Kein Zusatztext außerhalb des Schemas." in _nano_closed_output_suffix(
        "gpt-5.4-nano"
    )
    assert _nano_closed_output_suffix("gpt-4o-mini") == ""


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
        openai_request_timeout=60.0,
    )


def test_model_routing_prefers_ui_override() -> None:
    settings = _build_settings(openai_model_override="gpt-4.1-mini")

    model = resolve_model_for_task(
        task_type=TASK_MEDIUM_REASONING,
        ui_model_override="o3-mini",
        settings=settings,
    )

    assert model == "o3-mini"


def test_model_routing_uses_openai_model_override_before_task_models() -> None:
    settings = _build_settings(openai_model_override="gpt-4.1-mini")

    model = resolve_model_for_task(
        task_type=TASK_HIGH_REASONING,
        ui_model_override="",
        settings=settings,
    )

    assert model == "gpt-4.1-mini"


def test_model_routing_uses_task_specific_models_without_openai_override() -> None:
    settings = _build_settings(openai_model_override=None)

    assert (
        resolve_model_for_task(
            task_type=TASK_LIGHTWEIGHT,
            ui_model_override="",
            settings=settings,
        )
        == "gpt-4o-mini"
    )
    assert (
        resolve_model_for_task(
            task_type=TASK_MEDIUM_REASONING,
            ui_model_override="",
            settings=settings,
        )
        == "gpt-4.1-mini"
    )
    assert (
        resolve_model_for_task(
            task_type=TASK_HIGH_REASONING,
            ui_model_override="",
            settings=settings,
        )
        == "o3-mini"
    )
