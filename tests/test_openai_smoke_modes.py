from __future__ import annotations

from llm_client import build_openai_request_kwargs


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
