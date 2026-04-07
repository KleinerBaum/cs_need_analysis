from __future__ import annotations

import httpx
from openai import APIStatusError, APITimeoutError, AuthenticationError
from pydantic import BaseModel, ValidationError

from llm_client import (
    _error_from_openai_exception,
    _error_from_structured_output_exception,
)


def test_openai_timeout_maps_to_concise_ui_message() -> None:
    request = httpx.Request("POST", "https://api.openai.com/v1/responses")
    err = APITimeoutError(request=request)

    mapped = _error_from_openai_exception(err)
    assert "timeout" in mapped.ui_message.lower()


def test_openai_400_maps_to_incompatible_parameter_message() -> None:
    request = httpx.Request("POST", "https://api.openai.com/v1/responses")
    response = httpx.Response(status_code=400, request=request)
    err = APIStatusError(
        "bad request",
        response=response,
        body={"error": {"message": "unsupported_parameter"}},
    )

    mapped = _error_from_openai_exception(err)
    assert "invalid openai parameters" in mapped.ui_message.lower()


def test_openai_auth_maps_to_authentication_message() -> None:
    request = httpx.Request("POST", "https://api.openai.com/v1/responses")
    response = httpx.Response(status_code=401, request=request)
    err = AuthenticationError("auth failed", response=response, body={})

    mapped = _error_from_openai_exception(err)
    assert "authentication failed" in mapped.ui_message.lower()


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
