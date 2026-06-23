"""Runtime contract for short DE/EN UX copy."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Final, Mapping

from constants import (
    STEP_KEY_BENEFITS,
    STEP_KEY_COMPANY,
    STEP_KEY_INTERVIEW,
    STEP_KEY_LANDING,
    STEP_KEY_ROLE_TASKS,
    STEP_KEY_SKILLS,
    STEP_KEY_SUMMARY,
)
from i18n import active_language, normalize_language, tr_safe


UX_COPY_CONTRACT_VERSION: Final[str] = "2026-06-23"
UX_COPY_STEP_KEYS: Final[tuple[str, ...]] = (
    STEP_KEY_LANDING,
    STEP_KEY_COMPANY,
    STEP_KEY_ROLE_TASKS,
    STEP_KEY_SKILLS,
    STEP_KEY_BENEFITS,
    STEP_KEY_INTERVIEW,
    STEP_KEY_SUMMARY,
)
UX_COPY_FIELDS: Final[tuple[str, ...]] = (
    "headline",
    "subheadline",
    "value_line",
    "primary_cta",
    "secondary_cta",
    "empty_state",
    "readiness",
)

_SUMMARY_DEFAULT = "default"
_SUMMARY_GAP = "gap"
_SUMMARY_READY = "ready"


@dataclass(frozen=True)
class VacancyCopyContext:
    role_title: str = ""
    company_name: str = ""
    location: str = ""
    department: str = ""
    work_model: str = ""
    seniority_level: str = ""
    readiness_score: int | None = None
    open_questions_count: int | None = None
    critical_gaps_count: int | None = None


@dataclass(frozen=True)
class StepCopy:
    headline: str
    subheadline: str
    value_line: str = ""
    primary_cta: str = ""
    secondary_cta: str = ""
    empty_state: str = ""
    readiness: str = ""


@dataclass(frozen=True)
class StepCopyLocaleKeys:
    headline: str
    subheadline: str
    value_line: str
    primary_cta: str
    secondary_cta: str
    empty_state: str
    readiness: str


def _base_key(step_key: str, field: str) -> str:
    return f"ux_copy.steps.{step_key}.{field}"


def _summary_variant_key(field: str, variant: str) -> str:
    return f"ux_copy.steps.{STEP_KEY_SUMMARY}.{field}.{variant}"


def _build_locale_keys(step_key: str, *, summary_variant: str) -> StepCopyLocaleKeys:
    if step_key == STEP_KEY_SUMMARY:
        return StepCopyLocaleKeys(
            headline=_summary_variant_key("headline", summary_variant),
            subheadline=_summary_variant_key("subheadline", summary_variant),
            value_line=_base_key(step_key, "value_line"),
            primary_cta=_base_key(step_key, "primary_cta"),
            secondary_cta=_base_key(step_key, "secondary_cta"),
            empty_state=_base_key(step_key, "empty_state"),
            readiness=_summary_variant_key("readiness", summary_variant),
        )
    return StepCopyLocaleKeys(
        headline=_base_key(step_key, "headline"),
        subheadline=_base_key(step_key, "subheadline"),
        value_line=_base_key(step_key, "value_line"),
        primary_cta=_base_key(step_key, "primary_cta"),
        secondary_cta=_base_key(step_key, "secondary_cta"),
        empty_state=_base_key(step_key, "empty_state"),
        readiness=_base_key(step_key, "readiness"),
    )


def _clean_value(value: object, *, fallback: str) -> str:
    cleaned = str(value or "").strip()
    return cleaned or fallback


def _coerce_int(value: object, *, fallback: int = 0) -> int:
    if value is None:
        return fallback
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def _template_values(
    context: VacancyCopyContext | None,
    *,
    language: str,
) -> dict[str, Any]:
    ctx = context or VacancyCopyContext()
    if language == "en":
        role_fallback = "this role"
        company_fallback = "the company"
        location_fallback = "the relevant location"
    else:
        role_fallback = "diese Rolle"
        company_fallback = "das Unternehmen"
        location_fallback = "dem relevanten Standort"
    return {
        "role_title": _clean_value(ctx.role_title, fallback=role_fallback),
        "company_name": _clean_value(ctx.company_name, fallback=company_fallback),
        "location": _clean_value(ctx.location, fallback=location_fallback),
        "department": str(ctx.department or "").strip(),
        "work_model": str(ctx.work_model or "").strip(),
        "seniority_level": str(ctx.seniority_level or "").strip(),
        "readiness_score": _coerce_int(ctx.readiness_score),
        "open_questions_count": _coerce_int(ctx.open_questions_count),
        "critical_gaps_count": _coerce_int(ctx.critical_gaps_count),
    }


def _summary_variant(values: Mapping[str, Any]) -> str:
    critical_gaps = _coerce_int(values.get("critical_gaps_count"))
    readiness_score = _coerce_int(values.get("readiness_score"))
    if critical_gaps > 0:
        return _SUMMARY_GAP
    if readiness_score >= 100:
        return _SUMMARY_READY
    return _SUMMARY_DEFAULT


def _resolve_key(key: str, *, language: str, values: Mapping[str, Any]) -> str:
    return tr_safe(key, language=language, **values)


def build_step_copy(
    step_key: str,
    *,
    language: str | None = None,
    context: VacancyCopyContext | None = None,
) -> StepCopy:
    normalized_language = normalize_language(language or active_language())
    normalized_step_key = step_key if step_key in UX_COPY_STEP_KEYS else STEP_KEY_LANDING
    values = _template_values(context, language=normalized_language)
    summary_variant = (
        _summary_variant(values)
        if normalized_step_key == STEP_KEY_SUMMARY
        else _SUMMARY_DEFAULT
    )
    keys = _build_locale_keys(normalized_step_key, summary_variant=summary_variant)
    return StepCopy(
        headline=_resolve_key(
            keys.headline, language=normalized_language, values=values
        ),
        subheadline=_resolve_key(
            keys.subheadline, language=normalized_language, values=values
        ),
        value_line=_resolve_key(
            keys.value_line, language=normalized_language, values=values
        ),
        primary_cta=_resolve_key(
            keys.primary_cta, language=normalized_language, values=values
        ),
        secondary_cta=_resolve_key(
            keys.secondary_cta, language=normalized_language, values=values
        ),
        empty_state=_resolve_key(
            keys.empty_state, language=normalized_language, values=values
        ),
        readiness=_resolve_key(
            keys.readiness, language=normalized_language, values=values
        ),
    )


def build_landing_copy(
    *,
    language: str | None = None,
    context: VacancyCopyContext | None = None,
) -> StepCopy:
    return build_step_copy(STEP_KEY_LANDING, language=language, context=context)


def build_summary_copy(
    *,
    language: str | None = None,
    context: VacancyCopyContext | None = None,
) -> StepCopy:
    return build_step_copy(STEP_KEY_SUMMARY, language=language, context=context)
