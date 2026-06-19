"""Intake fact adapters for legacy session state."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Mapping, MutableMapping, Sequence

from constants import (
    SUMMARY_ARTIFACT_IDS,
    FactKey,
    FactResolutionStatus,
    FactSensitivity,
    FactSourceType,
    SSKey,
)
from interview_process import normalize_interview_internal_flow
from parsing import redact_pii
from schemas import JobAdExtract


_JOB_EXTRACT_FACT_FIELDS: dict[FactKey, str] = {
    FactKey.COMPANY_LANGUAGE_GUESS: "language_guess",
    FactKey.COMPANY_COMPANY_NAME: "company_name",
    FactKey.COMPANY_BRAND_NAME: "brand_name",
    FactKey.COMPANY_COMPANY_WEBSITE: "company_website",
    FactKey.COMPANY_LOCATION_CITY: "location_city",
    FactKey.COMPANY_LOCATION_COUNTRY: "location_country",
    FactKey.COMPANY_PLACE_OF_WORK: "place_of_work",
    FactKey.COMPANY_REMOTE_POLICY: "remote_policy",
    FactKey.COMPANY_DEPARTMENT_NAME: "department_name",
    FactKey.COMPANY_REPORTS_TO: "reports_to",
    FactKey.COMPANY_DIRECT_REPORTS_COUNT: "direct_reports_count",
    FactKey.ROLE_JOB_TITLE: "job_title",
    FactKey.ROLE_EMPLOYMENT_TYPE: "employment_type",
    FactKey.ROLE_CONTRACT_TYPE: "contract_type",
    FactKey.ROLE_SENIORITY_LEVEL: "seniority_level",
    FactKey.ROLE_JOB_REF_NUMBER: "job_ref_number",
    FactKey.ROLE_ROLE_OVERVIEW: "role_overview",
    FactKey.ROLE_RESPONSIBILITIES: "responsibilities",
    FactKey.ROLE_DELIVERABLES: "deliverables",
    FactKey.ROLE_SUCCESS_METRICS: "success_metrics",
    FactKey.ROLE_TECH_STACK: "tech_stack",
    FactKey.ROLE_DOMAIN_EXPERTISE: "domain_expertise",
    FactKey.ROLE_TRAVEL_REQUIRED: "travel_required",
    FactKey.ROLE_ON_CALL: "on_call",
    FactKey.ROLE_ONBOARDING_NOTES: "onboarding_notes",
    FactKey.ROLE_GAPS: "gaps",
    FactKey.ROLE_ASSUMPTIONS: "assumptions",
    FactKey.SKILLS_MUST_HAVE_SKILLS: "must_have_skills",
    FactKey.SKILLS_NICE_TO_HAVE_SKILLS: "nice_to_have_skills",
    FactKey.SKILLS_SOFT_SKILLS: "soft_skills",
    FactKey.SKILLS_EDUCATION: "education",
    FactKey.SKILLS_CERTIFICATIONS: "certifications",
    FactKey.SKILLS_LANGUAGES: "languages",
    FactKey.BENEFITS_SALARY_RANGE: "salary_range",
    FactKey.BENEFITS_BENEFITS: "benefits",
    FactKey.INTERVIEW_START_DATE: "start_date",
    FactKey.INTERVIEW_APPLICATION_DEADLINE: "application_deadline",
    FactKey.INTERVIEW_RECRUITMENT_STEPS: "recruitment_steps",
    FactKey.INTERVIEW_CONTACTS: "contacts",
}

_SUPPORTED_LEGACY_FACTS: tuple[FactKey, ...] = tuple(FactKey)

_WRITE_THROUGH_FACT_FIELDS: dict[str, FactKey] = {
    "language_guess": FactKey.COMPANY_LANGUAGE_GUESS,
    "company_name": FactKey.COMPANY_COMPANY_NAME,
    "brand_name": FactKey.COMPANY_BRAND_NAME,
    "company_website": FactKey.COMPANY_COMPANY_WEBSITE,
    "location_city": FactKey.COMPANY_LOCATION_CITY,
    "location_country": FactKey.COMPANY_LOCATION_COUNTRY,
    "place_of_work": FactKey.COMPANY_PLACE_OF_WORK,
    "remote_policy": FactKey.COMPANY_REMOTE_POLICY,
    "department_name": FactKey.COMPANY_DEPARTMENT_NAME,
    "reports_to": FactKey.COMPANY_REPORTS_TO,
    "direct_reports_count": FactKey.COMPANY_DIRECT_REPORTS_COUNT,
    "job_title": FactKey.ROLE_JOB_TITLE,
    "employment_type": FactKey.ROLE_EMPLOYMENT_TYPE,
    "contract_type": FactKey.ROLE_CONTRACT_TYPE,
    "seniority_level": FactKey.ROLE_SENIORITY_LEVEL,
    "job_ref_number": FactKey.ROLE_JOB_REF_NUMBER,
    "role_overview": FactKey.ROLE_ROLE_OVERVIEW,
    "responsibilities": FactKey.ROLE_RESPONSIBILITIES,
    "deliverables": FactKey.ROLE_DELIVERABLES,
    "success_metrics": FactKey.ROLE_SUCCESS_METRICS,
    "tech_stack": FactKey.ROLE_TECH_STACK,
    "domain_expertise": FactKey.ROLE_DOMAIN_EXPERTISE,
    "travel_required": FactKey.ROLE_TRAVEL_REQUIRED,
    "on_call": FactKey.ROLE_ON_CALL,
    "onboarding_notes": FactKey.ROLE_ONBOARDING_NOTES,
    "gaps": FactKey.ROLE_GAPS,
    "assumptions": FactKey.ROLE_ASSUMPTIONS,
    "must_have_skills": FactKey.SKILLS_MUST_HAVE_SKILLS,
    "nice_to_have_skills": FactKey.SKILLS_NICE_TO_HAVE_SKILLS,
    "soft_skills": FactKey.SKILLS_SOFT_SKILLS,
    "education": FactKey.SKILLS_EDUCATION,
    "certifications": FactKey.SKILLS_CERTIFICATIONS,
    "languages": FactKey.SKILLS_LANGUAGES,
    "salary_range": FactKey.BENEFITS_SALARY_RANGE,
    "benefits": FactKey.BENEFITS_BENEFITS,
    "start_date": FactKey.INTERVIEW_START_DATE,
    "application_deadline": FactKey.INTERVIEW_APPLICATION_DEADLINE,
    "recruitment_steps": FactKey.INTERVIEW_RECRUITMENT_STEPS,
    "contacts": FactKey.INTERVIEW_CONTACTS,
}

_WRITE_THROUGH_FACTS: frozenset[FactKey] = frozenset(FactKey)
_DEFAULT_CONFIDENCE_BY_SOURCE: dict[FactSourceType, float] = {
    FactSourceType.MANUAL: 1.0,
    FactSourceType.JOBSPEC: 0.75,
    FactSourceType.HOMEPAGE: 0.75,
    FactSourceType.ESCO: 0.75,
    FactSourceType.LLM: 0.75,
}
_DEFAULT_SENSITIVITY_BY_FACT: dict[FactKey, FactSensitivity] = {
    FactKey.INTAKE_SEARCH_CONFIDENTIALITY: FactSensitivity.RESTRICTED,
    FactKey.BENEFITS_SALARY_RANGE: FactSensitivity.RESTRICTED,
    FactKey.BENEFITS_VARIABLE_PAY: FactSensitivity.RESTRICTED,
    FactKey.INTERVIEW_CONTACTS: FactSensitivity.PERSONAL,
}


def get_intake_fact_state(session_state: Mapping[str, Any]) -> dict[str, Any]:
    """Return the additive fact registry state without creating it."""

    raw_state = session_state.get(SSKey.INTAKE_FACTS.value)
    return raw_state if isinstance(raw_state, dict) else {}


def reset_intake_fact_state(session_state: MutableMapping[str, Any]) -> None:
    """Reset additive fact registry state; legacy state remains untouched."""

    session_state[SSKey.INTAKE_FACTS.value] = {}


def get_intake_fact_evidence_state(session_state: Mapping[str, Any]) -> dict[str, Any]:
    """Return additive fact evidence state without creating it."""

    raw_state = session_state.get(SSKey.INTAKE_FACT_EVIDENCE.value)
    return raw_state if isinstance(raw_state, dict) else {}


def reset_intake_fact_evidence_state(session_state: MutableMapping[str, Any]) -> None:
    """Reset additive fact evidence state; legacy state remains untouched."""

    session_state[SSKey.INTAKE_FACT_EVIDENCE.value] = {}


def write_intake_fact(
    session_state: MutableMapping[str, Any],
    fact_key: FactKey | str,
    value: Any,
    *,
    source_type: FactSourceType | str = FactSourceType.MANUAL,
    source_label: str | None = None,
    confidence: float | None = None,
    evidence_snippet: str | None = None,
    confirmed: bool | None = None,
    sensitivity: FactSensitivity | str | None = None,
    resolution_status: FactResolutionStatus | str | None = None,
    used_by_artifacts: Sequence[str] | None = None,
    updated_at: str | None = None,
) -> None:
    """Mirror one supported canonical fact into additive fact state."""

    resolved_key = _coerce_fact_key(fact_key)
    if resolved_key is None or resolved_key not in _WRITE_THROUGH_FACTS:
        return

    normalized_value = _normalize_fact_value(value)
    resolved_source = _coerce_fact_source_type(source_type) or FactSourceType.MANUAL
    fact_state = _mutable_fact_state(session_state)
    previous_value = fact_state.get(resolved_key.value)
    previous_evidence = _mutable_fact_evidence_state(session_state).get(
        resolved_key.value
    )
    if normalized_value is None:
        fact_state.pop(resolved_key.value, None)
        _clear_intake_fact_evidence(session_state, resolved_key)
        _record_manual_fact_lifecycle_event(
            session_state,
            resolved_key,
            source_type=resolved_source,
            previous_value=previous_value,
            normalized_value=None,
            previous_evidence=previous_evidence,
        )
    else:
        fact_state[resolved_key.value] = normalized_value
        write_intake_fact_evidence(
            session_state,
            resolved_key,
            source_type=resolved_source,
            source_label=source_label,
            confidence=confidence,
            evidence_snippet=evidence_snippet,
            confirmed=confirmed,
            sensitivity=sensitivity,
            resolution_status=resolution_status,
            used_by_artifacts=used_by_artifacts,
            updated_at=updated_at,
        )
        _record_manual_fact_lifecycle_event(
            session_state,
            resolved_key,
            source_type=resolved_source,
            previous_value=previous_value,
            normalized_value=normalized_value,
            previous_evidence=previous_evidence,
        )
    session_state[SSKey.INTAKE_FACTS.value] = fact_state


def write_intake_fact_evidence(
    session_state: MutableMapping[str, Any],
    fact_key: FactKey | str,
    *,
    source_type: FactSourceType | str = FactSourceType.MANUAL,
    source_label: str | None = None,
    confidence: float | None = None,
    evidence_snippet: str | None = None,
    confirmed: bool | None = None,
    sensitivity: FactSensitivity | str | None = None,
    resolution_status: FactResolutionStatus | str | None = None,
    used_by_artifacts: Sequence[str] | None = None,
    updated_at: str | None = None,
) -> None:
    """Mirror one supported canonical fact evidence record into additive state."""

    resolved_key = _coerce_fact_key(fact_key)
    if resolved_key is None or resolved_key not in _WRITE_THROUGH_FACTS:
        return

    resolved_source = _coerce_fact_source_type(source_type)
    if resolved_source is None:
        resolved_source = FactSourceType.MANUAL
    resolved_confidence = _normalize_confidence(
        confidence,
        default=_DEFAULT_CONFIDENCE_BY_SOURCE[resolved_source],
    )
    resolved_sensitivity = _coerce_fact_sensitivity(sensitivity) or (
        _DEFAULT_SENSITIVITY_BY_FACT.get(resolved_key, FactSensitivity.NORMAL)
    )
    resolved_resolution = _coerce_fact_resolution_status(resolution_status)
    evidence_state = _mutable_fact_evidence_state(session_state)
    resolved_confirmed = (
        confirmed if confirmed is not None else resolved_source == FactSourceType.MANUAL
    )
    if resolved_resolution is None:
        resolved_resolution = _derive_fact_resolution_status(
            fact_key=resolved_key,
            source_type=resolved_source,
            confirmed=bool(resolved_confirmed),
        )
    previous_entry_raw = evidence_state.get(resolved_key.value)
    previous_entry = (
        previous_entry_raw if isinstance(previous_entry_raw, Mapping) else {}
    )
    previous_secondary = previous_entry.get("secondary_evidence")
    next_entry = {
        "source_type": resolved_source.value,
        "source_label": _normalize_string(source_label)
        or _default_source_label(resolved_source),
        "confidence": resolved_confidence,
        "confirmed": bool(resolved_confirmed),
        "resolution_status": resolved_resolution.value,
        "sensitivity": resolved_sensitivity.value,
        "evidence_snippet": _normalize_evidence_snippet(evidence_snippet),
        "used_by_artifacts": _normalize_used_by_artifacts(used_by_artifacts),
        "updated_at": updated_at or datetime.now(UTC).isoformat(),
    }
    if isinstance(previous_secondary, list) and previous_secondary:
        next_entry["secondary_evidence"] = previous_secondary
    evidence_state[resolved_key.value] = next_entry
    session_state[SSKey.INTAKE_FACT_EVIDENCE.value] = evidence_state


def append_intake_fact_secondary_evidence(
    session_state: MutableMapping[str, Any],
    fact_key: FactKey | str,
    *,
    value: Any,
    source_type: FactSourceType | str,
    source_label: str | None = None,
    confidence: float | None = None,
    evidence_snippet: str | None = None,
    confirmed: bool = False,
    resolution_status: FactResolutionStatus | str | None = None,
    updated_at: str | None = None,
) -> None:
    """Append non-winning evidence for a canonical fact without changing its value."""

    resolved_key = _coerce_fact_key(fact_key)
    if resolved_key is None or resolved_key not in _WRITE_THROUGH_FACTS:
        return

    resolved_source = _coerce_fact_source_type(source_type) or FactSourceType.MANUAL
    resolved_resolution = (
        _coerce_fact_resolution_status(resolution_status)
        or _derive_fact_resolution_status(
            fact_key=resolved_key,
            source_type=resolved_source,
            confirmed=confirmed,
        )
    )
    evidence_state = _mutable_fact_evidence_state(session_state)
    current_raw = evidence_state.get(resolved_key.value)
    current = dict(current_raw) if isinstance(current_raw, Mapping) else {}
    secondary_raw = current.get("secondary_evidence")
    secondary = list(secondary_raw) if isinstance(secondary_raw, list) else []
    secondary.append(
        {
            "source_type": resolved_source.value,
            "source_label": _normalize_string(source_label)
            or _default_source_label(resolved_source),
            "confidence": _normalize_confidence(
                confidence,
                default=_DEFAULT_CONFIDENCE_BY_SOURCE[resolved_source],
            ),
            "confirmed": bool(confirmed),
            "resolution_status": resolved_resolution.value,
            "value": _normalize_fact_value(value),
            "evidence_snippet": _normalize_evidence_snippet(evidence_snippet),
            "updated_at": updated_at or datetime.now(UTC).isoformat(),
        }
    )
    current["secondary_evidence"] = secondary
    evidence_state[resolved_key.value] = current
    session_state[SSKey.INTAKE_FACT_EVIDENCE.value] = evidence_state


def latest_fact_confidence(
    fact_key: FactKey | str,
    evidence_state: Mapping[str, Any] | None,
) -> float | None:
    """Return the latest stored confidence for a canonical fact, if available."""

    resolved_key = _coerce_fact_key(fact_key)
    if resolved_key is None or not isinstance(evidence_state, Mapping):
        return None
    raw_entry = evidence_state.get(resolved_key.value)
    if not isinstance(raw_entry, Mapping):
        return None
    raw_confidence = raw_entry.get("confidence")
    try:
        return _normalize_confidence(float(raw_confidence), default=0.0)
    except (TypeError, ValueError):
        return None


def build_intake_fact_resolution_state(
    session_state: Mapping[str, Any],
    *,
    fact_keys: Sequence[FactKey | str] | None = None,
) -> dict[str, dict[str, Any]]:
    """Return canonical resolution metadata for supported intake facts."""

    fact_state = get_intake_fact_state(session_state)
    evidence_state = get_intake_fact_evidence_state(session_state)
    requested_keys = (
        tuple(fact_keys) if fact_keys is not None else tuple(_SUPPORTED_LEGACY_FACTS)
    )
    resolution_state: dict[str, dict[str, Any]] = {}

    for raw_fact_key in requested_keys:
        fact_key = _coerce_fact_key(raw_fact_key)
        if fact_key is None or fact_key not in _SUPPORTED_LEGACY_FACTS:
            continue

        value = fact_state.get(fact_key.value)
        evidence_raw = evidence_state.get(fact_key.value)
        evidence = evidence_raw if isinstance(evidence_raw, Mapping) else {}
        status = _resolution_status_for_payload(
            value=value,
            evidence=evidence,
        )
        entry: dict[str, Any] = {"status": status.value}
        if value is not None:
            entry["value"] = value
        for field_name in (
            "source_type",
            "source_label",
            "confidence",
            "confirmed",
            "updated_at",
            "used_by_artifacts",
        ):
            if field_name in evidence:
                entry[field_name] = evidence[field_name]
        resolution_state[fact_key.value] = entry

    return resolution_state


def mark_intake_facts_used_by_artifact(
    session_state: MutableMapping[str, Any],
    artifact_id: str,
    *,
    fact_keys: Sequence[FactKey | str] | None = None,
    updated_at: str | None = None,
) -> None:
    """Append one artifact usage marker to existing intake fact evidence rows."""

    normalized_artifact_id = _normalize_string(artifact_id)
    if normalized_artifact_id not in set(SUMMARY_ARTIFACT_IDS):
        return

    evidence_state = _mutable_fact_evidence_state(session_state)
    if not evidence_state:
        return

    if fact_keys is None:
        target_keys = set(evidence_state)
    else:
        target_keys = {
            fact_key.value
            for raw_fact_key in fact_keys
            for fact_key in [_coerce_fact_key(raw_fact_key)]
            if fact_key is not None
        }
    if not target_keys:
        return

    timestamp = updated_at or datetime.now(UTC).isoformat()
    changed = False
    for fact_key in target_keys:
        raw_entry = evidence_state.get(fact_key)
        if not isinstance(raw_entry, Mapping):
            continue
        entry = dict(raw_entry)
        existing_artifacts = entry.get("used_by_artifacts")
        existing_list = (
            list(existing_artifacts) if isinstance(existing_artifacts, list) else []
        )
        next_artifacts = _normalize_used_by_artifacts(
            [*existing_list, normalized_artifact_id]
        )
        if next_artifacts == existing_artifacts:
            continue
        entry["used_by_artifacts"] = next_artifacts
        entry["updated_at"] = timestamp
        evidence_state[fact_key] = entry
        changed = True

    if changed:
        session_state[SSKey.INTAKE_FACT_EVIDENCE.value] = evidence_state


def write_intake_fact_by_legacy_field(
    session_state: MutableMapping[str, Any],
    legacy_field: str,
    value: Any,
    *,
    source_type: FactSourceType | str = FactSourceType.MANUAL,
    source_label: str | None = None,
    confidence: float | None = None,
    evidence_snippet: str | None = None,
    confirmed: bool | None = None,
    sensitivity: FactSensitivity | str | None = None,
    resolution_status: FactResolutionStatus | str | None = None,
    used_by_artifacts: Sequence[str] | None = None,
    updated_at: str | None = None,
) -> None:
    """Mirror a supported legacy field name into additive fact state."""

    fact_key = _WRITE_THROUGH_FACT_FIELDS.get(str(legacy_field or "").strip())
    if fact_key is not None:
        write_intake_fact(
            session_state,
            fact_key,
            value,
            source_type=source_type,
            source_label=source_label,
            confidence=confidence,
            evidence_snippet=evidence_snippet,
            confirmed=confirmed,
            sensitivity=sensitivity,
            resolution_status=resolution_status,
            used_by_artifacts=used_by_artifacts,
            updated_at=updated_at,
        )


def write_job_extract_intake_facts(
    session_state: MutableMapping[str, Any],
    job_extract: JobAdExtract | Mapping[str, Any],
) -> None:
    """Mirror PR3a-supported fields from a reviewed job extract."""

    try:
        payload = JobAdExtract.model_validate(job_extract).model_dump(mode="json")
    except Exception:
        return
    field_evidence = _field_evidence_by_name(payload.get("field_evidence"))
    for field_name in _WRITE_THROUGH_FACT_FIELDS:
        evidence = field_evidence.get(field_name, {})
        write_intake_fact_by_legacy_field(
            session_state,
            field_name,
            payload.get(field_name),
            source_type=FactSourceType.JOBSPEC,
            source_label="Jobspec extraction",
            confidence=evidence.get("confidence", 0.75),
            evidence_snippet=evidence.get("evidence_snippet"),
        )


def sync_selected_skill_intake_facts(session_state: MutableMapping[str, Any]) -> None:
    """Mirror selected free-skill status buckets into PR3a skill facts."""

    write_intake_fact(
        session_state,
        FactKey.SKILLS_MUST_HAVE_SKILLS,
        _selected_skills_by_status(session_state, "must"),
        source_type=FactSourceType.MANUAL,
        source_label="Manual skill selection",
        confidence=1.0,
    )
    write_intake_fact(
        session_state,
        FactKey.SKILLS_NICE_TO_HAVE_SKILLS,
        _selected_skills_by_status(session_state, "nice"),
        source_type=FactSourceType.MANUAL,
        source_label="Manual skill selection",
        confidence=1.0,
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

    intake_fact_state = get_intake_fact_state(session_state)
    if resolved_key.value in intake_fact_state:
        return intake_fact_state.get(resolved_key.value)

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


def _mutable_fact_evidence_state(session_state: Mapping[str, Any]) -> dict[str, Any]:
    raw_state = session_state.get(SSKey.INTAKE_FACT_EVIDENCE.value)
    return dict(raw_state) if isinstance(raw_state, dict) else {}


def _field_evidence_by_name(raw_field_evidence: Any) -> dict[str, Mapping[str, Any]]:
    if not isinstance(raw_field_evidence, list):
        return {}
    evidence_by_name: dict[str, Mapping[str, Any]] = {}
    for raw_entry in raw_field_evidence:
        if not isinstance(raw_entry, Mapping):
            continue
        field_name = _normalize_string(raw_entry.get("field_name"))
        if field_name is None:
            continue
        evidence_by_name[field_name] = raw_entry
    return evidence_by_name


def _clear_intake_fact_evidence(
    session_state: MutableMapping[str, Any],
    fact_key: FactKey,
) -> None:
    evidence_state = _mutable_fact_evidence_state(session_state)
    evidence_state.pop(fact_key.value, None)
    session_state[SSKey.INTAKE_FACT_EVIDENCE.value] = evidence_state


def _record_manual_fact_lifecycle_event(
    session_state: MutableMapping[str, Any],
    fact_key: FactKey,
    *,
    source_type: FactSourceType,
    previous_value: Any,
    normalized_value: Any | None,
    previous_evidence: Any,
) -> None:
    if source_type != FactSourceType.MANUAL:
        return
    source_value = source_type.value
    if normalized_value is None:
        if previous_value is not None:
            _record_fact_rejected(
                session_state,
                fact_key=fact_key.value,
                source_type=source_value,
            )
        return
    if previous_value is None:
        _record_fact_confirmed(
            session_state,
            fact_key=fact_key.value,
            source_type=source_value,
        )
        return
    if previous_value != normalized_value:
        _record_fact_corrected(
            session_state,
            fact_key=fact_key.value,
            source_type=source_value,
        )
        return
    if _evidence_source_type(previous_evidence) != source_value:
        _record_fact_confirmed(
            session_state,
            fact_key=fact_key.value,
            source_type=source_value,
        )


def _record_fact_confirmed(
    session_state: MutableMapping[str, Any],
    *,
    fact_key: str,
    source_type: str | None = None,
) -> None:
    from usage_events import record_fact_confirmed

    record_fact_confirmed(
        session_state,
        fact_key=fact_key,
        source_type=source_type,
    )


def _record_fact_corrected(
    session_state: MutableMapping[str, Any],
    *,
    fact_key: str,
    source_type: str | None = None,
) -> None:
    from usage_events import record_fact_corrected

    record_fact_corrected(
        session_state,
        fact_key=fact_key,
        source_type=source_type,
    )


def _record_fact_rejected(
    session_state: MutableMapping[str, Any],
    *,
    fact_key: str,
    source_type: str | None = None,
) -> None:
    from usage_events import record_fact_rejected

    record_fact_rejected(
        session_state,
        fact_key=fact_key,
        source_type=source_type,
    )


def _evidence_source_type(raw_evidence: Any) -> str | None:
    if not isinstance(raw_evidence, Mapping):
        return None
    source_type = raw_evidence.get("source_type")
    return source_type if isinstance(source_type, str) else None


def _coerce_fact_source_type(
    raw_source_type: FactSourceType | str,
) -> FactSourceType | None:
    if isinstance(raw_source_type, FactSourceType):
        return raw_source_type
    try:
        return FactSourceType(str(raw_source_type))
    except ValueError:
        return None


def _coerce_fact_sensitivity(
    raw_sensitivity: FactSensitivity | str | None,
) -> FactSensitivity | None:
    if isinstance(raw_sensitivity, FactSensitivity):
        return raw_sensitivity
    if not isinstance(raw_sensitivity, str):
        return None
    try:
        return FactSensitivity(raw_sensitivity)
    except ValueError:
        return None


def _coerce_fact_resolution_status(
    raw_status: FactResolutionStatus | str | None,
) -> FactResolutionStatus | None:
    if isinstance(raw_status, FactResolutionStatus):
        return raw_status
    if not isinstance(raw_status, str):
        return None
    try:
        return FactResolutionStatus(raw_status)
    except ValueError:
        return None


def _derive_fact_resolution_status(
    *,
    fact_key: FactKey,
    source_type: FactSourceType,
    confirmed: bool,
) -> FactResolutionStatus:
    if confirmed:
        return FactResolutionStatus.CONFIRMED
    if fact_key == FactKey.ROLE_ASSUMPTIONS:
        return FactResolutionStatus.ASSUMED
    if source_type in {
        FactSourceType.JOBSPEC,
        FactSourceType.HOMEPAGE,
        FactSourceType.ESCO,
        FactSourceType.LLM,
    }:
        return FactResolutionStatus.INFERRED
    return FactResolutionStatus.MISSING


def _resolution_status_for_payload(
    *,
    value: Any,
    evidence: Mapping[str, Any],
) -> FactResolutionStatus:
    if value is None:
        return FactResolutionStatus.MISSING
    explicit_status = _coerce_fact_resolution_status(evidence.get("resolution_status"))
    if explicit_status is not None:
        return explicit_status
    if bool(evidence.get("confirmed")):
        return FactResolutionStatus.CONFIRMED
    return FactResolutionStatus.INFERRED


def _normalize_confidence(value: Any, *, default: float) -> float:
    if value is None:
        value = default
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return max(0.0, min(1.0, float(default)))


def _normalize_evidence_snippet(value: Any) -> str | None:
    snippet = _normalize_string(value)
    if snippet is None:
        return None
    return _normalize_string(redact_pii(snippet))


def _normalize_used_by_artifacts(raw_artifacts: Sequence[str] | None) -> list[str]:
    if raw_artifacts is None:
        return []
    valid_ids = set(SUMMARY_ARTIFACT_IDS)
    normalized: list[str] = []
    for raw_artifact in raw_artifacts:
        artifact_id = _normalize_string(raw_artifact)
        if artifact_id is None or artifact_id not in valid_ids:
            continue
        if artifact_id not in normalized:
            normalized.append(artifact_id)
    return normalized


def _default_source_label(source_type: FactSourceType) -> str:
    if source_type == FactSourceType.MANUAL:
        return "Manual input"
    if source_type == FactSourceType.JOBSPEC:
        return "Jobspec extraction"
    if source_type == FactSourceType.HOMEPAGE:
        return "Homepage research"
    if source_type == FactSourceType.ESCO:
        return "ESCO enrichment"
    return "LLM output"


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
