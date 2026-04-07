# llm_client.py
"""OpenAI API wrapper for this app.

Uses Structured Outputs via the OpenAI Python SDK `.responses.parse(...)` when available.
"""

from __future__ import annotations

import hashlib
import json
import os
from typing import Any, Dict, List, Optional, Tuple, Type

import streamlit as st
from openai import AuthenticationError, OpenAI
from pydantic import BaseModel

from constants import DEFAULT_LANGUAGE
from schemas import JobAdExtract, QuestionPlan, VacancyBrief
from settings_openai import OpenAISettings, load_openai_settings


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

    raise RuntimeError(
        "OpenAI API key not configured. Set OPENAI_API_KEY in Streamlit secrets "
        "or environment variables and retry."
    )


def _safe_hash(text: str, n: int = 10) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:n]


def _parse_with_structured_outputs(
    *,
    model: str,
    messages: List[Dict[str, Any]],
    out_model: Type[BaseModel],
    store: bool,
    temperature: float,
) -> Tuple[BaseModel, Optional[Dict[str, Any]]]:
    """Try `.responses.parse`, then fall back to `.chat.completions.parse` if needed."""
    settings = load_openai_settings()
    if not _has_any_openai_api_key(settings):
        _raise_missing_api_key_hint()

    client = get_openai_client()

    # Newer SDK path (Responses API + parse helper)
    if hasattr(client, "responses") and hasattr(client.responses, "parse"):
        try:
            resp = client.responses.parse(
                model=model,
                input=messages,
                text_format=out_model,
                store=store,
                temperature=temperature,
            )
        except AuthenticationError as exc:
            if not _has_any_openai_api_key(settings):
                _raise_missing_api_key_hint()
            raise RuntimeError(
                "OpenAI authentication failed. Verify OPENAI_API_KEY and retry."
            ) from exc

        parsed = resp.output_parsed
        usage = getattr(resp, "usage", None)
        return parsed, usage

    # Fallback: Chat Completions parse helper (older projects may still use it)
    if hasattr(client, "chat") and hasattr(client.chat.completions, "parse"):
        try:
            completion = client.chat.completions.parse(
                model=model,
                messages=messages,
                response_format=out_model,
                store=store,
                temperature=temperature,
            )
        except AuthenticationError as exc:
            if not _has_any_openai_api_key(settings):
                _raise_missing_api_key_hint()
            raise RuntimeError(
                "OpenAI authentication failed. Verify OPENAI_API_KEY and retry."
            ) from exc

        parsed = completion.choices[0].message.parsed
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
    temperature: float = 0.2,
) -> Tuple[JobAdExtract, Optional[Dict[str, Any]]]:
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

    parsed, usage = _parse_with_structured_outputs(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        out_model=JobAdExtract,
        store=store,
        temperature=temperature,
    )

    return parsed, usage


def generate_question_plan(
    job: JobAdExtract,
    *,
    model: str,
    language: str = DEFAULT_LANGUAGE,
    store: bool = False,
    temperature: float = 0.2,
) -> Tuple[QuestionPlan, Optional[Dict[str, Any]]]:
    system = (
        "Du bist ein Experte für Vacancy Intake & Recruiting Briefings. "
        "Du erstellst einen dynamischen, aber stabilen Fragebogen für Line Manager. "
        "Der Fragebogen soll alle recruitment-relevanten Informationen top-down einsammeln "
        "und sich am Jobspec orientieren. "
        "Erzeuge nur Fragen, die einen echten Mehrwert liefern (keine Dopplungen). "
        "Nutze kurze, klare Fragen. "
        f"Sprache: {language}."
    )

    user = (
        "Erstelle einen QuestionPlan mit Steps: company, team, role_tasks, skills, benefits, interview. "
        "Der Step 'jobad' ist bereits durch die Jobspec-Extraktion abgedeckt. "
        "Füge bei jedem Step 6–12 Fragen hinzu, je nachdem, was im Jobspec fehlt. "
        "Bevorzuge konkrete, messbare Antworten (z. B. 'Erfolgskriterien', 'Top-Deliverables', 'Must-have vs Nice-to-have').\n\n"
        "Jobspec-Extraktion (JSON):\n"
        f"{job.model_dump_json(indent=2)}"
    )

    parsed, usage = _parse_with_structured_outputs(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        out_model=QuestionPlan,
        store=store,
        temperature=temperature,
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
    temperature: float = 0.25,
) -> Tuple[VacancyBrief, Optional[Dict[str, Any]]]:
    system = (
        "Du bist ein Recruiting Partner, der aus einer Jobspec und Manager-Antworten "
        "einen vollständigen Recruiting Brief erstellt. "
        "Du bist präzise, vermeidest Marketing-Floskeln und machst offene Punkte transparent. "
        f"Sprache: {language}."
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
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        out_model=VacancyBrief,
        store=store,
        temperature=temperature,
    )

    # Always embed the merged structured payload for downstream systems
    merged = {
        "job_extract": job.model_dump(),
        "answers": answers,
    }
    parsed.structured_data = merged
    return parsed, usage
