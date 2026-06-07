"""Intake fact adapters for legacy session state."""

from __future__ import annotations

from typing import Any, Mapping, MutableMapping

from constants import FactKey, SSKey
from interview_process import normalize_interview_internal_flow
from schemas import JobAdExtract


_JOB_EXTRACT_FACT_FIELDS: dict[FactKey, str] = {
    FactKey.COMPANY_COMPANY_NAME: "company_name",
    FactKey.COMPANY_COMPANY_WEBSITE: "company_website",
    FactKey.COMPANY_LOCATION_CITY: "location_city",
    FactKey.ROLE_JOB_TITLE: "job_title",
    FactKey.ROLE_RESPONSIBILITIES: "responsibilities",
    FactKey.ROLE_SUCCESS_METRICS: "success_metrics",
    FactKey.SKILLS_MUST_HAVE_SKILLS: "must_have_skills",
    FactKey.SKILLS_NICE_TO_HAVE_SKILLS: "nice_to_have_skills",
    FactKey.SKILLS_LANGUAGES: "languages",
    FactKey.BENEFITS_SALARY_RANGE: "salary_range",
    FactKey.BENEFITS_BENEFITS: "benefits",
    FactKey.INTERVIEW_RECRUITMENT_STEPS: "recruitment_steps",
    FactKey.INTERVIEW_CONTACTS: "contacts",
}

_SUPPORTED_LEGACY_FACTS: tuple[FactKey, ...] = tuple(_JOB_EXTRACT_FACT_FIELDS)

_WRITE_THROUGH_FACT_FIELDS: dict[str, FactKey] = {
    "company_name": FactKey.COMPANY_COMPANY_NAME,
    "company_website": FactKey.COMPANY_COMPANY_WEBSITE,
    "location_city": FactKey.COMPANY_LOCATION_CITY,
    "job_title": FactKey.ROLE_JOB_TITLE,
    "must_have_skills": FactKey.SKILLS_MUST_HAVE_SKILLS,
    "nice_to_have_skills": FactKey.SKILLS_NICE_TO_HAVE_SKILLS,
}

_WRITE_THROUGH_FACTS: frozenset[FactKey] = frozenset(
    _WRITE_THROUGH_FACT_FIELDS.values()
)


def get_intake_fact_state(session_state: Mapping[str, Any]) -> dict[str, Any]:
    """Return the additive fact registry state without creating it."""

    raw_state = session_state.get(SSKey.INTAKE_FACTS.value)
    return raw_state if isinstance(raw_state, dict) else {}


def reset_intake_fact_state(session_state: MutableMapping[str, Any]) -> None:
    """Reset additive fact registry state; legacy state remains untouched."""

    session_state[SSKey.INTAKE_FACTS.value] = {}


def write_intake_fact(
    session_state: MutableMapping[str, Any],
    fact_key: FactKey | str,
    value: Any,
) -> None:
    """Mirror one supported canonical fact into additive fact state."""

    resolved_key = _coerce_fact_key(fact_key)
    if resolved_key is None or resolved_key not in _WRITE_THROUGH_FACTS:
        return

    normalized_value = _normalize_fact_value(value)
    fact_state = _mutable_fact_state(session_state)
    if normalized_value is None:
        fact_state.pop(resolved_key.value, None)
    else:
        fact_state[resolved_key.value] = normalized_value
    session_state[SSKey.INTAKE_FACTS.value] = fact_state


def write_intake_fact_by_legacy_field(
    session_state: MutableMapping[str, Any],
    legacy_field: str,
    value: Any,
) -> None:
    """Mirror a supported legacy field name into additive fact state."""

    fact_key = _WRITE_THROUGH_FACT_FIELDS.get(str(legacy_field or "").strip())
    if fact_key is not None:
        write_intake_fact(session_state, fact_key, value)


def write_job_extract_intake_facts(
    session_state: MutableMapping[str, Any],
    job_extract: JobAdExtract | Mapping[str, Any],
) -> None:
    """Mirror PR3a-supported fields from a reviewed job extract."""

    try:
        payload = JobAdExtract.model_validate(job_extract).model_dump(mode="json")
    except Exception:
        return
    for field_name in _WRITE_THROUGH_FACT_FIELDS:
        write_intake_fact_by_legacy_field(
            session_state,
            field_name,
            payload.get(field_name),
        )


def sync_selected_skill_intake_facts(session_state: MutableMapping[str, Any]) -> None:
    """Mirror selected free-skill status buckets into PR3a skill facts."""

    write_intake_fact(
        session_state,
        FactKey.SKILLS_MUST_HAVE_SKILLS,
        _selected_skills_by_status(session_state, "must"),
    )
    write_intake_fact(
        session_state,
        FactKey.SKILLS_NICE_TO_HAVE_SKILLS,
        _selected_skills_by_status(session_state, "nice"),
    )


