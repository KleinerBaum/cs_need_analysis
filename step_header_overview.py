"""Derived payloads for compact extracted-data step headers."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Literal

from constants import (
    ESCO_ANCHOR_STATE_ANCHORED,
    ESCO_ANCHOR_STATE_ANCHORED_WITH_CONTEXT,
    FactKey,
    SSKey,
    STEP_KEY_BENEFITS,
    STEP_KEY_COMPANY,
    STEP_KEY_INTERVIEW,
    STEP_KEY_ROLE_TASKS,
    STEP_KEY_SKILLS,
    SUMMARY_ACTIVE_ARTIFACT_IDS,
)
from schemas import JobAdExtract
from step_sections import has_meaningful_fact_value

StepHeaderTone = Literal["neutral", "primary", "success", "warning"]


@dataclass(frozen=True)
class StepHeaderItem:
    label: str
    value: str = ""
    items: tuple[str, ...] = ()
    count: int | None = None
    tone: StepHeaderTone = "neutral"


@dataclass(frozen=True)
class StepHeaderGroup:
    title: str
    items: tuple[StepHeaderItem, ...]
    tone: StepHeaderTone = "neutral"


@dataclass(frozen=True)
class StepHeaderOverview:
    groups: tuple[StepHeaderGroup, ...]


_JOB_EXTRACT_ATTR_BY_FACT: dict[FactKey, str] = {
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

_PERIOD_LABELS = {
    "yearly": "year",
    "monthly": "month",
    "hourly": "hour",
    "one_time": "one-time",
}


def build_step_header_overview(
    *,
    step_key: str,
    step_payload: Mapping[str, Any],
    session_state: Mapping[str, Any],
) -> StepHeaderOverview | None:
    """Build a compact, read-only preview of data connected to a wizard step."""

    facts = _mapping(step_payload.get("intake_facts"))
    job = _coerce_job_extract(step_payload.get("job_extract"))
    section_statuses = _sequence(step_payload.get("section_statuses"))
    if step_key == STEP_KEY_COMPANY:
        return _build_company_overview(
            facts=facts,
            job=job,
            section_statuses=section_statuses,
        )
    if step_key == STEP_KEY_ROLE_TASKS:
        return _build_role_tasks_overview(
            facts=facts,
            job=job,
            session_state=session_state,
            section_statuses=section_statuses,
        )
    if step_key == STEP_KEY_SKILLS:
        return _build_skills_overview(facts=facts, job=job, session_state=session_state)
    if step_key == STEP_KEY_BENEFITS:
        return _build_benefits_overview(facts=facts, job=job, session_state=session_state)
    if step_key == STEP_KEY_INTERVIEW:
        return _build_interview_overview(facts=facts, job=job, session_state=session_state)
    return None


def build_summary_header_overview(
    *,
    readiness_percent: int,
    completion_text: str,
    blocker_count: int,
    esco_ready: bool,
    brief_state: str,
    brief_status_label: str,
    ready_for_follow_ups: bool,
    session_state: Mapping[str, Any],
) -> StepHeaderOverview:
    """Build the Summary header overview from existing readiness/artifact state."""

    active_artifact = _compact(session_state.get(SSKey.SUMMARY_ACTIVE_ARTIFACT.value))
    artifact_errors = _mapping(
        session_state.get(SSKey.SUMMARY_ARTIFACT_LAST_ERROR.value)
    )
    generated_count = sum(
        1
        for artifact_id in SUMMARY_ACTIVE_ARTIFACT_IDS
        if has_meaningful_fact_value(session_state.get(_artifact_state_key(artifact_id)))
    )
    brief_tone: StepHeaderTone = (
        "success" if brief_state in {"current", "ready"} else "warning"
    )
    groups = (
        StepHeaderGroup(
            title="Freigabe",
            tone="success" if ready_for_follow_ups else "warning",
            items=_items(
                StepHeaderItem(
                    "Bereitschaft",
                    f"{readiness_percent}%",
                    tone="success" if ready_for_follow_ups else "warning",
                ),
                StepHeaderItem(
                    "Release-Blocker",
                    str(blocker_count),
                    tone="success" if blocker_count == 0 else "warning",
                ),
                StepHeaderItem("Kritische Fakten", completion_text),
                StepHeaderItem(
                    "ESCO",
                    "Bestätigt" if esco_ready else "Offen",
                    tone="success" if esco_ready else "warning",
                ),
            ),
        ),
        StepHeaderGroup(
            title="Unterlagen",
            items=_items(
                StepHeaderItem("Brief", _clip(brief_status_label, 72), tone=brief_tone),
                StepHeaderItem("Aktiv", active_artifact or "Recruiting Brief"),
                StepHeaderItem(
                    "Erstellt",
                    f"{generated_count}/{len(SUMMARY_ACTIVE_ARTIFACT_IDS)}",
                ),
                StepHeaderItem(
                    "Fehler",
                    str(len(artifact_errors)),
                    tone="warning" if artifact_errors else "success",
                ),
            ),
        ),
    )
    return StepHeaderOverview(groups=_non_empty_groups(groups))


def _build_company_overview(
    *,
    facts: Mapping[str, Any],
    job: JobAdExtract | None,
    section_statuses: Sequence[Any],
) -> StepHeaderOverview | None:
    company_values = _dedupe(
        [
            _fact_text(FactKey.COMPANY_COMPANY_NAME, facts, job),
            _fact_text(FactKey.COMPANY_BRAND_NAME, facts, job),
        ]
    )
    location_values = _dedupe(
        [
            _fact_text(FactKey.COMPANY_LOCATION_CITY, facts, job),
            _fact_text(FactKey.COMPANY_LOCATION_COUNTRY, facts, job),
            _fact_text(FactKey.COMPANY_PLACE_OF_WORK, facts, job),
        ]
    )
    work_model = _dedupe(
        [
            _fact_text(FactKey.COMPANY_WORK_ARRANGEMENT, facts, job),
            _fact_text(FactKey.COMPANY_REMOTE_POLICY, facts, job),
        ]
    )
    team_values = _dedupe(
        [
            _fact_text(FactKey.COMPANY_DEPARTMENT_NAME, facts, job),
            _reports_to_text(facts, job),
            _direct_reports_text(facts, job),
        ]
    )
    context_values = _dedupe(
        [
            _fact_text(FactKey.COMPANY_EMPLOYER_PITCH, facts, job),
            *_fact_list(FactKey.COMPANY_ROLE_RELEVANT_POSITIONING, facts, job),
            _fact_text(FactKey.COMPANY_HIRING_REASON, facts, job),
            _fact_text(FactKey.COMPANY_ROLE_BUSINESS_IMPACT, facts, job),
        ]
    )
    groups = (
        StepHeaderGroup(
            "Arbeitgeber",
            _items(
                _chip_item("Unternehmen", company_values, tone="primary"),
                _chip_item("Standort", location_values),
                _chip_item("Arbeitsmodell", work_model),
                _chip_item("Team", team_values),
            ),
        ),
        StepHeaderGroup(
            "Kontext",
            _items(
                _chip_item("Positionierung", context_values),
                _value_item("Website", _fact_text(FactKey.COMPANY_COMPANY_WEBSITE, facts, job)),
                _missing_item(section_statuses),
            ),
        ),
    )
    return _overview_or_none(groups)


def _build_role_tasks_overview(
    *,
    facts: Mapping[str, Any],
    job: JobAdExtract | None,
    session_state: Mapping[str, Any],
    section_statuses: Sequence[Any],
) -> StepHeaderOverview | None:
    selected_tasks = _string_list(session_state.get(SSKey.ROLE_TASKS_SELECTED.value))
    responsibilities = selected_tasks or _fact_list(FactKey.ROLE_RESPONSIBILITIES, facts, job)
    deliverables = _fact_list(FactKey.ROLE_DELIVERABLES, facts, job)
    success_metrics = _fact_list(FactKey.ROLE_SUCCESS_METRICS, facts, job)
    tech_domain = _dedupe(
        [
            *_fact_list(FactKey.ROLE_TECH_STACK, facts, job),
            *_fact_list(FactKey.ROLE_DOMAIN_EXPERTISE, facts, job),
        ]
    )
    groups = (
        StepHeaderGroup(
            "Rolle",
            _items(
                _value_item(
                    "Titel",
                    _fact_text(FactKey.ROLE_JOB_TITLE, facts, job),
                    tone="primary",
                ),
                _chip_item(
                    "Vertrag",
                    _dedupe(
                        [
                            _fact_text(FactKey.ROLE_EMPLOYMENT_TYPE, facts, job),
                            _fact_text(FactKey.ROLE_CONTRACT_TYPE, facts, job),
                            _fact_text(FactKey.ROLE_SENIORITY_LEVEL, facts, job),
                        ]
                    ),
                ),
                _value_item(
                    "Beitrag",
                    _fact_text(FactKey.ROLE_BUSINESS_OUTCOME_PRIMARY, facts, job),
                ),
            ),
        ),
        StepHeaderGroup(
            "Aufgaben",
            _items(
                _chip_item(
                    "Aufgaben",
                    responsibilities,
                    count=len(responsibilities),
                    tone="primary",
                ),
                _chip_item("Ergebnisse", deliverables, count=len(deliverables)),
                _chip_item("Erfolg", success_metrics, count=len(success_metrics)),
            ),
        ),
        StepHeaderGroup(
            "Signale",
            _items(
                _chip_item("Tech & Domain", tech_domain, count=len(tech_domain)),
                _chip_item(
                    "Annahmen",
                    _fact_list(FactKey.ROLE_ASSUMPTIONS, facts, job),
                    tone="warning",
                ),
                _chip_item("Lücken", _fact_list(FactKey.ROLE_GAPS, facts, job), tone="warning"),
                _missing_item(section_statuses),
            ),
        ),
    )
    return _overview_or_none(groups)


def _build_skills_overview(
    *,
    facts: Mapping[str, Any],
    job: JobAdExtract | None,
    session_state: Mapping[str, Any],
) -> StepHeaderOverview | None:
    must_skills = _selected_skills(session_state, status="must") or _fact_list(
        FactKey.SKILLS_MUST_HAVE_SKILLS, facts, job
    )
    nice_skills = _selected_skills(session_state, status="nice") or _fact_list(
        FactKey.SKILLS_NICE_TO_HAVE_SKILLS, facts, job
    )
    tech_stack = _fact_list(FactKey.ROLE_TECH_STACK, facts, job)
    certifications = _dedupe(
        [
            *_fact_list(FactKey.SKILLS_CERTIFICATIONS, facts, job),
            *_fact_list(FactKey.SKILLS_LANGUAGES, facts, job),
        ]
    )
    esco_title = _esco_title(session_state)
    unmapped_terms = _string_list(
        session_state.get(SSKey.ESCO_UNMAPPED_REQUIREMENT_TERMS.value)
    )
    groups = (
        StepHeaderGroup(
            "Anforderungen",
            _items(
                _chip_item("Must-have", must_skills, count=len(must_skills), tone="primary"),
                _chip_item("Nice-to-have", nice_skills, count=len(nice_skills)),
                _chip_item("Tech Stack", tech_stack, count=len(tech_stack)),
                _chip_item("Zertifikate & Sprachen", certifications, count=len(certifications)),
            ),
        ),
        StepHeaderGroup(
            "Mapping",
            _items(
                _value_item(
                    "ESCO",
                    esco_title or "Noch nicht bestätigt",
                    tone="success" if esco_title else "warning",
                ),
                _chip_item(
                    "Offene Begriffe",
                    unmapped_terms,
                    count=len(unmapped_terms),
                    tone="warning",
                ),
                _chip_item(
                    "KO-Kriterien",
                    _fact_list(FactKey.SKILLS_KNOCKOUT_CRITERIA, facts, job),
                    tone="warning",
                ),
                _chip_item("Trainierbar", _fact_list(FactKey.SKILLS_TRAINABLE_SKILLS, facts, job)),
            ),
        ),
    )
    return _overview_or_none(groups)


def _build_benefits_overview(
    *,
    facts: Mapping[str, Any],
    job: JobAdExtract | None,
    session_state: Mapping[str, Any],
) -> StepHeaderOverview | None:
    selected_benefits = _string_list(session_state.get(SSKey.BENEFITS_SELECTED.value))
    benefits = selected_benefits or _fact_list(FactKey.BENEFITS_BENEFITS, facts, job)
    groups = (
        StepHeaderGroup(
            "Angebot",
            _items(
                _value_item(
                    "Gehalt",
                    _salary_text(
                        _fact_raw(FactKey.BENEFITS_SALARY_RANGE, facts, job)
                    ),
                    tone="primary",
                ),
                _value_item(
                    "Variable Vergütung",
                    _variable_pay_text(
                        _fact_raw(FactKey.BENEFITS_VARIABLE_PAY, facts, job)
                    ),
                ),
                _chip_item("Benefits", benefits, count=len(benefits)),
                _chip_item("Bausteine", _fact_list(FactKey.BENEFITS_OFFER_COMPONENTS, facts, job)),
            ),
        ),
        StepHeaderGroup(
            "Rahmen",
            _items(
                _chip_item(
                    "Arbeitsmodell",
                    _dedupe(
                        [
                            _fact_text(FactKey.COMPANY_WORK_ARRANGEMENT, facts, job),
                            _fact_text(FactKey.COMPANY_REMOTE_POLICY, facts, job),
                        ]
                    ),
                ),
                _value_item(
                    "Start",
                    _start_flexibility_text(
                        _fact_raw(FactKey.TIMELINE_START_FLEXIBILITY, facts, job)
                    ),
                ),
                _value_item(
                    "Reise",
                    _travel_text(_fact_raw(FactKey.ROLE_TRAVEL_PROFILE, facts, job)),
                ),
                _value_item(
                    "Schicht/Rufbereitschaft",
                    _shift_text(
                        _fact_raw(FactKey.BENEFITS_SHIFT_COMPENSATION, facts, job)
                    ),
                ),
                _chip_item(
                    "Tarif/Vorgaben",
                    _fact_list(
                        FactKey.BENEFITS_COLLECTIVE_AGREEMENT_CONTEXT, facts, job
                    ),
                ),
            ),
        ),
    )
    return _overview_or_none(groups)


def _build_interview_overview(
    *,
    facts: Mapping[str, Any],
    job: JobAdExtract | None,
    session_state: Mapping[str, Any],
) -> StepHeaderOverview | None:
    stages = _fact_list(FactKey.INTERVIEW_RECRUITMENT_STEPS, facts, job)
    internal_flow_contacts = _mapping(
        session_state.get(SSKey.INTERVIEW_INTERNAL_FLOW.value)
    ).get("contacts")
    contacts_count = len(
        _object_list(_fact_raw(FactKey.INTERVIEW_CONTACTS, facts, job))
    ) + len(
        _object_list(internal_flow_contacts)
    )
    stage_owners = _object_list(_fact_raw(FactKey.INTERVIEW_STAGE_OWNERS, facts, job))
    communication = _fact_list(FactKey.INTERVIEW_COMMUNICATION_SLA, facts, job)
    evidence = _fact_list(FactKey.INTERVIEW_ASSESSMENT_EVIDENCE, facts, job)
    core_questions = _fact_list(FactKey.INTERVIEW_CORE_QUESTIONS, facts, job)
    scorecard = _scorecard_text(
        _fact_raw(FactKey.INTERVIEW_SCORECARD_TEMPLATE, facts, job)
    )
    groups = (
        StepHeaderGroup(
            "Prozess",
            _items(
                _chip_item("Stufen", stages, count=len(stages), tone="primary"),
                _value_item("Owner", f"{len(stage_owners)} Rollen geklärt" if stage_owners else ""),
                _chip_item("SLA", communication, count=len(communication)),
                _value_item("Kontakte", f"{contacts_count} hinterlegt" if contacts_count else ""),
            ),
        ),
        StepHeaderGroup(
            "Bewertung",
            _items(
                _value_item("Scorecard", scorecard),
                _chip_item("Nachweise", evidence, count=len(evidence)),
                _chip_item("Kernfragen", core_questions, count=len(core_questions)),
                _value_item(
                    "Compliance",
                    _fact_text(FactKey.INTERVIEW_COMPLIANCE_NOTES, facts, job),
                    tone="warning",
                ),
            ),
        ),
    )
    return _overview_or_none(groups)


def _artifact_state_key(artifact_id: str) -> str:
    if artifact_id == "brief":
        return SSKey.BRIEF.value
    if artifact_id == "job_ad":
        return SSKey.JOB_AD_DRAFT_CUSTOM.value
    if artifact_id == "interview_hr":
        return SSKey.INTERVIEW_PREP_HR.value
    if artifact_id == "interview_fach":
        return SSKey.INTERVIEW_PREP_FACH.value
    if artifact_id == "boolean_search":
        return SSKey.BOOLEAN_SEARCH_STRING.value
    return ""


def _fact_raw(
    fact_key: FactKey,
    facts: Mapping[str, Any],
    job: JobAdExtract | None,
) -> Any:
    value = facts.get(fact_key.value)
    if has_meaningful_fact_value(value):
        return value
    if job is None:
        return None
    attr = _JOB_EXTRACT_ATTR_BY_FACT.get(fact_key)
    if not attr:
        return None
    value = getattr(job, attr, None)
    return value if has_meaningful_fact_value(value) else None


def _fact_text(
    fact_key: FactKey,
    facts: Mapping[str, Any],
    job: JobAdExtract | None,
) -> str:
    return _format_scalar(_fact_raw(fact_key, facts, job))


def _fact_list(
    fact_key: FactKey,
    facts: Mapping[str, Any],
    job: JobAdExtract | None,
) -> list[str]:
    return _string_list(_fact_raw(fact_key, facts, job))


def _selected_skills(session_state: Mapping[str, Any], *, status: str) -> list[str]:
    selected = _string_list(session_state.get(SSKey.SKILLS_SELECTED.value))
    statuses = _mapping(session_state.get(SSKey.SKILLS_SELECTED_STATUS.value))
    output: list[str] = []
    for label in selected:
        status_payload = _mapping(statuses.get(f"label:{label.casefold()}"))
        if status_payload.get("status") == status:
            output.append(label)
    esco_key = (
        SSKey.ESCO_CONFIRMED_ESSENTIAL_SKILLS
        if status == "must"
        else SSKey.ESCO_CONFIRMED_OPTIONAL_SKILLS
    )
    selected_key = (
        SSKey.ESCO_SKILLS_SELECTED_MUST
        if status == "must"
        else SSKey.ESCO_SKILLS_SELECTED_NICE
    )
    output.extend(_string_list(session_state.get(esco_key.value)))
    if not output:
        output.extend(_string_list(session_state.get(selected_key.value)))
    return _dedupe(output)


def _esco_title(session_state: Mapping[str, Any]) -> str:
    anchor_state = _compact(session_state.get(SSKey.ESCO_ANCHOR_STATE.value))
    if anchor_state not in {ESCO_ANCHOR_STATE_ANCHORED, ESCO_ANCHOR_STATE_ANCHORED_WITH_CONTEXT}:
        return ""
    selected = _mapping(session_state.get(SSKey.ESCO_OCCUPATION_SELECTED.value))
    anchor = _mapping(session_state.get(SSKey.ESCO_PRIMARY_ANCHOR.value))
    return (
        _compact(selected.get("title"))
        or _compact(selected.get("preferredLabel"))
        or _compact(anchor.get("title"))
        or _compact(anchor.get("preferredLabel"))
    )


def _missing_item(section_statuses: Sequence[Any]) -> StepHeaderItem | None:
    missing: list[str] = []
    for raw_status in section_statuses:
        status = _mapping(raw_status)
        missing.extend(_string_list(status.get("missing_labels")))
    deduped = _dedupe(missing)
    return _chip_item("Noch offen", deduped, count=len(deduped), tone="warning")


def _reports_to_text(facts: Mapping[str, Any], job: JobAdExtract | None) -> str:
    reports_to = _fact_text(FactKey.COMPANY_REPORTS_TO, facts, job)
    return f"Berichtet an {reports_to}" if reports_to else ""


def _direct_reports_text(facts: Mapping[str, Any], job: JobAdExtract | None) -> str:
    count = _fact_text(FactKey.COMPANY_DIRECT_REPORTS_COUNT, facts, job)
    return f"{count} Direct Reports" if count else ""


def _salary_text(value: Any) -> str:
    payload = _object(value)
    salary_min = _compact(payload.get("min"))
    salary_max = _compact(payload.get("max"))
    if not salary_min and not salary_max:
        return ""
    if salary_min and salary_max:
        amount = f"{salary_min} - {salary_max}"
    elif salary_min:
        amount = f"ab {salary_min}"
    else:
        amount = f"bis {salary_max}"
    suffix = " ".join(
        item
        for item in (
            _compact(payload.get("currency")),
            _PERIOD_LABELS.get(
                _compact(payload.get("period")),
                _compact(payload.get("period")),
            ),
        )
        if item
    )
    return f"{amount} {suffix}".strip()


def _variable_pay_text(value: Any) -> str:
    payload = _object(value)
    eligible = payload.get("eligible")
    if eligible is False:
        return "Nicht vorgesehen"
    ote_min = _compact(payload.get("ote_min"))
    ote_max = _compact(payload.get("ote_max"))
    currency = _compact(payload.get("currency"))
    period = _PERIOD_LABELS.get(
        _compact(payload.get("period")),
        _compact(payload.get("period")),
    )
    if ote_min or ote_max:
        amount = f"{ote_min} - {ote_max}".strip(" -")
        return " ".join(item for item in (amount, currency, period) if item)
    if eligible is True:
        return "Vorgesehen"
    return _compact(payload.get("bonus_logic"))


def _start_flexibility_text(value: Any) -> str:
    payload = _object(value)
    return " · ".join(
        item
        for item in (
            _compact(payload.get("target_start")),
            _compact(payload.get("flexibility")),
            _compact(payload.get("notice_period")),
        )
        if item
    )


def _travel_text(value: Any) -> str:
    payload = _object(value)
    if payload.get("required") is False:
        return "Keine Reise"
    parts = [
        _compact(payload.get("frequency")),
        _compact(payload.get("percent")) + "%"
        if _compact(payload.get("percent"))
        else "",
        _compact(payload.get("region")),
    ]
    return " · ".join(item for item in parts if item)


def _shift_text(value: Any) -> str:
    payload = _object(value)
    return " · ".join(
        item
        for item in (
            _compact(payload.get("rotation")),
            _compact(payload.get("compensation")),
            _compact(payload.get("notes")),
        )
        if item
    )


def _scorecard_text(value: Any) -> str:
    payload = _object(value)
    criteria = _sequence(payload.get("criteria"))
    if criteria:
        stage = _compact(payload.get("stage"))
        return f"{len(criteria)} Kriterien" + (f" · {stage}" if stage else "")
    return _compact(payload.get("notes"))


def _chip_item(
    label: str,
    items: Sequence[str],
    *,
    count: int | None = None,
    tone: StepHeaderTone = "neutral",
) -> StepHeaderItem | None:
    normalized = _dedupe(items)
    if not normalized and not count:
        return None
    return StepHeaderItem(label=label, items=tuple(normalized[:6]), count=count, tone=tone)


def _value_item(
    label: str,
    value: str,
    *,
    tone: StepHeaderTone = "neutral",
) -> StepHeaderItem | None:
    text = _compact(value)
    if not text:
        return None
    return StepHeaderItem(label=label, value=_clip(text, 90), tone=tone)


def _items(*items: StepHeaderItem | None) -> tuple[StepHeaderItem, ...]:
    return tuple(item for item in items if item is not None)


def _overview_or_none(groups: Sequence[StepHeaderGroup]) -> StepHeaderOverview | None:
    non_empty = _non_empty_groups(groups)
    if not non_empty:
        return None
    return StepHeaderOverview(groups=non_empty)


def _non_empty_groups(groups: Sequence[StepHeaderGroup]) -> tuple[StepHeaderGroup, ...]:
    return tuple(group for group in groups if group.items)


def _string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [_compact(value)] if _compact(value) else []
    if isinstance(value, Mapping):
        label = (
            _compact(value.get("label"))
            or _compact(value.get("title"))
            or _compact(value.get("name"))
            or _compact(value.get("stage"))
            or _compact(value.get("event"))
            or _compact(value.get("item"))
        )
        if label:
            detail = (
                _compact(value.get("goal"))
                or _compact(value.get("details"))
                or _compact(value.get("success_signal"))
            )
            return [f"{label}: {detail}" if detail else label]
        parts = [
            f"{_compact(key)}: {_compact(item)}"
            for key, item in value.items()
            if _compact(item) and not isinstance(item, (Mapping, list, tuple, set))
        ]
        return ["; ".join(parts)] if parts else []
    if hasattr(value, "model_dump"):
        return _string_list(value.model_dump(mode="json"))
    if isinstance(value, Sequence):
        output: list[str] = []
        for item in value:
            output.extend(_string_list(item))
        return _dedupe(output)
    return [_compact(value)] if _compact(value) else []


def _object_list(value: Any) -> list[Mapping[str, Any]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return []
    output: list[Mapping[str, Any]] = []
    for item in value:
        if isinstance(item, Mapping):
            output.append(item)
        elif hasattr(item, "model_dump"):
            output.append(item.model_dump(mode="json"))
    return output


def _object(value: Any) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    return {}


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _sequence(value: Any) -> Sequence[Any]:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return value
    return ()


def _coerce_job_extract(value: Any) -> JobAdExtract | None:
    if isinstance(value, JobAdExtract):
        return value
    if not value:
        return None
    try:
        return JobAdExtract.model_validate(value)
    except Exception:
        return None


def _format_scalar(value: Any) -> str:
    if isinstance(value, Mapping):
        return ""
    if hasattr(value, "model_dump"):
        return ""
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return ""
    return _compact(value)


def _compact(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _clip(value: str, limit: int) -> str:
    text = _compact(value)
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)].rstrip() + "…"


def _dedupe(values: Sequence[str]) -> list[str]:
    output: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = _compact(value)
        key = text.casefold()
        if not text or key in seen:
            continue
        output.append(text)
        seen.add(key)
    return output
