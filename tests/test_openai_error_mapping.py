from __future__ import annotations

from types import SimpleNamespace

import httpx
import pytest
from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    RateLimitError,
)
from pydantic import BaseModel, ValidationError

import llm_client
import llm_error_mapping
from constants import SSKey
from llm_client import (
    OpenAIRuntimeConfig,
    _error_from_openai_exception,
    _error_from_structured_output_exception,
    _is_retryable_openai_exception,
    _parse_with_structured_outputs,
)
from settings_openai import OpenAISettings


def test_error_mapping_helpers_remain_available_from_llm_client_facade() -> None:
    assert llm_client.OpenAICallError is llm_error_mapping.OpenAICallError
    assert (
        llm_client._error_from_openai_exception
        is llm_error_mapping._error_from_openai_exception
    )
    assert (
        llm_client._error_from_structured_output_exception
        is llm_error_mapping._error_from_structured_output_exception
    )
    assert llm_client._error_from_openai_exception.__name__ == (
        "_error_from_openai_exception"
    )
    assert llm_client._error_from_structured_output_exception.__name__ == (
        "_error_from_structured_output_exception"
    )


def test_openai_timeout_maps_to_concise_ui_message() -> None:
    request = httpx.Request("POST", "https://api.openai.com/v1/responses")
    err = APITimeoutError(request=request)

    mapped = _error_from_openai_exception(err, endpoint="responses.parse")
    assert "timeout" in mapped.ui_message.lower()
    assert mapped.error_code == "OPENAI_TIMEOUT"
    assert mapped.debug_detail is not None
    assert "endpoint=responses.parse" in mapped.debug_detail
    assert "exception=APITimeoutError" in mapped.debug_detail


def test_openai_rate_limit_is_retryable_for_backoff() -> None:
    request = httpx.Request("POST", "https://api.openai.com/v1/responses")
    response = httpx.Response(status_code=429, request=request)
    err = RateLimitError(
        "rate limit",
        response=response,
        body={"error": {"message": "rate limit"}},
    )

    assert _is_retryable_openai_exception(err)


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


def _runtime_config_for_parse(
    *, resolved_model: str = "gpt-5-mini"
) -> OpenAIRuntimeConfig:
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
        esco_vector_store_id=None,
        esco_rag_enabled=False,
        esco_rag_max_results=5,
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
        task_kind="test_structured_output",
    )


class _MiniOut(BaseModel):
    value: int


