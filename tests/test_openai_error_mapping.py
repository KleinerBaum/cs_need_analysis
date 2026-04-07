from __future__ import annotations

import httpx
import pytest
from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
)
from pydantic import BaseModel, ValidationError

from llm_client import (
    OpenAIRuntimeConfig,
    _error_from_openai_exception,
    _error_from_structured_output_exception,
    _parse_with_structured_outputs,
)
from settings_openai import OpenAISettings


def test_openai_timeout_maps_to_concise_ui_message() -> None:
    request = httpx.Request("POST", "https://api.openai.com/v1/responses")
    err = APITimeoutError(request=request)

    mapped = _error_from_openai_exception(err, endpoint="responses.parse")
    assert "timeout" in mapped.ui_message.lower()
    assert mapped.error_code == "OPENAI_TIMEOUT"
    assert mapped.debug_detail is not None
    assert "endpoint=responses.parse" in mapped.debug_detail
    assert "exception=APITimeoutError" in mapped.debug_detail


def test_openai_400_maps_to_invalid_parameter_message() -> None:
    request = httpx.Request("POST", "https://api.openai.com/v1/responses")
    response = httpx.Response(status_code=400, request=request)
    err = APIStatusError(
        "bad request",
        response=response,
        body={"error": {"message": "invalid_request_error"}},
    )

    mapped = _error_from_openai_exception(err, endpoint="responses.parse")
    assert "invalid openai parameters" in mapped.ui_message.lower()
    assert mapped.error_code == "OPENAI_BAD_REQUEST_INVALID"
    assert mapped.debug_detail is not None
    assert "api_message=invalid_request_error" in mapped.debug_detail


def test_openai_400_unsupported_parameter_maps_precisely() -> None:
    request = httpx.Request("POST", "https://api.openai.com/v1/responses")
    response = httpx.Response(status_code=400, request=request)
    err = APIStatusError(
        "bad request",
        response=response,
        body={"error": {"message": "unsupported parameter: reasoning"}},
    )

    mapped = _error_from_openai_exception(err, endpoint="responses.parse")
    assert "unsupported openai parameter" in mapped.ui_message.lower()
    assert mapped.error_code == "OPENAI_BAD_REQUEST_UNSUPPORTED_PARAMETER"


def test_openai_400_model_not_found_maps_precisely() -> None:
    request = httpx.Request("POST", "https://api.openai.com/v1/responses")
    response = httpx.Response(status_code=400, request=request)
    err = APIStatusError(
        "bad request",
        response=response,
        body={"error": {"message": "model not found: gpt-4x"}},
    )

    mapped = _error_from_openai_exception(err, endpoint="responses.parse")
    assert "model not found" in mapped.ui_message.lower()
    assert mapped.error_code == "OPENAI_BAD_REQUEST_MODEL_NOT_FOUND"


@pytest.mark.parametrize(
    ("api_message", "expected_code", "ui_hint"),
    [
        (
            "Unsupported parameter: text_format for this model.",
            "OPENAI_BAD_REQUEST_STRUCTURED_OUTPUT_UNSUPPORTED",
            "structured output unsupported",
        ),
        (
            "Model does not support parameter reasoning at this endpoint.",
            "OPENAI_BAD_REQUEST_MODEL_CAPABILITY",
            "model capability mismatch",
        ),
        (
            "This endpoint is not supported for this model. Use /v1/chat/completions.",
            "OPENAI_BAD_REQUEST_ENDPOINT_INCOMPATIBLE",
            "incompatible openai endpoint",
        ),
    ],
)
def test_openai_400_new_classifiers_map_precisely(
    api_message: str,
    expected_code: str,
    ui_hint: str,
) -> None:
    request = httpx.Request("POST", "https://api.openai.com/v1/responses")
    response = httpx.Response(status_code=400, request=request)
    err = APIStatusError(
        "bad request",
        response=response,
        body={"error": {"message": api_message}},
    )

    mapped = _error_from_openai_exception(err, endpoint="responses.parse")
    assert mapped.error_code == expected_code
    assert ui_hint in mapped.ui_message.lower()


def test_openai_auth_maps_to_authentication_message() -> None:
    request = httpx.Request("POST", "https://api.openai.com/v1/responses")
    response = httpx.Response(status_code=401, request=request)
    err = AuthenticationError("auth failed", response=response, body={})

    mapped = _error_from_openai_exception(err, endpoint="responses.parse")
    assert "authentication failed" in mapped.ui_message.lower()
    assert mapped.error_code == "OPENAI_AUTH"


