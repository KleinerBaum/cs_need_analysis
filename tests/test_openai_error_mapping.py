from __future__ import annotations

import httpx
from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
)
from pydantic import BaseModel, ValidationError

from llm_client import (
    _error_from_openai_exception,
    _error_from_structured_output_exception,
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


def test_openai_400_maps_to_incompatible_parameter_message() -> None:
    request = httpx.Request("POST", "https://api.openai.com/v1/responses")
    response = httpx.Response(status_code=400, request=request)
    err = APIStatusError(
        "bad request",
        response=response,
        body={"error": {"message": "invalid_request_error"}},
    )

    mapped = _error_from_openai_exception(err, endpoint="responses.parse")
    assert "invalid openai parameters" in mapped.ui_message.lower()
    assert mapped.error_code == "OPENAI_BAD_REQUEST"


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
    assert mapped.error_code == "OPENAI_BAD_REQUEST"


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