def test_parse_structured_outputs_retries_on_compatible_400(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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


def test_parse_structured_outputs_records_fallback_model_event(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeResponse:
        output_parsed = _MiniOut(value=9)
        usage = {"total_tokens": 7}

    class FakeResponses:
        def __init__(self) -> None:
            self.calls: list[dict[str, object]] = []

        def parse(self, **kwargs: object) -> FakeResponse:
            self.calls.append(kwargs)
            if kwargs.get("model") != "gpt-4o-mini":
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
    fake_session_state: dict[str, object] = {}

    monkeypatch.setattr("llm_client.get_openai_client", lambda settings: fake_client)
    monkeypatch.setattr("llm_client._has_any_openai_api_key", lambda settings: True)
    monkeypatch.setattr(
        "llm_client.st",
        SimpleNamespace(session_state=fake_session_state),
    )

    parsed, usage = _parse_with_structured_outputs(
        runtime_config=_runtime_config_for_parse(),
        messages=[{"role": "user", "content": "hi"}],
        out_model=_MiniOut,
        store=False,
    )

    parsed_model = _MiniOut.model_validate(parsed.model_dump())
    assert parsed_model.value == 9
    assert usage == {"total_tokens": 7}
    assert [call["model"] for call in fake_responses.calls] == [
        "gpt-5-mini",
        "gpt-5-mini",
        "gpt-4o-mini",
    ]
    assert fake_session_state[SSKey.USAGE_EVENTS.value][0]["event_type"] == (
        "fallback_model_used"
    )
    assert fake_session_state[SSKey.USAGE_EVENTS.value][0]["metadata"] == {
        "task_kind": "test_structured_output",
        "requested_model": "gpt-5-mini",
        "final_model": "gpt-4o-mini",
        "fallback_kind": "fallback_model",
        "endpoint": "responses.parse",
        "error_code": "OPENAI_BAD_REQUEST_STRUCTURED_OUTPUT_UNSUPPORTED",
    }
    assert fake_session_state[SSKey.USAGE_EVENTS.value][1]["event_type"] == (
        "openai_usage_recorded"
    )
    assert fake_session_state[SSKey.USAGE_EVENTS.value][1]["metadata"] == {
        "task_kind": "test_structured_output",
        "model": "gpt-4o-mini",
        "endpoint": "responses.parse",
        "parse_status": "ok",
        "total_tokens": 7,
        "cache_hit": False,
        "retry_category": "fallback_model",
    }


def test_parse_structured_outputs_records_openai_usage_event(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeResponse:
        id = "resp_test"
        model = "gpt-5-mini"
        output_parsed = _MiniOut(value=4)
        usage = {
            "input_tokens": 11,
            "output_tokens": 5,
            "total_tokens": 16,
            "input_tokens_details": {"cached_tokens": 7},
        }

    class FakeResponses:
        def parse(self, **_kwargs: object) -> FakeResponse:
            return FakeResponse()

    fake_client = type("Client", (), {"responses": FakeResponses()})()
    fake_session_state: dict[str, object] = {}

    monkeypatch.setattr("llm_client.get_openai_client", lambda settings: fake_client)
    monkeypatch.setattr("llm_client._has_any_openai_api_key", lambda settings: True)
    monkeypatch.setattr(
        "llm_client.st",
        SimpleNamespace(session_state=fake_session_state),
    )

    parsed, usage = _parse_with_structured_outputs(
        runtime_config=_runtime_config_for_parse(),
        messages=[{"role": "user", "content": "hi"}],
        out_model=_MiniOut,
        store=False,
    )

    assert _MiniOut.model_validate(parsed.model_dump()).value == 4
    assert usage == FakeResponse.usage
    assert fake_session_state[SSKey.USAGE_EVENTS.value][0]["event_type"] == (
        "openai_usage_recorded"
    )
    assert fake_session_state[SSKey.USAGE_EVENTS.value][0]["metadata"] == {
        "task_kind": "test_structured_output",
        "model": "gpt-5-mini",
        "endpoint": "responses.parse",
        "parse_status": "ok",
        "prompt_tokens": 11,
        "completion_tokens": 5,
        "total_tokens": 16,
        "cached_tokens": 7,
        "cache_hit": False,
        "retry_category": "none",
    }


def test_parse_structured_outputs_records_transport_retry_category(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeResponse:
        output_parsed = _MiniOut(value=5)
        usage = {"total_tokens": 9}

    class FakeResponses:
        def __init__(self) -> None:
            self.calls = 0

        def parse(self, **_kwargs: object) -> FakeResponse:
            self.calls += 1
            if self.calls == 1:
                request = httpx.Request("POST", "https://api.openai.com/v1/responses")
                response = httpx.Response(status_code=429, request=request)
                raise RateLimitError(
                    "rate limit",
                    response=response,
                    body={"error": {"message": "rate limit"}},
                )
            return FakeResponse()

    fake_responses = FakeResponses()
    fake_client = type("Client", (), {"responses": fake_responses})()
    fake_session_state: dict[str, object] = {}

    monkeypatch.setattr("llm_client.get_openai_client", lambda settings: fake_client)
    monkeypatch.setattr("llm_client._has_any_openai_api_key", lambda settings: True)
    monkeypatch.setattr("llm_client.time.sleep", lambda _seconds: None)
    monkeypatch.setattr(
        "llm_client.st",
        SimpleNamespace(session_state=fake_session_state),
    )

    parsed, usage = _parse_with_structured_outputs(
        runtime_config=_runtime_config_for_parse(),
        messages=[{"role": "user", "content": "hi"}],
        out_model=_MiniOut,
        store=False,
    )

    assert _MiniOut.model_validate(parsed.model_dump()).value == 5
    assert usage == {"total_tokens": 9}
    assert fake_responses.calls == 2
    assert fake_session_state[SSKey.USAGE_EVENTS.value][0]["metadata"] == {
        "task_kind": "test_structured_output",
        "model": "gpt-5-mini",
        "endpoint": "responses.parse",
        "parse_status": "ok",
        "total_tokens": 9,
        "cache_hit": False,
        "retry_category": "transport_retry",
    }


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