def test_openai_connection_maps_to_connection_message() -> None:
    request = httpx.Request("POST", "https://api.openai.com/v1/responses")
    err = APIConnectionError(message="connection", request=request)

    mapped = _error_from_openai_exception(err, endpoint="responses.parse")
    assert "connection failed" in mapped.ui_message.lower()
    assert mapped.error_code == "OPENAI_CONNECTION"


def test_structured_output_validation_error_maps_cleanly() -> None:
    class MiniModel(BaseModel):
        value: int

    try:
        MiniModel.model_validate({"value": "bad"})
    except ValidationError as err:
        mapped = _error_from_structured_output_exception(err)
    else:
        raise AssertionError("Expected ValidationError for invalid MiniModel payload.")

    assert "structured output" in mapped.ui_message.lower()
    assert mapped.error_code == "OPENAI_PARSE"


def _runtime_config_for_parse(*, resolved_model: str = "gpt-5-mini") -> OpenAIRuntimeConfig:
    settings = OpenAISettings(
        openai_api_key="test-key",
        openai_model=resolved_model,
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
    )
    return OpenAIRuntimeConfig(
        resolved_model=resolved_model,
        reasoning_effort=settings.reasoning_effort,
        verbosity=settings.verbosity,
        timeout_seconds=settings.openai_request_timeout,
        task_max_output_tokens=None,
        task_max_bullets_per_field=None,
        task_max_sentences_per_field=None,
        settings=settings,
    )


class _MiniOut(BaseModel):
    value: int


def test_parse_structured_outputs_retries_on_compatible_400(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeResponse:
        output_parsed = _MiniOut(value=7)
        usage = {"total_tokens": 5}

    class FakeResponses:
        def __init__(self) -> None:
            self.calls: list[dict[str, object]] = []

        def parse(self, **kwargs: object) -> FakeResponse:
            self.calls.append(kwargs)
            if len(self.calls) == 1:
                request = httpx.Request("POST", "https://api.openai.com/v1/responses")
                response = httpx.Response(status_code=400, request=request)
                raise APIStatusError(
                    "bad request",
                    response=response,
                    body={
                        "error": {
                            "message": "Unsupported parameter: text_format for this model."
                        }
                    },
                )
            return FakeResponse()

    fake_responses = FakeResponses()
    fake_client = type("Client", (), {"responses": fake_responses})()

    monkeypatch.setattr("llm_client.get_openai_client", lambda settings: fake_client)
    monkeypatch.setattr("llm_client._has_any_openai_api_key", lambda settings: True)

    parsed, usage = _parse_with_structured_outputs(
        runtime_config=_runtime_config_for_parse(),
        messages=[{"role": "user", "content": "hi"}],
        out_model=_MiniOut,
        store=False,
    )

    parsed_model = _MiniOut.model_validate(parsed.model_dump())
    assert parsed_model.value == 7
    assert usage == {"total_tokens": 5}
    assert len(fake_responses.calls) == 2
    assert "reasoning" in fake_responses.calls[0]
    assert "text" in fake_responses.calls[0]
    assert "reasoning" not in fake_responses.calls[1]
    assert "text" not in fake_responses.calls[1]


def test_parse_structured_outputs_does_not_retry_on_non_retryable_400(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeResponses:
        def __init__(self) -> None:
            self.calls = 0

        def parse(self, **kwargs: object) -> object:
            self.calls += 1
            request = httpx.Request("POST", "https://api.openai.com/v1/responses")
            response = httpx.Response(status_code=400, request=request)
            raise APIStatusError(
                "bad request",
                response=response,
                body={"error": {"message": "invalid_request_error"}},
            )

    fake_responses = FakeResponses()
    fake_client = type("Client", (), {"responses": fake_responses})()
    monkeypatch.setattr("llm_client.get_openai_client", lambda settings: fake_client)
    monkeypatch.setattr("llm_client._has_any_openai_api_key", lambda settings: True)

    with pytest.raises(Exception) as exc_info:
        _parse_with_structured_outputs(
            runtime_config=_runtime_config_for_parse(),
            messages=[{"role": "user", "content": "hi"}],
            out_model=_MiniOut,
            store=False,
        )

    assert "invalid openai parameters" in str(exc_info.value).lower()
    assert fake_responses.calls == 1
