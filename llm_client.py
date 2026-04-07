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
from typing import Any, Callable, Dict, List, Optional, Tuple, Type

import streamlit as st
from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    OpenAI,
)
from pydantic import BaseModel, ValidationError

from constants import DEFAULT_LANGUAGE
from model_capabilities import (
    is_gpt54_family,
    is_gpt5_legacy_model,
    is_nano_model,
    normalize_reasoning_effort,
    supports_reasoning,
    supports_temperature,
    supports_verbosity,
)
from schemas import JobAdExtract, QuestionPlan, VacancyBrief
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


@dataclass(frozen=True)
class OpenAIRuntimeConfig:
    """Resolved runtime configuration for a single LLM task call chain."""

    resolved_model: str
    reasoning_effort: str | None
    verbosity: str | None
    timeout_seconds: float
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
        settings=settings,
    )


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
) -> dict[str, Any]:
    """Build kwargs for `responses.parse` with endpoint-specific fields."""

    request_kwargs: dict[str, Any] = {"model": model, "store": store}
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

    if isinstance(exc, (APITimeoutError, TimeoutError)):
        return OpenAICallError(
            "OpenAI-Timeout (DE) / OpenAI timeout (EN). Bitte erneut versuchen.",
            debug_detail=_debug_detail(),
            error_code="OPENAI_TIMEOUT",
        )

    if isinstance(exc, APIStatusError) and exc.status_code == 400:
        unsupported_hint = (
            "unsupported parameter" in api_message_norm
            or "unknown parameter" in api_message_norm
            or "not allowed" in api_message_norm
            or "invalid type" in api_message_norm
        )
        model_not_found_hint = (
            "model not found" in api_message_norm or "unknown model" in api_message_norm
        )
        ui_message = (
            "OpenAI-Modell nicht gefunden (DE) / OpenAI model not found (EN)."
            if model_not_found_hint
            else (
                "Nicht unterstützter OpenAI-Parameter (DE) / Unsupported OpenAI parameter (EN)."
                if unsupported_hint
                else "Ungültige OpenAI-Parameter (DE) / Invalid OpenAI parameters (EN)."
            )
        )
        return OpenAICallError(
            ui_message,
            debug_detail=_debug_detail(),
            error_code="OPENAI_BAD_REQUEST",
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
        TASK_GENERATE_VACANCY_BRIEF: resolved_settings.high_reasoning_model,
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
        except Exception as exc:
            if not _has_any_openai_api_key(settings):
                _raise_missing_api_key_hint()
            mapped = _error_from_openai_exception(exc, endpoint="responses.parse")
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
    parsed, usage = _parse_with_structured_outputs(
        runtime_config=runtime_config,
        messages=messages,
        out_model=JobAdExtract,
        store=store,
        maybe_temperature=temperature,
    )

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
    system = (
        "Du bist ein Experte für Vacancy Intake & Recruiting Briefings. "
        "Du erstellst einen dynamischen, aber stabilen Fragebogen für Line Manager. "
        "Der Fragebogen soll alle recruitment-relevanten Informationen top-down einsammeln "
        "und sich am Jobspec orientieren. "
        "Erzeuge nur Fragen, die einen echten Mehrwert liefern (keine Dopplungen). "
        "Nutze kurze, klare Fragen. "
        f"Sprache: {language}."
        f"{nano_suffix}"
    )

    user = (
        "Erstelle einen QuestionPlan in dieser Reihenfolge: company, team, role_tasks, skills, benefits, interview. "
        "Der Step 'jobad' ist bereits durch die Jobspec-Extraktion abgedeckt. "
        "Füge bei jedem Step 6–12 Fragen hinzu, je nachdem, was im Jobspec fehlt. "
        "Bevorzuge konkrete, messbare Antworten (z. B. 'Erfolgskriterien', 'Top-Deliverables', 'Must-have vs Nice-to-have').\n\n"
        "Jobspec-Extraktion (JSON):\n"
        f"{job.model_dump_json(indent=2)}"
    )

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
    return plan


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
    system = (
        "Du bist ein Recruiting Partner, der aus einer Jobspec und Manager-Antworten "
        "einen vollständigen Recruiting Brief erstellt. "
        "Du bist präzise, vermeidest Marketing-Floskeln und machst offene Punkte transparent. "
        f"Sprache: {language}."
        f"{nano_suffix}"
    )

    user = (
        "Erstelle jetzt den finalen VacancyBrief.\n\n"
        "Jobspec-Extraktion (JSON):\n"
        f"{job.model_dump_json(indent=2)}\n\n"
        "Manager-Antworten (JSON):\n"
        f"{json.dumps(answers, indent=2, ensure_ascii=False)}\n\n"
        "Wichtig: Falls wichtige Informationen fehlen, schreibe sie unter risks_open_questions."
    )

    parsed, usage = _parse_with_structured_outputs(
        runtime_config=runtime_config,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        out_model=VacancyBrief,
        store=store,
        maybe_temperature=temperature,
    )

    # Always embed the merged structured payload for downstream systems
    merged = {
        "job_extract": job.model_dump(),
        "answers": answers,
    }
    parsed.structured_data = merged
    return parsed, usage
