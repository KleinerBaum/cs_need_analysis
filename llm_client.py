# llm_client.py
"""OpenAI API wrapper for this app.

Uses Structured Outputs via the OpenAI Python SDK `.responses.parse(...)` when available.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple, Type, cast

import streamlit as st
from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    OpenAI,
)
from pydantic import BaseModel, ConfigDict, ValidationError

from constants import (
    AnswerType,
    DEFAULT_LANGUAGE,
    JOB_AD_SCHEMA_VERSION,
    QUESTION_SCHEMA_VERSION,
    SSKey,
    VACANCY_SCHEMA_VERSION,
)
from model_capabilities import (
    is_gpt54_family,
    is_gpt5_legacy_model,
    is_nano_model,
    normalize_reasoning_effort,
    supports_reasoning,
    supports_temperature,
    supports_verbosity,
)
from schemas import (
    JobAdExtract,
    QuestionDependency,
    QuestionPlan,
    VacancyBrief,
    VacancyBriefLLM,
)
from settings_openai import OpenAISettings, load_openai_settings

logger = logging.getLogger(__name__)

# Re-exported for backwards-compatible imports and lightweight diagnostics.
_MODEL_CAPABILITY_EXPORTS = (
    is_gpt5_legacy_model,
    is_gpt54_family,
    is_nano_model,
    supports_reasoning,
    supports_verbosity,
)


ModelTaskKind = str
TASK_EXTRACT_JOB_AD = "extract_job_ad"
TASK_GENERATE_QUESTION_PLAN = "generate_question_plan"
TASK_GENERATE_VACANCY_BRIEF = "generate_vacancy_brief"
TASK_GENERATE_JOB_AD = "generate_job_ad"

_OTHER_OPTION = "Sonstiges"
_CATEGORY_QUESTION_RULES: tuple[dict[str, Any], ...] = (
    {
        "terms": ("hard skills",),
        "answer_type": AnswerType.MULTI_SELECT,
        "options": (
            "Python",
            "Java",
            "SQL",
            "Cloud",
            "Datenanalyse",
            _OTHER_OPTION,
        ),
    },
    {
        "terms": ("soft skills",),
        "answer_type": AnswerType.MULTI_SELECT,
        "options": (
            "Kommunikation",
            "Teamfähigkeit",
            "Eigenverantwortung",
            "Stakeholder-Management",
            "Problemlösung",
            _OTHER_OPTION,
        ),
    },
    {
        "terms": ("sprachen",),
        "answer_type": AnswerType.MULTI_SELECT,
        "options": ("Deutsch", "Englisch", "Französisch", "Spanisch", _OTHER_OPTION),
    },
    {
        "terms": ("seniority",),
        "answer_type": AnswerType.SINGLE_SELECT,
        "options": ("Junior", "Mid-Level", "Senior", "Lead", _OTHER_OPTION),
    },
    {
        "terms": ("tools",),
        "answer_type": AnswerType.MULTI_SELECT,
        "options": ("Jira", "Confluence", "GitHub", "Salesforce", "SAP", _OTHER_OPTION),
    },
    {
        "terms": ("arbeitsmodell",),
        "answer_type": AnswerType.SINGLE_SELECT,
        "options": ("Vor Ort", "Hybrid", "Remote", _OTHER_OPTION),
    },
)

_NUMERIC_QUESTION_RULES: tuple[dict[str, Any], ...] = (
    {
        "terms": ("jahre", "years", "berufserfahrung", "experience"),
        "bounds": (0.0, 30.0, 1.0),
    },
    {
        "terms": ("anzahl", "number", "headcount", "fte", "teamgröße", "teamgroesse"),
        "bounds": (0.0, 500.0, 1.0),
    },
    {
        "terms": ("tage", "days", "pro woche", "per week"),
        "bounds": (0.0, 7.0, 1.0),
    },
    {
        "terms": ("prozent", "%", "percentage"),
        "bounds": (0.0, 100.0, 1.0),
    },
    {
        "terms": ("gehalt", "salary", "budget", "compensation"),
        "bounds": (20_000.0, 500_000.0, 1_000.0),
    },
)
_QUESTION_PRIORITY_VALUES = {"core", "standard", "detail"}


class VacancyBriefCriticalSections(BaseModel):
    """Subset schema for optional quality upgrades on critical sections only."""

    model_config = ConfigDict(extra="forbid")

    evaluation_rubric: list[str]
    risks_open_questions: list[str]


class JobAdGenerationResult(BaseModel):
    """Strict schema for user-tailored job ad generation."""

    model_config = ConfigDict(extra="forbid")

    headline: str
    target_group: list[str]
    agg_checklist: list[str]
    job_ad_text: str


@dataclass(frozen=True)
class OpenAIRuntimeConfig:
    """Resolved runtime configuration for a single LLM task call chain."""

    resolved_model: str
    reasoning_effort: str | None
    verbosity: str | None
    timeout_seconds: float
    task_max_output_tokens: int | None
    task_max_bullets_per_field: int | None
    task_max_sentences_per_field: int | None
    settings: OpenAISettings


def _resolve_runtime_config(
    *,
    task_kind: ModelTaskKind,
    session_override: str | None,
) -> OpenAIRuntimeConfig:
    """Resolve model and OpenAI settings exactly once per task invocation."""

    settings = load_openai_settings()
    resolved_model = resolve_model_for_task(
        task_kind=task_kind,
        session_override=session_override,
        settings=settings,
    )
    return OpenAIRuntimeConfig(
        resolved_model=resolved_model,
        reasoning_effort=settings.reasoning_effort,
        verbosity=settings.verbosity,
        timeout_seconds=settings.openai_request_timeout,
        task_max_output_tokens=settings.task_max_output_tokens.get(task_kind),
        task_max_bullets_per_field=settings.task_max_bullets_per_field.get(task_kind),
        task_max_sentences_per_field=settings.task_max_sentences_per_field.get(
            task_kind
        ),
        settings=settings,
    )


def build_task_prompt_limits_suffix(
    *,
    max_bullets_per_field: int | None,
    max_sentences_per_field: int | None,
    max_output_tokens: int | None,
) -> str:
    """Build strict task-level prompt limits from runtime configuration."""

    parts: list[str] = []
    if max_bullets_per_field is not None:
        parts.append(f"Maximal {max_bullets_per_field} Bulletpoints pro Listenfeld.")
    if max_sentences_per_field is not None:
        parts.append(f"Maximal {max_sentences_per_field} Sätze pro Textfeld.")
    if max_output_tokens is not None:
        parts.append(
            "Bei knappem Budget priorisiere Pflichtfelder mit hoher Hiring-Relevanz; "
            "fülle Nice-to-have nur bei verbleibendem Budget."
        )
    if not parts:
        return ""
    return " Zusätzliche Output-Limits: " + " ".join(parts)


class OpenAICallError(RuntimeError):
    """Application-level error with user-facing and debug-safe details."""

    def __init__(
        self,
        ui_message: str,
        *,
        debug_detail: str | None = None,
        error_code: str | None = None,
    ) -> None:
        super().__init__(ui_message)
        self.ui_message = ui_message
        self.debug_detail = debug_detail
        self.error_code = error_code


_STRUCTURED_OUTPUT_RETRYABLE_ERROR_CODES = frozenset(
    {
        "OPENAI_BAD_REQUEST_STRUCTURED_OUTPUT_UNSUPPORTED",
        "OPENAI_BAD_REQUEST_MODEL_CAPABILITY",
        "OPENAI_BAD_REQUEST_ENDPOINT_INCOMPATIBLE",
    }
)


def build_extract_job_ad_messages(
    job_text: str,
    language: str = DEFAULT_LANGUAGE,
    model: str | None = None,
) -> list[dict[str, str]]:
    """Build the standardized message list for job-ad extraction."""

    guardrails = build_small_model_guardrails(model or "")
    system = (
        "Du bist ein Senior HR / Recruiting Analyst. "
        "Extrahiere aus einem Jobspec/Job Ad alle recruitment-relevanten Informationen "
        "und normalisiere sie in ein strukturiertes JSON, ohne Halluzinationen. "
        "Wenn etwas nicht explizit vorkommt oder nicht sicher ableitbar ist: setze null/leer und schreibe es in 'gaps'. "
        "Wenn du Annahmen triffst: dokumentiere sie in 'assumptions'. "
        f"Antworte in der Sprache: {language}."
        f"{guardrails}"
    )

    user = (
        "Analysiere folgenden Text (Jobspec/Job Ad). "
        "Behalte Formulierungen aus dem Original, wo sinnvoll.\n\n"
        "=== JOBSPEC START ===\n"
        f"{job_text}\n"
        "=== JOBSPEC END ==="
    )

    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


def build_small_model_guardrails(model: str) -> str:
    """Return minimal strict-output guardrails for selected nano models."""

    normalized_model = model.strip().lower()
    if normalized_model not in {"gpt-5-nano", "gpt-5.4-nano"}:
        return ""

    return (
        " Für kleine Modelle strikt befolgen: "
        "1) Nur strukturierte Ausgabe gemäß Schema. "
        "2) Kein Zusatztext außerhalb des Schemas. "
        "3) Keine impliziten Nebenaufgaben. "
        "4) Fehlende Infos leer/null statt geraten."
    )


def normalize_verbosity(verbosity: str | None) -> str | None:
    """Normalize verbosity values and drop unsupported inputs."""

    if verbosity is None:
        return None

    normalized_verbosity = verbosity.strip().lower()
    if normalized_verbosity in {"low", "medium", "high"}:
        return normalized_verbosity

    return None


def _build_capability_gated_request_kwargs(
    *,
    model: str,
    maybe_temperature: float | None = None,
    reasoning_effort: str | None,
    verbosity: str | None,
) -> dict[str, Any]:
    """Build capability-gated kwargs shared across parse endpoints."""

    normalized_reasoning_effort = normalize_reasoning_effort(model, reasoning_effort)
    normalized_verbosity = normalize_verbosity(verbosity)

    request_kwargs: dict[str, Any] = {}
    if maybe_temperature is not None and supports_temperature(
        model, normalized_reasoning_effort
    ):
        request_kwargs["temperature"] = maybe_temperature
    if supports_reasoning(model) and normalized_reasoning_effort is not None:
        request_kwargs["reasoning"] = {"effort": normalized_reasoning_effort}
    if supports_verbosity(model) and normalized_verbosity is not None:
        request_kwargs["text"] = {"verbosity": normalized_verbosity}

    return request_kwargs


def build_responses_request_kwargs(
    *,
    model: str,
    store: bool,
    maybe_temperature: float | None = None,
    reasoning_effort: str | None,
    verbosity: str | None,
    max_output_tokens: int | None = None,
) -> dict[str, Any]:
    """Build kwargs for `responses.parse` with endpoint-specific fields."""

    request_kwargs: dict[str, Any] = {"model": model, "store": store}
    if max_output_tokens is not None:
        request_kwargs["max_output_tokens"] = max_output_tokens
    request_kwargs.update(
        _build_capability_gated_request_kwargs(
            model=model,
            maybe_temperature=maybe_temperature,
            reasoning_effort=reasoning_effort,
            verbosity=verbosity,
        )
    )
    return request_kwargs


def build_chat_parse_request_kwargs(
    *,
    model: str,
    maybe_temperature: float | None = None,
    reasoning_effort: str | None,
    verbosity: str | None,
) -> dict[str, Any]:
    """Build kwargs for `chat.completions.parse` without responses-only fields."""

    request_kwargs: dict[str, Any] = {"model": model}
    request_kwargs.update(
        _build_capability_gated_request_kwargs(
            model=model,
            maybe_temperature=maybe_temperature,
            reasoning_effort=reasoning_effort,
            verbosity=verbosity,
        )
    )
    return request_kwargs


def _build_openai_client(settings: OpenAISettings) -> OpenAI:
    """Create an OpenAI SDK client from normalized app settings."""

    timeout = settings.openai_request_timeout
    if settings.openai_api_key:
        return OpenAI(api_key=settings.openai_api_key, timeout=timeout)

    # Allow OpenAI SDK default env var fallback handling.
    return OpenAI(timeout=timeout)


def _build_openai_client_from_runtime_settings(
    *,
    timeout_seconds: float,
    explicit_api_key: str | None,
) -> OpenAI:
    """Create an OpenAI SDK client from runtime cache key inputs."""

    if explicit_api_key:
        return OpenAI(api_key=explicit_api_key, timeout=timeout_seconds)
    return OpenAI(timeout=timeout_seconds)


@st.cache_resource
def _get_cached_openai_client(
    timeout_seconds: float,
    api_key_hash: str,
    has_any_api_key: bool,
    _explicit_api_key: str | None = None,
) -> OpenAI:
    """Return cached OpenAI client keyed by non-sensitive runtime fingerprint."""

    # Keep these parameters explicit for deterministic cache invalidation.
    _ = (api_key_hash, has_any_api_key)
    return _build_openai_client_from_runtime_settings(
        timeout_seconds=timeout_seconds,
        explicit_api_key=_explicit_api_key,
    )


def get_openai_client(*, settings: OpenAISettings | None = None) -> OpenAI:
    """Create a cached OpenAI client.

    Priority for API key:
    1) st.secrets["OPENAI_API_KEY"] (common in Streamlit deployments)
    2) Environment variable OPENAI_API_KEY (local dev / CI)
    """
    settings = settings or load_openai_settings()
    resolved_api_key = settings.openai_api_key or os.getenv("OPENAI_API_KEY")
    has_any_api_key = bool(resolved_api_key)
    api_key_hash = _safe_hash(resolved_api_key) if resolved_api_key else "missing"

    return _get_cached_openai_client(
        timeout_seconds=settings.openai_request_timeout,
        api_key_hash=api_key_hash,
        has_any_api_key=has_any_api_key,
        _explicit_api_key=settings.openai_api_key,
    )


def _has_any_openai_api_key(settings: OpenAISettings) -> bool:
    """Check whether a key is present via app settings or SDK env fallback."""

    return bool(settings.openai_api_key or os.getenv("OPENAI_API_KEY"))


def _raise_missing_api_key_hint() -> None:
    """Raise a clear message for UI and logs without exposing secrets."""

    raise OpenAICallError(
        "OpenAI API-Key fehlt (DE) / Missing OpenAI API key (EN).",
        debug_detail="No OPENAI_API_KEY found in st.secrets or environment.",
        error_code="OPENAI_AUTH",
    )


def _safe_hash(text: str, n: int = 10) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:n]


def _canonicalize_for_cache(value: Any) -> str:
    """Return deterministic JSON text for cache-key inputs."""

    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _get_session_response_cache() -> dict[str, dict[str, Any]]:
    """Return mutable in-session LLM response cache bucket."""

    cache_key = SSKey.LLM_RESPONSE_CACHE.value
    cache = st.session_state.get(cache_key)
    if not isinstance(cache, dict):
        cache = {}
        st.session_state[cache_key] = cache
    return cache


def _build_llm_cache_key(
    *,
    task_kind: str,
    resolved_model: str,
    language: str,
    reasoning_effort: str | None,
    verbosity: str | None,
    store: bool,
    normalized_content: str,
    schema_version: str | None = None,
) -> str:
    """Build a stable cache key from model-relevant inputs."""

    key_payload = {
        "task_kind": task_kind,
        "resolved_model": resolved_model,
        "language": language.strip().lower(),
        "reasoning_effort": normalize_reasoning_effort(
            resolved_model, reasoning_effort
        ),
        "verbosity": normalize_verbosity(verbosity),
        "store": bool(store),
        "normalized_content": normalized_content,
        "schema_version": schema_version,
    }
    return hashlib.sha256(
        _canonicalize_for_cache(key_payload).encode("utf-8")
    ).hexdigest()


def _cached_usage(*, cache_key: str) -> dict[str, Any]:
    """Return standardized usage metadata for cache hits."""

    return {
        "cached": True,
        "cache_key": cache_key,
        "provider": "session_state",
    }


def _invalidate_cache_entry_for_validation_error(
    *,
    cache: dict[str, dict[str, Any]],
    cache_key: str,
    task_kind: str,
    model_name: str,
) -> None:
    """Drop invalid cached payloads after schema validation failures."""

    cache.pop(cache_key, None)
    logger.warning(
        "Invalid cached LLM response removed; recomputing. task=%s model=%s cache_key=%s",
        task_kind,
        model_name,
        _safe_hash(cache_key),
    )


def _error_from_openai_exception(exc: Exception, *, endpoint: str) -> OpenAICallError:
    """Convert SDK exceptions into concise, user-safe app errors."""
    status_code = getattr(exc, "status_code", None)

    def _extract_api_error_message() -> str:
        """Extract nested API error messages from OpenAI SDK exceptions."""

        body = getattr(exc, "body", None)
        if isinstance(body, dict):
            error_obj = body.get("error")
            if isinstance(error_obj, dict):
                message = error_obj.get("message")
                if isinstance(message, str):
                    return message
            elif isinstance(error_obj, str):
                return error_obj
            message = body.get("message")
            if isinstance(message, str):
                return message

        error_attr = getattr(exc, "error", None)
        if isinstance(error_attr, dict):
            message = error_attr.get("message")
            if isinstance(message, str):
                return message

        return ""

    def _sanitize_api_message(message: str, *, max_len: int = 200) -> str:
        """Mask likely sensitive fragments and keep message compact."""

        collapsed = " ".join(message.split())
        redacted = re.sub(
            r"(?i)\b(sk-[A-Za-z0-9_-]{8,})\b", "[redacted-key]", collapsed
        )
        redacted = re.sub(
            r"(?i)\bbearer\s+[A-Za-z0-9._-]+", "Bearer [redacted]", redacted
        )
        redacted = re.sub(
            r"(?i)\b(api[_-]?key|token|secret|password)\s*[:=]\s*[^,;\s]+",
            r"\1=[redacted]",
            redacted,
        )

        if len(redacted) <= max_len:
            return redacted
        return f"{redacted[: max_len - 1].rstrip()}…"

    api_message_raw = _extract_api_error_message()
    api_message_sanitized = (
        _sanitize_api_message(api_message_raw) if api_message_raw else ""
    )
    api_message_norm = api_message_sanitized.lower()

    def _debug_detail() -> str:
        details = [f"endpoint={endpoint}", f"exception={type(exc).__name__}"]
        if status_code is not None:
            details.append(f"status_code={status_code}")
        if api_message_sanitized:
            details.append(f"api_message={api_message_sanitized}")
        return ", ".join(details)

    def _classify_bad_request() -> tuple[str, str]:
        """Return ``(error_code, ui_message)`` for common 400 API causes."""

        message = api_message_norm
        model_not_found_hint = (
            "model not found" in message or "unknown model" in message
        )
        endpoint_incompatibility_hint = (
            "endpoint" in message
            and ("not supported" in message or "incompatible" in message)
        ) or (
            "use /v1/chat/completions" in message
            or "use /v1/responses" in message
            or "responses api" in message
            or "chat.completions" in message
        )
        structured_output_hint = (
            "response_format" in message
            or "text_format" in message
            or "structured output" in message
            or "json_schema" in message
            or "json schema" in message
        ) and (
            "unsupported" in message
            or "not supported" in message
            or "unknown parameter" in message
            or "not allowed" in message
            or "invalid" in message
        )
        model_capability_hint = (
            "does not support" in message
            or "unsupported for model" in message
            or "model capability" in message
            or "not available for this model" in message
        ) and (
            "temperature" in message
            or "reasoning" in message
            or "verbosity" in message
            or "response_format" in message
            or "text_format" in message
            or "json_schema" in message
            or "max_output_tokens" in message
        )
        unsupported_hint = (
            "unsupported parameter" in message
            or "unknown parameter" in message
            or "not allowed" in message
            or "invalid type" in message
        )

        if model_not_found_hint:
            return (
                "OPENAI_BAD_REQUEST_MODEL_NOT_FOUND",
                "OpenAI-Modell nicht gefunden (DE) / OpenAI model not found (EN).",
            )
        if endpoint_incompatibility_hint:
            return (
                "OPENAI_BAD_REQUEST_ENDPOINT_INCOMPATIBLE",
                "OpenAI-Endpoint inkompatibel (DE) / Incompatible OpenAI endpoint (EN).",
            )
        if structured_output_hint:
            return (
                "OPENAI_BAD_REQUEST_STRUCTURED_OUTPUT_UNSUPPORTED",
                "Structured Output nicht unterstützt (DE) / Structured output unsupported (EN).",
            )
        if model_capability_hint:
            return (
                "OPENAI_BAD_REQUEST_MODEL_CAPABILITY",
                "OpenAI-Modellfähigkeit passt nicht (DE) / OpenAI model capability mismatch (EN).",
            )
        if unsupported_hint:
            return (
                "OPENAI_BAD_REQUEST_UNSUPPORTED_PARAMETER",
                "Nicht unterstützter OpenAI-Parameter (DE) / Unsupported OpenAI parameter (EN).",
            )
        return (
            "OPENAI_BAD_REQUEST_INVALID",
            "Ungültige OpenAI-Parameter (DE) / Invalid OpenAI parameters (EN).",
        )

    if isinstance(exc, (APITimeoutError, TimeoutError)):
        return OpenAICallError(
            "OpenAI-Timeout (DE) / OpenAI timeout (EN). Bitte erneut versuchen.",
            debug_detail=_debug_detail(),
            error_code="OPENAI_TIMEOUT",
        )

    if isinstance(exc, APIStatusError) and exc.status_code == 400:
        error_code, ui_message = _classify_bad_request()
        return OpenAICallError(
            ui_message,
            debug_detail=_debug_detail(),
            error_code=error_code,
        )

    if isinstance(exc, AuthenticationError):
        return OpenAICallError(
            "OpenAI-Authentifizierung fehlgeschlagen (DE) / OpenAI authentication failed (EN).",
            debug_detail=_debug_detail(),
            error_code="OPENAI_AUTH",
        )

    if isinstance(exc, APIConnectionError):
        return OpenAICallError(
            "OpenAI-Verbindung fehlgeschlagen (DE) / OpenAI connection failed (EN).",
            debug_detail=_debug_detail(),
            error_code="OPENAI_CONNECTION",
        )

    return OpenAICallError(
        "OpenAI-Aufruf fehlgeschlagen (DE) / OpenAI request failed (EN).",
        debug_detail=_debug_detail(),
        error_code="OPENAI_UNKNOWN",
    )


def _error_from_structured_output_exception(exc: Exception) -> OpenAICallError:
    """Map schema/validation failures to user-safe structured-output messages."""

    if isinstance(exc, ValidationError):
        return OpenAICallError(
            "Antwortformat ungültig (DE) / Invalid structured output (EN).",
            debug_detail="Pydantic validation failed for structured output.",
            error_code="OPENAI_PARSE",
        )

    return OpenAICallError(
        "Structured Output fehlgeschlagen (DE) / Structured output failed (EN).",
        debug_detail=f"Structured output parsing error: {type(exc).__name__}.",
        error_code="OPENAI_PARSE",
    )


def _is_retryable_openai_exception(exc: Exception) -> bool:
    """Return True for transient errors worth retrying."""

    return isinstance(exc, (APITimeoutError, TimeoutError, APIConnectionError))


def _run_openai_call_with_retry(
    *,
    fn: Callable[[], Any],
    label: str,
    max_attempts: int = 3,
    base_delay_seconds: float = 0.4,
) -> Any:
    """Run OpenAI call with exponential backoff for transient errors."""

    for attempt in range(1, max_attempts + 1):
        try:
            return fn()
        except Exception as exc:
            if not _is_retryable_openai_exception(exc) or attempt >= max_attempts:
                raise
            delay = base_delay_seconds * (2 ** (attempt - 1))
            logger.warning(
                "%s transient error (%s), retrying in %.2fs (%d/%d).",
                label,
                type(exc).__name__,
                delay,
                attempt,
                max_attempts,
            )
            time.sleep(delay)


def resolve_model_for_task(
    *,
    task_kind: ModelTaskKind,
    session_override: str | None,
    settings: OpenAISettings | None = None,
) -> str:
    """Resolve a model via session/global/task/default/final fallback priority."""

    resolved_settings = settings or load_openai_settings()
    trimmed_session_override = (session_override or "").strip()
    if trimmed_session_override:
        return trimmed_session_override

    if resolved_settings.openai_model_override:
        return resolved_settings.openai_model_override.strip()

    model_by_task: dict[ModelTaskKind, str] = {
        TASK_EXTRACT_JOB_AD: resolved_settings.lightweight_model,
        TASK_GENERATE_QUESTION_PLAN: resolved_settings.medium_reasoning_model,
        TASK_GENERATE_VACANCY_BRIEF: resolved_settings.medium_reasoning_model,
        TASK_GENERATE_JOB_AD: resolved_settings.high_reasoning_model,
    }
    routed_model = model_by_task.get(task_kind, "").strip()
    if routed_model:
        return routed_model

    fallback_model = resolved_settings.default_model.strip()
    if fallback_model:
        return fallback_model

    return "gpt-4o-mini"


def _parse_with_structured_outputs(
    *,
    runtime_config: OpenAIRuntimeConfig,
    messages: List[Dict[str, Any]],
    out_model: Type[BaseModel],
    store: bool,
    maybe_temperature: float | None = None,
) -> Tuple[BaseModel, Optional[Dict[str, Any]]]:
    """Try `.responses.parse`, then fall back to `.chat.completions.parse` if needed."""

    def _record_final_structured_output_path(
        *,
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
        st.session_state[SSKey.OPENAI_LAST_STRUCTURED_OUTPUT_PATH.value] = payload

    def _build_reduced_responses_request_kwargs(*, model: str) -> dict[str, Any]:
        return {"model": model, "store": store}

    def _fallback_model_candidate() -> str | None:
        candidate = runtime_config.settings.default_model.strip()
        if candidate and candidate != runtime_config.resolved_model:
            return candidate
        return None

    settings = runtime_config.settings
    if not _has_any_openai_api_key(settings):
        _raise_missing_api_key_hint()

    client = get_openai_client(settings=settings)
    responses_request_kwargs = build_responses_request_kwargs(
        model=runtime_config.resolved_model,
        store=store,
        maybe_temperature=maybe_temperature,
        reasoning_effort=runtime_config.reasoning_effort,
        verbosity=runtime_config.verbosity,
        max_output_tokens=runtime_config.task_max_output_tokens,
    )

    # Newer SDK path (Responses API + parse helper)
    if hasattr(client, "responses") and hasattr(client.responses, "parse"):
        try:
            resp = _run_openai_call_with_retry(
                fn=lambda: client.responses.parse(
                    input=messages,
                    text_format=out_model,
                    **responses_request_kwargs,
                ),
                label="OpenAI responses.parse",
            )
            _record_final_structured_output_path(
                endpoint="responses.parse",
                requested_model=runtime_config.resolved_model,
                final_model=runtime_config.resolved_model,
                used_reduced_request=False,
            )
        except Exception as exc:
            if not _has_any_openai_api_key(settings):
                _raise_missing_api_key_hint()
            mapped = _error_from_openai_exception(exc, endpoint="responses.parse")
            if mapped.error_code in _STRUCTURED_OUTPUT_RETRYABLE_ERROR_CODES:
                reduced_kwargs = _build_reduced_responses_request_kwargs(
                    model=runtime_config.resolved_model
                )
                try:
                    resp = _run_openai_call_with_retry(
                        fn=lambda: client.responses.parse(
                            input=messages,
                            text_format=out_model,
                            **reduced_kwargs,
                        ),
                        label="OpenAI responses.parse reduced",
                    )
                    _record_final_structured_output_path(
                        endpoint="responses.parse",
                        requested_model=runtime_config.resolved_model,
                        final_model=runtime_config.resolved_model,
                        used_reduced_request=True,
                    )
                except Exception as retry_exc:
                    fallback_model = _fallback_model_candidate()
                    if fallback_model is None:
                        mapped_retry = _error_from_openai_exception(
                            retry_exc, endpoint="responses.parse"
                        )
                        logger.warning(
                            "OpenAI reduced parse failed: %s",
                            mapped_retry.debug_detail or type(retry_exc).__name__,
                        )
                        raise mapped_retry from retry_exc
                    fallback_kwargs = _build_reduced_responses_request_kwargs(
                        model=fallback_model
                    )
                    try:
                        resp = _run_openai_call_with_retry(
                            fn=lambda: client.responses.parse(
                                input=messages,
                                text_format=out_model,
                                **fallback_kwargs,
                            ),
                            label="OpenAI responses.parse fallback-model",
                        )
                        _record_final_structured_output_path(
                            endpoint="responses.parse",
                            requested_model=runtime_config.resolved_model,
                            final_model=fallback_model,
                            used_reduced_request=True,
                        )
                    except Exception as fallback_exc:
                        mapped_fallback = _error_from_openai_exception(
                            fallback_exc, endpoint="responses.parse"
                        )
                        logger.warning(
                            "OpenAI fallback-model parse failed: %s",
                            mapped_fallback.debug_detail or type(fallback_exc).__name__,
                        )
                        raise mapped_fallback from fallback_exc
            else:
                logger.warning(
                    "OpenAI parse failed: %s",
                    mapped.debug_detail or type(exc).__name__,
                )
                raise mapped from exc

        try:
            parsed = resp.output_parsed
        except Exception as exc:
            mapped = _error_from_structured_output_exception(exc)
            logger.warning("Structured parse failed: %s", mapped.debug_detail)
            raise mapped from exc
        usage = getattr(resp, "usage", None)
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
            completion = _run_openai_call_with_retry(
                fn=lambda: client.chat.completions.parse(
                    messages=messages,
                    response_format=out_model,
                    **chat_request_kwargs,
                ),
                label="OpenAI chat.completions.parse",
            )
            _record_final_structured_output_path(
                endpoint="chat.completions.parse",
                requested_model=runtime_config.resolved_model,
                final_model=runtime_config.resolved_model,
                used_reduced_request=False,
            )
        except Exception as exc:
            if not _has_any_openai_api_key(settings):
                _raise_missing_api_key_hint()
            mapped = _error_from_openai_exception(
                exc,
                endpoint="chat.completions.parse",
            )
            logger.warning(
                "OpenAI chat.parse failed: %s",
                mapped.debug_detail or type(exc).__name__,
            )
            raise mapped from exc

        try:
            parsed = completion.choices[0].message.parsed
        except Exception as exc:
            mapped = _error_from_structured_output_exception(exc)
            logger.warning("Structured chat parse failed: %s", mapped.debug_detail)
            raise mapped from exc
        usage = getattr(completion, "usage", None)
        return parsed, usage

    raise OpenAICallError(
        "OpenAI-SDK inkompatibel (DE) / OpenAI SDK unsupported (EN).",
        debug_detail=(
            "endpoint=responses.parse|chat.completions.parse, "
            "exception=SDKFeatureMismatch"
        ),
        error_code="OPENAI_SDK_UNSUPPORTED",
    )


def extract_job_ad(
    job_text: str,
    *,
    model: str,
    language: str = DEFAULT_LANGUAGE,
    store: bool = False,
    temperature: float | None = None,
) -> Tuple[JobAdExtract, Optional[Dict[str, Any]]]:
    runtime_config = _resolve_runtime_config(
        task_kind=TASK_EXTRACT_JOB_AD,
        session_override=model,
    )
    messages = build_extract_job_ad_messages(
        job_text,
        language,
        model=runtime_config.resolved_model,
    )
    prompt_limits = build_task_prompt_limits_suffix(
        max_bullets_per_field=runtime_config.task_max_bullets_per_field,
        max_sentences_per_field=runtime_config.task_max_sentences_per_field,
        max_output_tokens=runtime_config.task_max_output_tokens,
    )
    if prompt_limits:
        messages[0]["content"] = f"{messages[0]['content']}{prompt_limits}"
    normalized_content = _canonicalize_for_cache({"job_text": job_text})
    cache_key = _build_llm_cache_key(
        task_kind=TASK_EXTRACT_JOB_AD,
        resolved_model=runtime_config.resolved_model,
        language=language,
        reasoning_effort=runtime_config.reasoning_effort,
        verbosity=runtime_config.verbosity,
        store=store,
        normalized_content=normalized_content,
        schema_version=JOB_AD_SCHEMA_VERSION,
    )
    cache = _get_session_response_cache()
    cached_entry = cache.get(cache_key)
    if isinstance(cached_entry, dict):
        cached_result = cached_entry.get("result")
        if isinstance(cached_result, dict):
            try:
                parsed_cached = JobAdExtract.model_validate(cached_result)
            except ValidationError:
                _invalidate_cache_entry_for_validation_error(
                    cache=cache,
                    cache_key=cache_key,
                    task_kind=TASK_EXTRACT_JOB_AD,
                    model_name=runtime_config.resolved_model,
                )
            else:
                return parsed_cached, _cached_usage(cache_key=cache_key)

    parsed, usage = _parse_with_structured_outputs(
        runtime_config=runtime_config,
        messages=messages,
        out_model=JobAdExtract,
        store=store,
        maybe_temperature=temperature,
    )
    cache[cache_key] = {"result": parsed.model_dump(mode="json")}

    return parsed, usage


def generate_question_plan(
    job: JobAdExtract,
    *,
    model: str,
    language: str = DEFAULT_LANGUAGE,
    store: bool = False,
    temperature: float | None = None,
) -> Tuple[QuestionPlan, Optional[Dict[str, Any]]]:
    runtime_config = _resolve_runtime_config(
        task_kind=TASK_GENERATE_QUESTION_PLAN,
        session_override=model,
    )
    nano_suffix = build_small_model_guardrails(runtime_config.resolved_model)
    task_limits_suffix = build_task_prompt_limits_suffix(
        max_bullets_per_field=runtime_config.task_max_bullets_per_field,
        max_sentences_per_field=runtime_config.task_max_sentences_per_field,
        max_output_tokens=runtime_config.task_max_output_tokens,
    )
    system = (
        "Du bist ein Experte für Vacancy Intake & Recruiting Briefings. "
        "Du erstellst einen dynamischen, aber stabilen Fragebogen für Line Manager. "
        "Der Fragebogen soll alle recruitment-relevanten Informationen top-down einsammeln "
        "und sich am Jobspec orientieren. "
        "Erzeuge nur Fragen, die einen echten Mehrwert liefern (keine Dopplungen). "
        "Nutze kurze, klare Fragen. "
        f"Sprache: {language}."
        f"{nano_suffix}"
        f"{task_limits_suffix}"
    )

    user = (
        "Erstelle einen QuestionPlan in dieser Reihenfolge: company, team, role_tasks, skills, benefits, interview. "
        "Der Step 'jobad' ist bereits durch die Jobspec-Extraktion abgedeckt. "
        "Füge bei jedem Step 6–12 Fragen hinzu, je nachdem, was im Jobspec fehlt. "
        "Markiere pro Step genau 3–5 Fragen mit priority='core'; "
        "weitere Fragen als 'standard' oder 'detail'. "
        "Setze group_key stabil und kurz (snake_case), sodass thematisch verwandte Fragen denselben group_key teilen. "
        "Nutze depends_on nur bei echten Follow-up-Fragen; vermeide verschachtelte oder übermäßige Abhängigkeiten. "
        "Für depends_on nutze nur einfache Regeln mit question_id plus equals ODER any_of ODER is_answered. "
        "Bevorzuge konkrete, messbare Antworten (z. B. 'Erfolgskriterien', 'Top-Deliverables', 'Must-have vs Nice-to-have').\n\n"
        "Wenn answer_type='number' genutzt wird, setze immer explizit min_value und max_value "
        "(optional step_value), passend zur Frage. Nutze keine Freitext-Frage für numerische Werte.\n\n"
        "Jobspec-Extraktion (JSON):\n"
        f"{json.dumps(job.model_dump(mode='json'), ensure_ascii=False, sort_keys=True, separators=(',', ':'))}"
    )

    normalized_job = _canonicalize_for_cache(job.model_dump(mode="json"))
    cache_key = _build_llm_cache_key(
        task_kind=TASK_GENERATE_QUESTION_PLAN,
        resolved_model=runtime_config.resolved_model,
        language=language,
        reasoning_effort=runtime_config.reasoning_effort,
        verbosity=runtime_config.verbosity,
        store=store,
        normalized_content=normalized_job,
        schema_version=QUESTION_SCHEMA_VERSION,
    )
    cache = _get_session_response_cache()
    cached_entry = cache.get(cache_key)
    if isinstance(cached_entry, dict):
        cached_result = cached_entry.get("result")
        if isinstance(cached_result, dict):
            try:
                parsed_cached = QuestionPlan.model_validate(cached_result)
            except ValidationError:
                _invalidate_cache_entry_for_validation_error(
                    cache=cache,
                    cache_key=cache_key,
                    task_kind=TASK_GENERATE_QUESTION_PLAN,
                    model_name=runtime_config.resolved_model,
                )
            else:
                normalized_cached = normalize_question_plan(parsed_cached)
                return normalized_cached, _cached_usage(cache_key=cache_key)

    parsed, usage = _parse_with_structured_outputs(
        runtime_config=runtime_config,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        out_model=QuestionPlan,
        store=store,
        maybe_temperature=temperature,
    )

    normalized = normalize_question_plan(parsed)
    cache[cache_key] = {"result": normalized.model_dump(mode="json")}
    return normalized, usage


def normalize_question_plan(plan: QuestionPlan) -> QuestionPlan:
    """Guarantee unique, stable-ish ids and basic invariants."""
    seen = set()
    for step in plan.steps:
        for q in step.questions:
            if not q.id or q.id.strip() == "":
                q.id = f"q_{step.step_key}_{_safe_hash(q.label)}"
            else:
                q.id = re_slugify(q.id)

            # Ensure uniqueness
            if q.id in seen:
                q.id = f"{q.id}_{_safe_hash(step.step_key + q.label)}"
            seen.add(q.id)

            # Default target_path if not provided
            if not q.target_path:
                q.target_path = f"answers.{step.step_key}.{q.id}"

            _normalize_category_question(q)
            _normalize_numeric_question(q)
            _normalize_question_priority(q)
            _normalize_question_group_key(q, step_key=step.step_key)
            _normalize_question_dependencies(q, step=step)
    return plan


def _normalize_question_priority(q: Any) -> None:
    raw_priority = getattr(q, "priority", None)
    if not isinstance(raw_priority, str):
        q.priority = None
        return
    normalized = raw_priority.strip().lower()
    q.priority = normalized if normalized in _QUESTION_PRIORITY_VALUES else None


def _normalize_question_group_key(q: Any, *, step_key: str) -> None:
    raw_group_key = getattr(q, "group_key", None)
    if isinstance(raw_group_key, str) and raw_group_key.strip():
        q.group_key = re_slugify(raw_group_key)
        return
    q.group_key = re_slugify(f"{step_key}_{q.id}")


def _normalize_question_dependencies(q: Any, *, step: Any) -> None:
    raw_depends_on = getattr(q, "depends_on", None)
    if not isinstance(raw_depends_on, list) or not raw_depends_on:
        q.depends_on = None
        return

    known_ids = {str(item.id) for item in getattr(step, "questions", []) if item.id}
    sanitized: list[QuestionDependency] = []
    for dep in raw_depends_on:
        if not hasattr(dep, "question_id"):
            continue
        source_id_raw = getattr(dep, "question_id", "")
        if not isinstance(source_id_raw, str) or not source_id_raw.strip():
            continue
        source_id = re_slugify(source_id_raw)
        if source_id == q.id or source_id not in known_ids:
            continue

        equals = getattr(dep, "equals", None)
        any_of = getattr(dep, "any_of", None)
        is_answered = getattr(dep, "is_answered", None)

        normalized_any_of: list[str | int | float | bool] | None = None
        if isinstance(any_of, list):
            normalized_any_of = []
            for value in any_of:
                if isinstance(value, (str, int, float, bool)):
                    normalized_any_of.append(value)
            if not normalized_any_of:
                normalized_any_of = None

        if not isinstance(equals, (str, int, float, bool)):
            equals = None
        if not isinstance(is_answered, bool):
            is_answered = None

        active_keys = sum(
            value is not None for value in (equals, normalized_any_of, is_answered)
        )
        if active_keys != 1:
            continue

        dep_payload: dict[str, Any] = {"question_id": source_id}
        if equals is not None:
            dep_payload["equals"] = equals
        if normalized_any_of is not None:
            dep_payload["any_of"] = normalized_any_of
        if is_answered is not None:
            dep_payload["is_answered"] = is_answered
        sanitized.append(QuestionDependency.model_validate(dep_payload))

    q.depends_on = sanitized or None


def _normalize_category_question(q: Any) -> None:
    haystack = " ".join(
        str(part).lower()
        for part in (
            getattr(q, "label", ""),
            getattr(q, "help", ""),
            getattr(q, "id", ""),
        )
        if isinstance(part, str)
    )
    for rule in _CATEGORY_QUESTION_RULES:
        if not any(term in haystack for term in rule["terms"]):
            continue
        q.answer_type = rule["answer_type"]
        q.options = _merge_options_with_fallback(q.options, rule["options"])
        if q.answer_type == AnswerType.MULTI_SELECT and not isinstance(q.default, list):
            q.default = []
        elif q.answer_type == AnswerType.SINGLE_SELECT and isinstance(q.default, list):
            q.default = q.default[0] if q.default else None
        return


def _merge_options_with_fallback(
    existing_options: list[str] | None,
    rule_options: tuple[str, ...],
) -> list[str]:
    merged: list[str] = []
    for option in [*(existing_options or []), *rule_options]:
        if not isinstance(option, str):
            continue
        cleaned = option.strip()
        if cleaned and cleaned not in merged:
            merged.append(cleaned)
    if _OTHER_OPTION not in merged:
        merged.append(_OTHER_OPTION)
    return merged


def _normalize_numeric_question(q: Any) -> None:
    haystack = " ".join(
        str(part).lower()
        for part in (
            getattr(q, "label", ""),
            getattr(q, "help", ""),
            getattr(q, "id", ""),
            getattr(q, "rationale", ""),
        )
        if isinstance(part, str)
    )
    if not haystack:
        return

    matched_rule: dict[str, Any] | None = None
    for rule in _NUMERIC_QUESTION_RULES:
        if any(term in haystack for term in rule["terms"]):
            matched_rule = rule
            break
    if matched_rule is None and getattr(q, "answer_type", None) != AnswerType.NUMBER:
        return

    q.answer_type = AnswerType.NUMBER
    if matched_rule is not None:
        rule_min, rule_max, rule_step = matched_rule["bounds"]
    else:
        rule_min, rule_max, rule_step = (0.0, 100.0, 1.0)

    min_value = getattr(q, "min_value", None)
    max_value = getattr(q, "max_value", None)
    step_value = getattr(q, "step_value", None)

    if min_value is None:
        q.min_value = rule_min
    if max_value is None:
        q.max_value = rule_max
    if step_value is None:
        q.step_value = rule_step


def re_slugify(s: str) -> str:
    import re

    s = s.strip().lower()
    s = re.sub(r"[^a-z0-9_\-]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    if not s:
        s = "q_" + _safe_hash(s)
    if s[0].isdigit():
        s = "q_" + s
    return s


def generate_vacancy_brief(
    job: JobAdExtract,
    answers: Dict[str, Any],
    *,
    model: str,
    language: str = DEFAULT_LANGUAGE,
    store: bool = False,
    temperature: float | None = None,
) -> Tuple[VacancyBrief, Optional[Dict[str, Any]]]:
    runtime_config = _resolve_runtime_config(
        task_kind=TASK_GENERATE_VACANCY_BRIEF,
        session_override=model,
    )
    nano_suffix = build_small_model_guardrails(runtime_config.resolved_model)
    task_limits_suffix = build_task_prompt_limits_suffix(
        max_bullets_per_field=runtime_config.task_max_bullets_per_field,
        max_sentences_per_field=runtime_config.task_max_sentences_per_field,
        max_output_tokens=runtime_config.task_max_output_tokens,
    )
    system = (
        "Du bist ein Recruiting Partner, der aus einer Jobspec und Manager-Antworten "
        "einen vollständigen Recruiting Brief erstellt. "
        "Du bist präzise, vermeidest Marketing-Floskeln und machst offene Punkte transparent. "
        f"Sprache: {language}."
        f"{nano_suffix}"
        f"{task_limits_suffix}"
    )

    user = (
        "Erstelle jetzt den finalen VacancyBrief.\n\n"
        "Jobspec-Extraktion (JSON):\n"
        f"{json.dumps(job.model_dump(mode='json'), ensure_ascii=False, sort_keys=True, separators=(',', ':'))}\n\n"
        "Manager-Antworten (JSON):\n"
        f"{json.dumps(answers, ensure_ascii=False, sort_keys=True, separators=(',', ':'))}\n\n"
        "Wichtig: Falls wichtige Informationen fehlen, schreibe sie unter risks_open_questions."
    )

    normalized_content = _canonicalize_for_cache(
        {
            "job": job.model_dump(mode="json"),
            "answers": answers,
        }
    )
    cache_key = _build_llm_cache_key(
        task_kind=TASK_GENERATE_VACANCY_BRIEF,
        resolved_model=runtime_config.resolved_model,
        language=language,
        reasoning_effort=runtime_config.reasoning_effort,
        verbosity=runtime_config.verbosity,
        store=store,
        normalized_content=normalized_content,
        schema_version=VACANCY_SCHEMA_VERSION,
    )
    cache = _get_session_response_cache()
    cached_entry = cache.get(cache_key)
    if isinstance(cached_entry, dict):
        cached_result = cached_entry.get("result")
        if isinstance(cached_result, dict):
            try:
                parsed_cached = VacancyBrief.model_validate(cached_result)
            except ValidationError:
                _invalidate_cache_entry_for_validation_error(
                    cache=cache,
                    cache_key=cache_key,
                    task_kind=TASK_GENERATE_VACANCY_BRIEF,
                    model_name=runtime_config.resolved_model,
                )
            else:
                return parsed_cached, _cached_usage(cache_key=cache_key)

    parsed, usage = _parse_with_structured_outputs(
        runtime_config=runtime_config,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        out_model=VacancyBriefLLM,
        store=store,
        maybe_temperature=temperature,
    )

    # Always embed the merged structured payload for downstream systems
    parsed_brief = cast(VacancyBriefLLM, parsed)
    merged = {
        "job_extract": job.model_dump(),
        "answers": answers,
    }
    brief = VacancyBrief(
        **parsed_brief.model_dump(),
        structured_data=merged,
    )
    cache[cache_key] = {"result": brief.model_dump(mode="json")}
    return brief, usage


def upgrade_vacancy_brief_critical_sections(
    base_brief: VacancyBrief,
    job: JobAdExtract,
    answers: Dict[str, Any],
    *,
    model: str,
    language: str = DEFAULT_LANGUAGE,
    store: bool = False,
    temperature: float | None = None,
) -> Tuple[VacancyBrief, Optional[Dict[str, Any]]]:
    """Sharpen only critical quality sections while keeping export schema unchanged."""

    runtime_config = _resolve_runtime_config(
        task_kind=TASK_GENERATE_VACANCY_BRIEF,
        session_override=model,
    )
    task_limits_suffix = build_task_prompt_limits_suffix(
        max_bullets_per_field=runtime_config.task_max_bullets_per_field,
        max_sentences_per_field=runtime_config.task_max_sentences_per_field,
        max_output_tokens=runtime_config.task_max_output_tokens,
    )
    system = (
        "Du bist ein Senior Recruiting Quality Reviewer. "
        "Du überarbeitest ausschließlich die kritischen Abschnitte eines vorhandenen Vacancy Briefs. "
        "Ziele: präzisere, testbare evaluation_rubric und konkrete risks_open_questions. "
        "Keine zusätzlichen Felder, keine Änderung anderer Brief-Abschnitte. "
        f"Sprache: {language}."
        f"{task_limits_suffix}"
    )
    user = (
        "Überarbeite nur evaluation_rubric und risks_open_questions.\n\n"
        "Bestehender Vacancy Brief (JSON):\n"
        f"{json.dumps(base_brief.model_dump(mode='json'), ensure_ascii=False, sort_keys=True, separators=(',', ':'))}\n\n"
        "Jobspec-Extraktion (JSON):\n"
        f"{json.dumps(job.model_dump(mode='json'), ensure_ascii=False, sort_keys=True, separators=(',', ':'))}\n\n"
        "Manager-Antworten (JSON):\n"
        f"{json.dumps(answers, ensure_ascii=False, sort_keys=True, separators=(',', ':'))}\n\n"
        "Anforderungen:\n"
        "- evaluation_rubric als klare, beobachtbare Kriterien (bullet-ready).\n"
        "- risks_open_questions nur offene Risiken/Unklarheiten, priorisiert nach Hiring-Impact."
    )
    normalized_content = _canonicalize_for_cache(
        {
            "base_brief": base_brief.model_dump(mode="json"),
            "job": job.model_dump(mode="json"),
            "answers": answers,
            "mode": "critical_upgrade",
        }
    )
    cache_key = _build_llm_cache_key(
        task_kind=f"{TASK_GENERATE_VACANCY_BRIEF}_critical_upgrade",
        resolved_model=runtime_config.resolved_model,
        language=language,
        reasoning_effort=runtime_config.reasoning_effort,
        verbosity=runtime_config.verbosity,
        store=store,
        normalized_content=normalized_content,
        schema_version=VACANCY_SCHEMA_VERSION,
    )
    cache = _get_session_response_cache()
    cached_entry = cache.get(cache_key)
    if isinstance(cached_entry, dict):
        cached_result = cached_entry.get("result")
        if isinstance(cached_result, dict):
            updated_cached = base_brief.model_copy(deep=True)
            updated_cached.evaluation_rubric = cached_result.get(
                "evaluation_rubric", []
            )
            updated_cached.risks_open_questions = cached_result.get(
                "risks_open_questions", []
            )
            return updated_cached, _cached_usage(cache_key=cache_key)

    parsed, usage = _parse_with_structured_outputs(
        runtime_config=runtime_config,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        out_model=VacancyBriefCriticalSections,
        store=store,
        maybe_temperature=temperature,
    )
    parsed_sections = cast(VacancyBriefCriticalSections, parsed)
    updated = base_brief.model_copy(deep=True)
    updated.evaluation_rubric = parsed_sections.evaluation_rubric
    updated.risks_open_questions = parsed_sections.risks_open_questions
    cache[cache_key] = {"result": parsed_sections.model_dump(mode="json")}
    return updated, usage


def generate_custom_job_ad(
    *,
    job: JobAdExtract,
    answers: Dict[str, Any],
    selected_values: Dict[str, list[str]],
    style_guide: str,
    change_request: str | None,
    model: str,
    language: str = DEFAULT_LANGUAGE,
    store: bool = False,
    temperature: float | None = None,
) -> Tuple[JobAdGenerationResult, Optional[Dict[str, Any]]]:
    """Generate or refine a job ad draft from explicitly selected intake values."""

    runtime_config = _resolve_runtime_config(
        task_kind=TASK_GENERATE_JOB_AD,
        session_override=model,
    )
    task_limits_suffix = build_task_prompt_limits_suffix(
        max_bullets_per_field=runtime_config.task_max_bullets_per_field,
        max_sentences_per_field=runtime_config.task_max_sentences_per_field,
        max_output_tokens=runtime_config.task_max_output_tokens,
    )
    system = (
        "Du bist ein Senior Recruiting Copywriter und Compliance Reviewer. "
        "Schreibe eine zielgruppen-optimierte, AGG-konforme Stellenanzeige auf Basis "
        "explizit ausgewählter Informationen. "
        "Wenn Informationen fehlen, markiere sie klar in agg_checklist ohne zu halluzinieren. "
        f"Sprache: {language}."
        f"{task_limits_suffix}"
    )
    user = (
        "Erzeuge eine finale Stellenanzeige nur aus den ausgewählten Daten. "
        "Verwende klare, inklusive Sprache und vermeide diskriminierende Formulierungen.\n\n"
        "Jobspec (JSON):\n"
        f"{json.dumps(job.model_dump(mode='json'), ensure_ascii=False, sort_keys=True, separators=(',', ':'))}\n\n"
        "Manager-Antworten (JSON):\n"
        f"{json.dumps(answers, ensure_ascii=False, sort_keys=True, separators=(',', ':'))}\n\n"
        "Ausgewählte Inhalte (JSON):\n"
        f"{json.dumps(selected_values, ensure_ascii=False, sort_keys=True, separators=(',', ':'))}\n\n"
        f"Styleguide:\n{style_guide.strip() or 'Nicht angegeben.'}\n\n"
        f"Anpassungswunsch:\n{(change_request or '').strip() or 'Kein zusätzlicher Änderungswunsch.'}\n\n"
        "Pflicht: headline, target_group (Liste), agg_checklist (Liste), job_ad_text liefern."
    )
    normalized_content = _canonicalize_for_cache(
        {
            "job": job.model_dump(mode="json"),
            "answers": answers,
            "selected_values": selected_values,
            "style_guide": style_guide,
            "change_request": change_request or "",
        }
    )
    cache_key = _build_llm_cache_key(
        task_kind=TASK_GENERATE_JOB_AD,
        resolved_model=runtime_config.resolved_model,
        language=language,
        reasoning_effort=runtime_config.reasoning_effort,
        verbosity=runtime_config.verbosity,
        store=store,
        normalized_content=normalized_content,
        schema_version=VACANCY_SCHEMA_VERSION,
    )
    cache = _get_session_response_cache()
    cached_entry = cache.get(cache_key)
    if isinstance(cached_entry, dict):
        cached_result = cached_entry.get("result")
        if isinstance(cached_result, dict):
            return JobAdGenerationResult.model_validate(cached_result), _cached_usage(
                cache_key=cache_key
            )

    parsed, usage = _parse_with_structured_outputs(
        runtime_config=runtime_config,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        out_model=JobAdGenerationResult,
        store=store,
        maybe_temperature=temperature,
    )
    result = cast(JobAdGenerationResult, parsed)
    cache[cache_key] = {"result": result.model_dump(mode="json")}
    return result, usage
