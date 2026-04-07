# llm_client.py
"""OpenAI API wrapper for this app.

Uses Structured Outputs via the OpenAI Python SDK `.responses.parse(...)` when available.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from typing import Any, Dict, List, Optional, Tuple, Type

import streamlit as st
from openai import APIStatusError, APITimeoutError, AuthenticationError, OpenAI
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
    supports_reasoning,
    supports_verbosity,
)


ModelTaskType = str
TASK_LIGHTWEIGHT = "extract"
TASK_MEDIUM_REASONING = "plan"
TASK_HIGH_REASONING = "quality_critical"


class OpenAICallError(RuntimeError):
    """Application-level error with user-facing and debug-safe details."""

    def __init__(self, ui_message: str, *, debug_detail: str | None = None) -> None:
        super().__init__(ui_message)
        self.ui_message = ui_message
        self.debug_detail = debug_detail


def build_extract_job_ad_messages(
    job_text: str, language: str = DEFAULT_LANGUAGE
) -> list[dict[str, str]]:
    """Build the standardized message list for job-ad extraction."""

    system = (
        "Du bist ein Senior HR / Recruiting Analyst. "
        "Extrahiere aus einem Jobspec/Job Ad alle recruitment-relevanten Informationen "
        "und normalisiere sie in ein strukturiertes JSON, ohne Halluzinationen. "
        "Wenn etwas nicht explizit vorkommt oder nicht sicher ableitbar ist: setze null/leer und schreibe es in 'gaps'. "
        "Wenn du Annahmen triffst: dokumentiere sie in 'assumptions'. "
        f"Antworte in der Sprache: {language}."
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


def _nano_closed_output_suffix(model: str) -> str:
    """Return a concise strict-output suffix for nano models."""

    if not is_nano_model(model):
        return ""

    return (
        " Für kleine Modelle strikt befolgen: "
        "1) Ausgabe nur als gültiges Schema-Objekt. "
        "2) Kein Zusatztext außerhalb des Schemas. "
        "3) Reihenfolge exakt wie angefordert. "
        "4) Keine impliziten Nebenaufgaben."
    )


def normalize_verbosity(verbosity: str | None) -> str | None:
    """Normalize verbosity values and drop unsupported inputs."""

    if verbosity is None:
        return None

    normalized_verbosity = verbosity.strip().lower()
    if normalized_verbosity in {"low", "medium", "high"}:
        return normalized_verbosity

    return None


def build_openai_request_kwargs(
    *,
    model: str,
    store: bool,
    maybe_temperature: float | None = None,
    reasoning_effort: str | None,
    verbosity: str | None,
) -> dict[str, Any]:
    """Build common request kwargs for structured parse calls."""

    normalized_reasoning_effort = normalize_reasoning_effort(model, reasoning_effort)
    normalized_verbosity = normalize_verbosity(verbosity)

    request_kwargs: dict[str, Any] = {
        "model": model,
        "store": store,
    }
    if maybe_temperature is not None and supports_temperature(
        model, normalized_reasoning_effort
    ):
        request_kwargs["temperature"] = maybe_temperature
    if supports_reasoning(model) and normalized_reasoning_effort is not None:
        request_kwargs["reasoning"] = {"effort": normalized_reasoning_effort}
    if supports_verbosity(model) and normalized_verbosity is not None:
        request_kwargs["text"] = {"verbosity": normalized_verbosity}

    return request_kwargs


def _build_openai_client(settings: OpenAISettings) -> OpenAI:
    """Create an OpenAI SDK client from normalized app settings."""

    timeout = settings.openai_request_timeout
    if settings.openai_api_key:
        return OpenAI(api_key=settings.openai_api_key, timeout=timeout)

    # Allow OpenAI SDK default env var fallback handling.
    return OpenAI(timeout=timeout)


@st.cache_resource
def get_openai_client() -> OpenAI:
    """Create a cached OpenAI client.

    Priority for API key:
    1) st.secrets["OPENAI_API_KEY"] (common in Streamlit deployments)
    2) Environment variable OPENAI_API_KEY (local dev / CI)
    """
    settings = load_openai_settings()
    return _build_openai_client(settings)


def _has_any_openai_api_key(settings: OpenAISettings) -> bool:
    """Check whether a key is present via app settings or SDK env fallback."""

    return bool(settings.openai_api_key or os.getenv("OPENAI_API_KEY"))


def _raise_missing_api_key_hint() -> None:
    """Raise a clear message for UI and logs without exposing secrets."""

    raise OpenAICallError(
        "OpenAI API-Key fehlt (DE) / Missing OpenAI API key (EN).",
        debug_detail="No OPENAI_API_KEY found in st.secrets or environment.",
    )


def _safe_hash(text: str, n: int = 10) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:n]


def _error_from_openai_exception(exc: Exception) -> OpenAICallError:
    """Convert SDK exceptions into concise, user-safe app errors."""

    if isinstance(exc, APITimeoutError):
        return OpenAICallError(
            "OpenAI-Timeout (DE) / OpenAI timeout (EN). Bitte erneut versuchen.",
            debug_detail="Request exceeded configured timeout.",
        )

    if isinstance(exc, APIStatusError) and exc.status_code == 400:
        return OpenAICallError(
            "Ungültige OpenAI-Parameter (DE) / Invalid OpenAI parameters (EN).",
            debug_detail="HTTP 400 from OpenAI (likely incompatible request fields).",
        )

    if isinstance(exc, AuthenticationError):
        return OpenAICallError(
            "OpenAI-Authentifizierung fehlgeschlagen (DE) / OpenAI authentication failed (EN).",
            debug_detail="AuthenticationError returned by OpenAI SDK.",
        )

    return OpenAICallError(
        "OpenAI-Aufruf fehlgeschlagen (DE) / OpenAI request failed (EN).",
        debug_detail=f"Unhandled OpenAI exception type: {type(exc).__name__}.",
    )


def _error_from_structured_output_exception(exc: Exception) -> OpenAICallError:
    """Map schema/validation failures to user-safe structured-output messages."""

    if isinstance(exc, ValidationError):
        return OpenAICallError(
            "Antwortformat ungültig (DE) / Invalid structured output (EN).",
            debug_detail="Pydantic validation failed for structured output.",
        )

    return OpenAICallError(
        "Structured Output fehlgeschlagen (DE) / Structured output failed (EN).",
        debug_detail=f"Structured output parsing error: {type(exc).__name__}.",
    )


def resolve_model_for_task(
    *,
    task_type: ModelTaskType,
    ui_model_override: str | None,
    settings: OpenAISettings | None = None,
) -> str:
    """Resolve a model via UI/global/task/default priority."""

    resolved_settings = settings or load_openai_settings()
    trimmed_ui_override = (ui_model_override or "").strip()
    base_model = resolved_settings.openai_model.strip()
    if trimmed_ui_override and trimmed_ui_override != base_model:
        return trimmed_ui_override

    if resolved_settings.openai_model_override:
        return resolved_settings.openai_model_override.strip()

    model_by_task: dict[ModelTaskType, str] = {
        TASK_LIGHTWEIGHT: resolved_settings.lightweight_model,
        TASK_MEDIUM_REASONING: resolved_settings.medium_reasoning_model,
        TASK_HIGH_REASONING: resolved_settings.high_reasoning_model,
    }
    routed_model = model_by_task.get(task_type, "").strip()
    if routed_model:
        return routed_model

    return resolved_settings.default_model


def _parse_with_structured_outputs(
    *,
    model: str,
    messages: List[Dict[str, Any]],
    out_model: Type[BaseModel],
    store: bool,
    maybe_temperature: float | None = None,
    reasoning_effort: str | None,
) -> Tuple[BaseModel, Optional[Dict[str, Any]]]:
    """Try `.responses.parse`, then fall back to `.chat.completions.parse` if needed."""
    settings = load_openai_settings()
    if not _has_any_openai_api_key(settings):
        _raise_missing_api_key_hint()

    client = get_openai_client()
    request_kwargs = build_openai_request_kwargs(
        model=model,
        store=store,
        maybe_temperature=maybe_temperature,
        reasoning_effort=reasoning_effort,
        verbosity=settings.verbosity,
    )

    # Newer SDK path (Responses API + parse helper)
    if hasattr(client, "responses") and hasattr(client.responses, "parse"):
        try:
            resp = client.responses.parse(
                input=messages,
                text_format=out_model,
                **request_kwargs,
            )
        except Exception as exc:
            if not _has_any_openai_api_key(settings):
                _raise_missing_api_key_hint()
            mapped = _error_from_openai_exception(exc)
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
        try:
            completion = client.chat.completions.parse(
                messages=messages,
                response_format=out_model,
                **request_kwargs,
            )
        except Exception as exc:
            if not _has_any_openai_api_key(settings):
                _raise_missing_api_key_hint()
            mapped = _error_from_openai_exception(exc)
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

    raise RuntimeError(
        "Your OpenAI Python SDK is missing `.responses.parse` / `.chat.completions.parse`. "
        "Please upgrade the `openai` package."
    )


def extract_job_ad(
    job_text: str,
    *,
    model: str,
    language: str = DEFAULT_LANGUAGE,
    store: bool = False,
    temperature: float | None = None,
) -> Tuple[JobAdExtract, Optional[Dict[str, Any]]]:
    resolved_model = resolve_model_for_task(
        task_type=TASK_LIGHTWEIGHT,
        ui_model_override=model,
    )
    messages = build_extract_job_ad_messages(job_text, language)
    nano_suffix = _nano_closed_output_suffix(resolved_model)
    parsed, usage = _parse_with_structured_outputs(
        model=resolved_model,
        messages=[
            {
                "role": "system",
                "content": messages[0]["content"] + nano_suffix,
            },
            messages[1],
        ],
        out_model=JobAdExtract,
        store=store,
        maybe_temperature=temperature,
        reasoning_effort=load_openai_settings().reasoning_effort,
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
    resolved_model = resolve_model_for_task(
        task_type=TASK_MEDIUM_REASONING,
        ui_model_override=model,
    )
    nano_suffix = _nano_closed_output_suffix(resolved_model)
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
        model=resolved_model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        out_model=QuestionPlan,
        store=store,
        maybe_temperature=temperature,
        reasoning_effort=load_openai_settings().reasoning_effort,
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
    resolved_model = resolve_model_for_task(
        task_type=TASK_HIGH_REASONING,
        ui_model_override=model,
    )
    nano_suffix = _nano_closed_output_suffix(resolved_model)
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
        model=resolved_model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        out_model=VacancyBrief,
        store=store,
        maybe_temperature=temperature,
        reasoning_effort=load_openai_settings().reasoning_effort,
    )

    # Always embed the merged structured payload for downstream systems
    merged = {
        "job_extract": job.model_dump(),
        "answers": answers,
    }
    parsed.structured_data = merged
    return parsed, usage
