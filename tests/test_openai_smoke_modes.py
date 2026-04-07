from __future__ import annotations

from llm_client import (
    _nano_closed_output_suffix,
    build_openai_request_kwargs,
    is_nano_model,
)


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


def test_nano_helpers_detect_supported_models() -> None:
    assert is_nano_model("gpt-5-nano")
    assert is_nano_model("gpt-5.4-nano")
    assert not is_nano_model("gpt-5-mini")


def test_nano_closed_output_suffix_is_only_added_for_nano() -> None:
    assert "Kein Zusatztext außerhalb des Schemas." in _nano_closed_output_suffix(
        "gpt-5.4-nano"
    )
    assert _nano_closed_output_suffix("gpt-4o-mini") == ""