def resolve_legacy_fact(
    fact_key: FactKey | str,
    session_state: Mapping[str, Any],
) -> Any | None:
    """Resolve one canonical fact from legacy state without mutating state."""

    resolved_key = _coerce_fact_key(fact_key)
    if resolved_key is None or resolved_key not in _SUPPORTED_LEGACY_FACTS:
        return None

    job_facts = _job_extract_facts(session_state)
    if resolved_key in job_facts:
        return job_facts[resolved_key]

    return _session_state_fact(resolved_key, session_state)


def collect_legacy_facts(session_state: Mapping[str, Any]) -> dict[FactKey, Any]:
    """Collect supported non-empty legacy facts under canonical keys."""

    facts: dict[FactKey, Any] = {}
    for fact_key in _SUPPORTED_LEGACY_FACTS:
        value = resolve_legacy_fact(fact_key, session_state)
        if value is not None:
            facts[fact_key] = value
    return facts


def _coerce_fact_key(raw_fact_key: FactKey | str) -> FactKey | None:
    if isinstance(raw_fact_key, FactKey):
        return raw_fact_key
    try:
        return FactKey(raw_fact_key)
    except ValueError:
        return None


def _mutable_fact_state(session_state: Mapping[str, Any]) -> dict[str, Any]:
    raw_state = session_state.get(SSKey.INTAKE_FACTS.value)
    return dict(raw_state) if isinstance(raw_state, dict) else {}


def _job_extract_facts(session_state: Mapping[str, Any]) -> dict[FactKey, Any]:
    raw_extract = session_state.get(SSKey.JOB_EXTRACT.value)
    if not raw_extract:
        return {}
    try:
        job_extract = JobAdExtract.model_validate(raw_extract)
    except Exception:
        return {}

    extract_payload = job_extract.model_dump(mode="json")
    facts: dict[FactKey, Any] = {}
    for fact_key, field_name in _JOB_EXTRACT_FACT_FIELDS.items():
        value = _normalize_fact_value(extract_payload.get(field_name))
        if value is not None:
            facts[fact_key] = value
    return facts


def _session_state_fact(
    fact_key: FactKey,
    session_state: Mapping[str, Any],
) -> Any | None:
    if fact_key == FactKey.ROLE_RESPONSIBILITIES:
        return _normalize_string_list(
            session_state.get(SSKey.ROLE_TASKS_SELECTED.value)
        )
    if fact_key == FactKey.SKILLS_MUST_HAVE_SKILLS:
        return _selected_skills_by_status(session_state, "must")
    if fact_key == FactKey.SKILLS_NICE_TO_HAVE_SKILLS:
        return _selected_skills_by_status(session_state, "nice")
    if fact_key == FactKey.BENEFITS_BENEFITS:
        return _normalize_string_list(session_state.get(SSKey.BENEFITS_SELECTED.value))
    if fact_key == FactKey.INTERVIEW_CONTACTS:
        return _normalize_object_list(
            normalize_interview_internal_flow(
                session_state.get(SSKey.INTERVIEW_INTERNAL_FLOW.value, {})
            ).get("contacts")
        )
    return None


def _selected_skills_by_status(
    session_state: Mapping[str, Any],
    status: str,
) -> list[str] | None:
    selected_raw = session_state.get(SSKey.SKILLS_SELECTED.value)
    statuses_raw = session_state.get(SSKey.SKILLS_SELECTED_STATUS.value)
    if not isinstance(selected_raw, list) or not isinstance(statuses_raw, dict):
        return None

    selected: list[str] = []
    for item in selected_raw:
        label = _normalize_string(item)
        if label is None:
            continue
        status_key = f"label:{label.casefold()}"
        raw_status = statuses_raw.get(status_key)
        if not isinstance(raw_status, dict):
            continue
        if raw_status.get("status") == status:
            selected.append(label)
    return selected or None


def _normalize_fact_value(value: Any) -> Any | None:
    if isinstance(value, str):
        return _normalize_string(value)
    if isinstance(value, list):
        if all(isinstance(item, str) for item in value):
            return _normalize_string_list(value)
        return _normalize_object_list(value)
    if isinstance(value, dict):
        return _normalize_object(value)
    if value is None:
        return None
    return value


def _normalize_string(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = value.strip()
    return cleaned or None


def _normalize_string_list(value: Any) -> list[str] | None:
    if not isinstance(value, list):
        return None
    cleaned = [
        item.strip()
        for item in value
        if isinstance(item, str) and item.strip()
    ]
    return cleaned or None


def _normalize_object_list(value: Any) -> list[dict[str, Any]] | None:
    if not isinstance(value, list):
        return None
    cleaned: list[dict[str, Any]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        normalized = _normalize_object(item)
        if normalized is not None:
            cleaned.append(normalized)
    return cleaned or None


def _normalize_object(value: Mapping[str, Any]) -> dict[str, Any] | None:
    cleaned: dict[str, Any] = {}
    for key, item in value.items():
        if isinstance(item, str):
            normalized = _normalize_string(item)
        elif isinstance(item, list):
            normalized = _normalize_fact_value(item)
        elif isinstance(item, dict):
            normalized = _normalize_object(item)
        else:
            normalized = item
        if normalized is not None:
            cleaned[str(key)] = normalized
    return cleaned or None
