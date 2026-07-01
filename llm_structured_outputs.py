"""Structured-output parsing helpers for OpenAI calls."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Mapping,
    MutableMapping,
    Protocol,
    Sequence,
    Type,
    cast,
)

from pydantic import BaseModel

from constants import SSKey
from llm_error_mapping import (
    OpenAICallError,
    _STRUCTURED_OUTPUT_RETRYABLE_ERROR_CODES,
    _error_from_openai_exception,
    _error_from_structured_output_exception,
)
from llm_request_shapes import (
    build_chat_parse_request_kwargs,
    build_responses_request_kwargs,
)
from observability import log_model_call
from settings_openai import OpenAISettings
from usage_events import record_fallback_model_used, record_openai_usage

logger = logging.getLogger(__name__)


class StructuredOutputRuntimeConfig(Protocol):
    """Runtime settings needed by structured-output parsing."""

    resolved_model: str
    reasoning_effort: str | None
    verbosity: str | None
    timeout_seconds: float
    task_max_output_tokens: int | None
    task_max_bullets_per_field: int | None
    task_max_sentences_per_field: int | None
    settings: OpenAISettings
    task_kind: str | None


@dataclass(frozen=True)
class StructuredOutputDependencies:
    """Runtime dependencies supplied by the llm_client compatibility facade."""

    get_openai_client: Callable[..., Any]
    has_any_openai_api_key: Callable[[OpenAISettings], bool]
    raise_missing_api_key_hint: Callable[[], None]
    run_openai_call_with_retry: Callable[..., Any]
    session_state: MutableMapping[str, Any]


class ParsedResponse(Protocol):
    """Minimal protocol for Responses API parse return objects."""

    output_parsed: BaseModel
    usage: object | None


class _ParsedChatMessage(Protocol):
    parsed: BaseModel | None


class _ParsedChatChoice(Protocol):
    message: _ParsedChatMessage


class ParsedChatCompletion(Protocol):
    """Minimal protocol for chat.completions.parse return objects."""

    choices: Sequence[_ParsedChatChoice]
    usage: object | None


def _normalize_usage_dict(usage: object | None) -> dict[str, Any] | None:
    """Normalize SDK usage payloads to plain dictionaries."""

    if usage is None:
        return None
    if isinstance(usage, dict):
        return cast(dict[str, Any], usage)

    model_dump = getattr(usage, "model_dump", None)
    if callable(model_dump):
        dumped = model_dump(mode="python")
        if isinstance(dumped, dict):
            return cast(dict[str, Any], dumped)

    to_dict = getattr(usage, "to_dict", None)
    if callable(to_dict):
        dumped = to_dict()
        if isinstance(dumped, dict):
            return cast(dict[str, Any], dumped)

    return None


def _usage_token_count(usage: Mapping[str, Any], *keys: str) -> int | None:
    """Return the first available integer token count from normalized SDK usage."""

    for key in keys:
        value = usage.get(key)
        if isinstance(value, (int, float)):
            return max(0, int(value))
    return None


def _usage_cached_token_count(usage: Mapping[str, Any]) -> int | None:
    """Return provider-side cached input token count when the SDK exposes it."""

    for detail_key in ("input_tokens_details", "prompt_tokens_details"):
        details = usage.get(detail_key)
        if isinstance(details, Mapping):
            cached_tokens = _usage_token_count(details, "cached_tokens")
            if cached_tokens is not None:
                return cached_tokens
    return _usage_token_count(usage, "cached_tokens")


def _record_openai_usage_event(
    *,
    session_state: MutableMapping[str, Any],
    task_kind: str | None,
    endpoint: str,
    model_name: str | None,
    usage: object | None,
    parse_status: str,
    cache_hit: bool,
    retry_category: str | None,
    error_category: str | None,
) -> None:
    """Append one aggregate OpenAI usage event without prompts or payload contents."""

    usage_dict = _normalize_usage_dict(usage) or {}
    record_openai_usage(
        session_state,
        task_kind=task_kind or "structured_output",
        model=model_name or "unknown",
        endpoint=endpoint,
        parse_status=parse_status,
        prompt_tokens=_usage_token_count(usage_dict, "prompt_tokens", "input_tokens"),
        completion_tokens=_usage_token_count(
            usage_dict,
            "completion_tokens",
            "output_tokens",
        ),
        total_tokens=_usage_token_count(usage_dict, "total_tokens"),
        cached_tokens=_usage_cached_token_count(usage_dict),
        cache_hit=cache_hit,
        retry_category=retry_category or "none",
        error_category=error_category,
    )


def _response_request_id(response: object) -> str | None:
    """Return safe OpenAI request/response id metadata when available."""

    for attr in ("_request_id", "request_id", "id"):
        value = getattr(response, attr, None)
        if isinstance(value, str) and value:
            return value
    return None


def _usage_with_response_metadata(
    *,
    usage: object | None,
    response: object,
    endpoint: str,
    latency_ms: int,
) -> dict[str, Any]:
    """Attach non-sensitive request metadata to normalized usage payloads."""

    usage_dict = _normalize_usage_dict(usage) or {}
    response_id = getattr(response, "id", None)
    request_id = _response_request_id(response)
    usage_dict.update(
        {
            "endpoint": endpoint,
            "request_id": request_id,
            "response_id": response_id if isinstance(response_id, str) else None,
            "latency_ms": latency_ms,
        }
    )
    return usage_dict


def _log_openai_response_metadata(
    *,
    task_kind: str | None,
    endpoint: str,
    model_name: str | None,
    response: object,
    latency_ms: int,
    usage: object | None,
    retry_category: str = "none",
) -> None:
    """Log safe OpenAI request metadata without prompts or payload contents."""

    logger.info(
        "OpenAI request completed; task=%s endpoint=%s request_id=%s latency_ms=%d",
        task_kind or "structured_output",
        endpoint,
        _response_request_id(response),
        latency_ms,
    )
    usage_dict = _normalize_usage_dict(usage) or {}
    log_model_call(
        task_kind=task_kind,
        model=getattr(response, "model", None) or model_name,
        latency_ms=latency_ms,
        prompt_tokens=_usage_token_count(usage_dict, "prompt_tokens", "input_tokens"),
        completion_tokens=_usage_token_count(
            usage_dict,
            "completion_tokens",
            "output_tokens",
        ),
        cached_tokens=_usage_cached_token_count(usage_dict),
        cache_hit=False,
        endpoint=endpoint,
        retry_category=retry_category,
    )


def _record_final_structured_output_path(
    *,
    session_state: MutableMapping[str, Any],
    endpoint: str,
    requested_model: str,
    final_model: str,
    used_reduced_request: bool,
) -> None:
    payload = {
        "endpoint": endpoint,
        "requested_model": requested_model,
        "final_model": final_model,
        "used_reduced_request": used_reduced_request,
    }
    session_state[SSKey.OPENAI_LAST_STRUCTURED_OUTPUT_PATH.value] = payload


def _parse_with_structured_outputs(
    *,
    runtime_config: StructuredOutputRuntimeConfig,
    messages: List[Dict[str, Any]],
    out_model: Type[BaseModel],
    store: bool,
    dependencies: StructuredOutputDependencies,
    maybe_temperature: float | None = None,
    responses_instructions: str | None = None,
    responses_input: object | None = None,
    previous_response_id: str | None = None,
    include_response_metadata: bool = False,
) -> tuple[BaseModel, dict[str, Any] | None]:
    """Try `.responses.parse`, then fall back to `.chat.completions.parse` if needed."""

    def _build_reduced_responses_request_kwargs(*, model: str) -> dict[str, Any]:
        kwargs: dict[str, Any] = {"model": model, "store": store}
        if previous_response_id:
            kwargs["previous_response_id"] = previous_response_id
        return kwargs

    def _fallback_model_candidate() -> str | None:
        candidate = runtime_config.settings.default_model.strip()
        if candidate and candidate != runtime_config.resolved_model:
            return candidate
        return None

    settings = runtime_config.settings
    if not dependencies.has_any_openai_api_key(settings):
        dependencies.raise_missing_api_key_hint()

    client = dependencies.get_openai_client(settings=settings)
    responses_request_kwargs = build_responses_request_kwargs(
        model=runtime_config.resolved_model,
        store=store,
        maybe_temperature=maybe_temperature,
        reasoning_effort=runtime_config.reasoning_effort,
        verbosity=runtime_config.verbosity,
        max_output_tokens=runtime_config.task_max_output_tokens,
        previous_response_id=previous_response_id,
    )
    responses_input_payload = messages if responses_input is None else responses_input
    final_model_name = runtime_config.resolved_model
    retry_category = "none"
    transport_retried = False

    def _mark_transport_retry() -> None:
        nonlocal transport_retried
        transport_retried = True

    def _current_retry_category() -> str:
        if retry_category == "none" and transport_retried:
            return "transport_retry"
        return retry_category

    def _responses_parse_kwargs(
        request_kwargs: Mapping[str, Any],
    ) -> dict[str, Any]:
        parse_kwargs = {
            "input": responses_input_payload,
            "text_format": out_model,
            **dict(request_kwargs),
        }
        if responses_instructions is not None:
            parse_kwargs["instructions"] = responses_instructions
        return parse_kwargs

    # Newer SDK path (Responses API + parse helper)
    if hasattr(client, "responses") and hasattr(client.responses, "parse"):
        try:
            started = time.perf_counter()
            resp = dependencies.run_openai_call_with_retry(
                fn=lambda: client.responses.parse(
                    **_responses_parse_kwargs(responses_request_kwargs),
                ),
                label="OpenAI responses.parse",
                on_retry=_mark_transport_retry,
            )
            latency_ms = int((time.perf_counter() - started) * 1000)
            final_model_name = runtime_config.resolved_model
            retry_category = "none"
            _record_final_structured_output_path(
                session_state=dependencies.session_state,
                endpoint="responses.parse",
                requested_model=runtime_config.resolved_model,
                final_model=runtime_config.resolved_model,
                used_reduced_request=False,
            )
        except Exception as exc:
            if not dependencies.has_any_openai_api_key(settings):
                dependencies.raise_missing_api_key_hint()
            mapped = _error_from_openai_exception(exc, endpoint="responses.parse")
            if mapped.error_code in _STRUCTURED_OUTPUT_RETRYABLE_ERROR_CODES:
                reduced_kwargs = _build_reduced_responses_request_kwargs(
                    model=runtime_config.resolved_model
                )
                try:
                    started = time.perf_counter()
                    resp = dependencies.run_openai_call_with_retry(
                        fn=lambda: client.responses.parse(
                            **_responses_parse_kwargs(reduced_kwargs),
                        ),
                        label="OpenAI responses.parse reduced",
                        on_retry=_mark_transport_retry,
                    )
                    latency_ms = int((time.perf_counter() - started) * 1000)
                    final_model_name = runtime_config.resolved_model
                    retry_category = "reduced_request"
                    _record_final_structured_output_path(
                        session_state=dependencies.session_state,
                        endpoint="responses.parse",
                        requested_model=runtime_config.resolved_model,
                        final_model=runtime_config.resolved_model,
                        used_reduced_request=True,
                    )
                except Exception as retry_exc:
                    mapped_retry = _error_from_openai_exception(
                        retry_exc, endpoint="responses.parse"
                    )
                    fallback_model = _fallback_model_candidate()
                    if fallback_model is None:
                        logger.warning(
                            "OpenAI reduced parse failed: %s",
                            mapped_retry.debug_detail or type(retry_exc).__name__,
                        )
                        _record_openai_usage_event(
                            session_state=dependencies.session_state,
                            task_kind=runtime_config.task_kind,
                            endpoint="responses.parse",
                            model_name=runtime_config.resolved_model,
                            usage=None,
                            parse_status="error",
                            cache_hit=False,
                            retry_category="reduced_request",
                            error_category=mapped_retry.error_code,
                        )
                        raise mapped_retry from retry_exc
                    fallback_kwargs = _build_reduced_responses_request_kwargs(
                        model=fallback_model
                    )
                    try:
                        started = time.perf_counter()
                        resp = dependencies.run_openai_call_with_retry(
                            fn=lambda: client.responses.parse(
                                **_responses_parse_kwargs(fallback_kwargs),
                            ),
                            label="OpenAI responses.parse fallback-model",
                            on_retry=_mark_transport_retry,
                        )
                        latency_ms = int((time.perf_counter() - started) * 1000)
                        final_model_name = fallback_model
                        retry_category = "fallback_model"
                        _record_final_structured_output_path(
                            session_state=dependencies.session_state,
                            endpoint="responses.parse",
                            requested_model=runtime_config.resolved_model,
                            final_model=fallback_model,
                            used_reduced_request=True,
                        )
                        record_fallback_model_used(
                            dependencies.session_state,
                            task_kind=runtime_config.task_kind or "structured_output",
                            requested_model=runtime_config.resolved_model,
                            final_model=fallback_model,
                            fallback_kind="fallback_model",
                            endpoint="responses.parse",
                            error_code=mapped_retry.error_code,
                        )
                    except Exception as fallback_exc:
                        mapped_fallback = _error_from_openai_exception(
                            fallback_exc, endpoint="responses.parse"
                        )
                        logger.warning(
                            "OpenAI fallback-model parse failed: %s",
                            mapped_fallback.debug_detail or type(fallback_exc).__name__,
                        )
                        _record_openai_usage_event(
                            session_state=dependencies.session_state,
                            task_kind=runtime_config.task_kind,
                            endpoint="responses.parse",
                            model_name=fallback_model,
                            usage=None,
                            parse_status="error",
                            cache_hit=False,
                            retry_category="fallback_model",
                            error_category=mapped_fallback.error_code,
                        )
                        raise mapped_fallback from fallback_exc
            else:
                logger.warning(
                    "OpenAI parse failed: %s",
                    mapped.debug_detail or type(exc).__name__,
                )
                _record_openai_usage_event(
                    session_state=dependencies.session_state,
                    task_kind=runtime_config.task_kind,
                    endpoint="responses.parse",
                    model_name=runtime_config.resolved_model,
                    usage=None,
                    parse_status="error",
                    cache_hit=False,
                    retry_category=_current_retry_category(),
                    error_category=mapped.error_code,
                )
                raise mapped from exc

        try:
            parsed_response = cast(ParsedResponse, resp)
            parsed = parsed_response.output_parsed
            if not isinstance(parsed, BaseModel):
                raise TypeError("Structured output parse did not return a BaseModel.")
        except Exception as exc:
            mapped = _error_from_structured_output_exception(exc)
            logger.warning("Structured parse failed: %s", mapped.debug_detail)
            _record_openai_usage_event(
                session_state=dependencies.session_state,
                task_kind=runtime_config.task_kind,
                endpoint="responses.parse",
                model_name=getattr(resp, "model", None) or final_model_name,
                usage=getattr(resp, "usage", None),
                parse_status="error",
                cache_hit=False,
                retry_category=_current_retry_category(),
                error_category=mapped.error_code,
            )
            raise mapped from exc
        response_model_name = getattr(parsed_response, "model", None) or final_model_name
        _log_openai_response_metadata(
            task_kind=runtime_config.task_kind,
            endpoint="responses.parse",
            model_name=response_model_name,
            response=parsed_response,
            latency_ms=latency_ms,
            usage=parsed_response.usage,
            retry_category=_current_retry_category(),
        )
        _record_openai_usage_event(
            session_state=dependencies.session_state,
            task_kind=runtime_config.task_kind,
            endpoint="responses.parse",
            model_name=response_model_name,
            usage=parsed_response.usage,
            parse_status="ok",
            cache_hit=False,
            retry_category=_current_retry_category(),
            error_category=None,
        )
        usage = (
            _usage_with_response_metadata(
                usage=parsed_response.usage,
                response=parsed_response,
                endpoint="responses.parse",
                latency_ms=latency_ms,
            )
            if include_response_metadata
            else _normalize_usage_dict(parsed_response.usage)
        )
        return parsed, usage

    # Fallback: Chat Completions parse helper (older projects may still use it)
    if hasattr(client, "chat") and hasattr(client.chat.completions, "parse"):
        chat_request_kwargs = build_chat_parse_request_kwargs(
            model=runtime_config.resolved_model,
            maybe_temperature=maybe_temperature,
            reasoning_effort=runtime_config.reasoning_effort,
            verbosity=runtime_config.verbosity,
        )
        try:
            started = time.perf_counter()
            completion = dependencies.run_openai_call_with_retry(
                fn=lambda: client.chat.completions.parse(
                    messages=messages,
                    response_format=out_model,
                    **chat_request_kwargs,
                ),
                label="OpenAI chat.completions.parse",
                on_retry=_mark_transport_retry,
            )
            latency_ms = int((time.perf_counter() - started) * 1000)
            final_model_name = runtime_config.resolved_model
            retry_category = "none"
            _record_final_structured_output_path(
                session_state=dependencies.session_state,
                endpoint="chat.completions.parse",
                requested_model=runtime_config.resolved_model,
                final_model=runtime_config.resolved_model,
                used_reduced_request=False,
            )
        except Exception as exc:
            if not dependencies.has_any_openai_api_key(settings):
                dependencies.raise_missing_api_key_hint()
            mapped = _error_from_openai_exception(
                exc,
                endpoint="chat.completions.parse",
            )
            logger.warning(
                "OpenAI chat.parse failed: %s",
                mapped.debug_detail or type(exc).__name__,
            )
            _record_openai_usage_event(
                session_state=dependencies.session_state,
                task_kind=runtime_config.task_kind,
                endpoint="chat.completions.parse",
                model_name=runtime_config.resolved_model,
                usage=None,
                parse_status="error",
                cache_hit=False,
                retry_category=_current_retry_category(),
                error_category=mapped.error_code,
            )
            raise mapped from exc

        try:
            parsed_completion = cast(ParsedChatCompletion, completion)
            maybe_parsed = parsed_completion.choices[0].message.parsed
            if not isinstance(maybe_parsed, BaseModel):
                raise TypeError(
                    "Chat structured output parse did not return a BaseModel."
                )
            parsed = maybe_parsed
        except Exception as exc:
            mapped = _error_from_structured_output_exception(exc)
            logger.warning("Structured chat parse failed: %s", mapped.debug_detail)
            _record_openai_usage_event(
                session_state=dependencies.session_state,
                task_kind=runtime_config.task_kind,
                endpoint="chat.completions.parse",
                model_name=getattr(completion, "model", None) or final_model_name,
                usage=getattr(completion, "usage", None),
                parse_status="error",
                cache_hit=False,
                retry_category=_current_retry_category(),
                error_category=mapped.error_code,
            )
            raise mapped from exc
        usage = _normalize_usage_dict(parsed_completion.usage)
        response_model_name = getattr(parsed_completion, "model", final_model_name)
        log_model_call(
            task_kind=runtime_config.task_kind,
            model=response_model_name,
            latency_ms=latency_ms,
            prompt_tokens=_usage_token_count(
                usage or {},
                "prompt_tokens",
                "input_tokens",
            ),
            completion_tokens=_usage_token_count(
                usage or {},
                "completion_tokens",
                "output_tokens",
            ),
            cached_tokens=_usage_cached_token_count(usage or {}),
            cache_hit=False,
            endpoint="chat.completions.parse",
            retry_category=_current_retry_category(),
        )
        _record_openai_usage_event(
            session_state=dependencies.session_state,
            task_kind=runtime_config.task_kind,
            endpoint="chat.completions.parse",
            model_name=response_model_name,
            usage=parsed_completion.usage,
            parse_status="ok",
            cache_hit=False,
            retry_category=_current_retry_category(),
            error_category=None,
        )
        return parsed, usage

    raise OpenAICallError(
        "OpenAI-SDK inkompatibel (DE) / OpenAI SDK unsupported (EN).",
        debug_detail=(
            "endpoint=responses.parse|chat.completions.parse, "
            "exception=SDKFeatureMismatch"
        ),
        error_code="OPENAI_SDK_UNSUPPORTED",
    )
