"""Pure helpers for Summary export formatting and input fingerprints."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from typing import Any

from constants import APP_NAME, FactKey, SSKey, VACANCY_DRAFT_SCHEMA_VERSION
from schemas import BooleanSearchPack, JobAdExtract, VacancyBrief
from ux_copy_contract import (
    summary_export_copy,
    summary_preview_copy,
)

VACANCY_DRAFT_SCHEMA_ID = "cs_need_analysis.vacancy_draft"
LIVE_ARTIFACT_PREVIEW_NOTICE = summary_preview_copy("notice", language="en")


def build_summary_input_fingerprint(
    *,
    job: JobAdExtract,
    answers: dict[str, Any],
    selected_role_tasks: list[str],
    selected_skills: list[str],
    selected_benefits: list[str],
    esco_occupation_selected: dict[str, str],
    esco_match_explainability: dict[str, Any],
    esco_selected_skills_must: list[dict[str, str]],
    esco_selected_skills_nice: list[dict[str, str]],
    intake_facts: dict[str, Any] | None = None,
    intake_fact_resolution: dict[str, Any] | None = None,
    confidence_threshold: float | None = None,
    offer_positioning: Mapping[str, Any] | None = None,
    interview_process: Mapping[str, Any] | None = None,
    salary_forecast: Mapping[str, Any] | None = None,
) -> str:
    non_sensitive_payload = {
        "job": job.model_dump(mode="json", exclude_none=True),
        "answers": answers,
        "intake_facts": intake_facts or {},
        "intake_fact_resolution": intake_fact_resolution or {},
        "confidence_threshold": confidence_threshold,
        "offer_positioning": dict(offer_positioning or {}),
        "interview_process": dict(interview_process or {}),
        "salary_forecast": dict(salary_forecast or {}),
        "selected_role_tasks": selected_role_tasks,
        "selected_skills": selected_skills,
        "selected_benefits": selected_benefits,
        "esco_occupation_selected": esco_occupation_selected,
        "esco_match_explainability": esco_match_explainability,
        "esco_selected_skills_must": esco_selected_skills_must,
        "esco_selected_skills_nice": esco_selected_skills_nice,
    }
    serialized = json.dumps(
        non_sensitive_payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _json_safe_draft_value(value: Any) -> Any:
    if value is None or isinstance(value, str | int | float | bool):
        return value
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    if isinstance(value, bytes | bytearray | memoryview):
        return None
    if hasattr(value, "model_dump"):
        try:
            return _json_safe_draft_value(value.model_dump(mode="json"))
        except Exception:
            return str(value)
    if isinstance(value, Mapping):
        return {str(key): _json_safe_draft_value(item) for key, item in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, str):
        return [_json_safe_draft_value(item) for item in value]
    if isinstance(value, set):
        return [_json_safe_draft_value(item) for item in value]
    return str(value)


def build_vacancy_draft_payload(
    session_state: Mapping[str, Any],
    *,
    allowed_keys: Sequence[SSKey],
    saved_at: datetime | None = None,
) -> dict[str, Any]:
    """Build a schema-versioned JSON-safe draft from allowlisted session keys."""

    saved_at_utc = (saved_at or datetime.now(timezone.utc)).astimezone(timezone.utc)
    state_payload: dict[str, Any] = {}
    for key in allowed_keys:
        if key.value not in session_state:
            continue
        state_payload[key.value] = _json_safe_draft_value(session_state[key.value])

    return {
        "schema": VACANCY_DRAFT_SCHEMA_ID,
        "schema_version": VACANCY_DRAFT_SCHEMA_VERSION,
        "application": APP_NAME,
        "saved_at": saved_at_utc.isoformat().replace("+00:00", "Z"),
        "state": state_payload,
    }


def vacancy_draft_state_fingerprint(
    session_state: Mapping[str, Any],
    *,
    allowed_keys: Sequence[SSKey],
) -> str:
    """Return a stable fingerprint for the allowlisted draft state only."""

    state_payload: dict[str, Any] = {}
    for key in allowed_keys:
        if key.value not in session_state:
            continue
        state_payload[key.value] = _json_safe_draft_value(session_state[key.value])
    serialized = json.dumps(
        state_payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def vacancy_draft_payload_to_json(payload: Mapping[str, Any]) -> str:
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        indent=2,
        default=str,
    )


def vacancy_draft_to_json(
    session_state: Mapping[str, Any],
    *,
    allowed_keys: Sequence[SSKey],
    saved_at: datetime | None = None,
) -> str:
    return vacancy_draft_payload_to_json(
        build_vacancy_draft_payload(
            session_state,
            allowed_keys=allowed_keys,
            saved_at=saved_at,
        )
    )


def parse_vacancy_draft_json(raw_json: str | bytes) -> dict[str, Any]:
    if isinstance(raw_json, bytes):
        raw_json = raw_json.decode("utf-8")
    payload = json.loads(raw_json)
    if not isinstance(payload, dict):
        raise ValueError("Draft JSON must contain an object payload.")
    return payload


def _compact_preview_text(value: Any) -> str:
    if isinstance(value, Mapping):
        for key in ("label", "title", "name", "value"):
            compact = _compact_preview_text(value.get(key))
            if compact:
                return compact
        return ""
    if isinstance(value, Sequence) and not isinstance(value, str | bytes):
        parts = [_compact_preview_text(item) for item in value]
        return ", ".join(part for part in parts if part)
    return " ".join(str(value or "").split()).strip()


def _dedupe_preview_items(values: Any, *, limit: int = 4) -> list[str]:
    if isinstance(values, str | bytes) or isinstance(values, Mapping):
        iterable: Sequence[Any] = [values]
    elif isinstance(values, Sequence):
        iterable = values
    else:
        iterable = []

    output: list[str] = []
    seen: set[str] = set()
    for item in iterable:
        compact = _compact_preview_text(item)
        dedupe_key = compact.casefold()
        if not compact or dedupe_key in seen:
            continue
        output.append(compact)
        seen.add(dedupe_key)
        if len(output) >= limit:
            break
    return output


def _preview_sequence_values(value: Any) -> list[Any]:
    if isinstance(value, str | bytes) or isinstance(value, Mapping):
        return [value] if _compact_preview_text(value) else []
    if isinstance(value, Sequence):
        return list(value)
    return []


def _preview_salary_text(job: JobAdExtract, *, language: str | None = None) -> str:
    salary_range = getattr(job, "salary_range", None)
    if salary_range is None:
        return ""
    salary_min = _compact_preview_text(getattr(salary_range, "min", None))
    salary_max = _compact_preview_text(getattr(salary_range, "max", None))
    if salary_min and salary_max:
        amount = f"{salary_min} - {salary_max}"
    elif salary_min:
        amount = summary_preview_copy(
            "salary_from",
            language=language,
            amount=salary_min,
        )
    elif salary_max:
        amount = summary_preview_copy(
            "salary_to",
            language=language,
            amount=salary_max,
        )
    else:
        return ""
    suffix = " ".join(
        item
        for item in (
            _compact_preview_text(getattr(salary_range, "currency", "")),
            _compact_preview_text(getattr(salary_range, "period", "")),
        )
        if item
    )
    return f"{amount} {suffix}".strip()


def _safe_interview_preview_items(interview_process: Mapping[str, Any]) -> list[str]:
    selected_values = interview_process.get("selected_values")
    if not isinstance(selected_values, Sequence) or isinstance(
        selected_values, str | bytes
    ):
        return []
    safe_areas = {
        "interview",
        "timing",
        "zeitplan",
        "kandidatenkommunikation",
        "candidate communication",
    }
    blocked_field_terms = (
        "e-mail",
        "email",
        "telefon",
        "ansprechpartner",
        "contact",
    )
    output: list[str] = []
    for item in selected_values:
        if not isinstance(item, Mapping):
            continue
        area = _compact_preview_text(item.get("Bereich") or item.get("area"))
        field = _compact_preview_text(item.get("Feld") or item.get("field"))
        value = _compact_preview_text(item.get("Wert") or item.get("value"))
        if not value:
            continue
        if area.casefold() not in safe_areas:
            continue
        if any(term in field.casefold() for term in blocked_field_terms):
            continue
        label = " - ".join(part for part in (field, value) if part)
        if label:
            output.append(label)
        if len(output) >= 3:
            break
    return _dedupe_preview_items(output, limit=3)


def _preview_decision_scope_label(value: Any, *, language: str | None = None) -> str:
    normalized = _compact_preview_text(value)
    if normalized == "unklar":
        return ""
    localized = summary_preview_copy(
        f"decision_scope.{normalized}",
        language=language,
    )
    return normalized if localized == f"decision_scope.{normalized}" else localized


def _preview_timeline_items(
    value: Any,
    *,
    limit: int = 3,
    language: str | None = None,
) -> list[str]:
    if not isinstance(value, Mapping):
        return []
    keys = ("30_days", "60_days", "90_days", "180_days")
    items: list[str] = []
    for key in keys:
        compact = _compact_preview_text(value.get(key))
        if compact:
            label = summary_preview_copy(f"timeline.{key}", language=language)
            items.append(f"{label}: {compact}")
        if len(items) >= limit:
            break
    return items


def _preview_prioritized_items(
    value: Any,
    *,
    priority: str,
    limit: int = 3,
) -> list[str]:
    if not isinstance(value, Sequence) or isinstance(value, str | bytes):
        return []
    output: list[str] = []
    for item in value:
        if not isinstance(item, Mapping):
            continue
        if _compact_preview_text(item.get("priority")) != priority:
            continue
        label = _compact_preview_text(item.get("label"))
        if label:
            output.append(label)
        if len(output) >= limit:
            break
    return _dedupe_preview_items(output, limit=limit)


def build_live_artifact_preview_payload(
    *,
    job: JobAdExtract,
    answers: Mapping[str, Any] | None = None,
    selected_role_tasks: Sequence[str] | None = None,
    selected_skills: Sequence[str] | None = None,
    selected_benefits: Sequence[str] | None = None,
    intake_facts: Mapping[str, Any] | None = None,
    interview_process: Mapping[str, Any] | None = None,
    offer_positioning: Mapping[str, Any] | None = None,
    language: str | None = None,
) -> dict[str, Any]:
    """Build concise deterministic artifact previews without generating artifacts."""

    _ = answers  # Reserved for future preview-only routing without changing callers.
    facts = intake_facts or {}
    role_title = _compact_preview_text(job.job_title) or summary_preview_copy(
        "role_fallback",
        language=language,
    )
    company = _compact_preview_text(job.company_name)
    location = _compact_preview_text(job.location_city or job.location_country)
    remote_policy = _compact_preview_text(job.remote_policy)
    salary_text = _preview_salary_text(job, language=language)
    role_summary = _compact_preview_text(job.role_overview) or role_title
    role_outcome = (
        _compact_preview_text(
            facts.get(FactKey.ROLE_BUSINESS_OUTCOME_PRIMARY.value)
        )
        or role_summary
    )
    day1_responsibilities = _dedupe_preview_items(
        facts.get(FactKey.ROLE_DAY1_RESPONSIBILITIES.value, []),
        limit=3,
    )
    expected_outputs = _dedupe_preview_items(
        [
            *list(job.deliverables or []),
            *_preview_sequence_values(facts.get(FactKey.ROLE_DELIVERABLES.value)),
        ],
        limit=3,
    )
    first_success_signals = _dedupe_preview_items(
        [
            *_preview_timeline_items(
                facts.get(FactKey.ROLE_SUCCESS_METRICS_TIMELINE.value, {}),
                language=language,
            ),
            *_dedupe_preview_items(
                facts.get(FactKey.ROLE_YEAR1_SUCCESS_SIGNALS.value, []),
                limit=2,
            ),
            *list(job.success_metrics or []),
        ],
        limit=3,
    )
    decision_scope = _preview_decision_scope_label(
        facts.get(FactKey.ROLE_DECISION_SCOPE.value),
        language=language,
    )
    must_responsibilities = _preview_prioritized_items(
        facts.get(FactKey.ROLE_RESPONSIBILITIES_PRIORITIZED.value, []),
        priority="must",
        limit=3,
    )
    non_negotiables = _dedupe_preview_items(
        facts.get(FactKey.COMPANY_NON_NEGOTIABLES.value, []),
        limit=3,
    )
    tasks = _dedupe_preview_items(
        [
            *(selected_role_tasks or []),
            *day1_responsibilities,
            *must_responsibilities,
            *list(job.responsibilities or []),
        ],
        limit=4,
    )
    skills = _dedupe_preview_items(
        [*(selected_skills or []), *list(job.must_have_skills or [])],
        limit=5,
    )
    nice_skills = _dedupe_preview_items(job.nice_to_have_skills or [], limit=3)
    offer_candidate_value = (
        _preview_sequence_values(offer_positioning.get("candidate_value"))
        if isinstance(offer_positioning, Mapping)
        else []
    )
    benefits = _dedupe_preview_items(
        [*offer_candidate_value, *(selected_benefits or []), *list(job.benefits or [])],
        limit=4,
    )
    salary_caveat = (
        _compact_preview_text(offer_positioning.get("salary_caveat"))
        if isinstance(offer_positioning, Mapping)
        else ""
    )
    open_clarifications = _dedupe_preview_items(
        [*list(job.gaps or []), *list(job.assumptions or [])],
        limit=2,
    )
    stages = _dedupe_preview_items(
        (
            (interview_process or {}).get("candidate_stages", [])
            if isinstance(interview_process, Mapping)
            else []
        )
        or [
            _compact_preview_text(
                f"{step.name}: {step.details}"
                if _compact_preview_text(step.details)
                else step.name
            )
            for step in job.recruitment_steps or []
        ],
        limit=3,
    )
    selected_interview_values = (
        _safe_interview_preview_items(interview_process)
        if isinstance(interview_process, Mapping)
        else []
    )

    scorecard_raw = facts.get(FactKey.INTERVIEW_SCORECARD_TEMPLATE.value)
    scorecard = scorecard_raw if isinstance(scorecard_raw, Mapping) else {}
    criteria_raw = scorecard.get("criteria")
    criteria_items = (
        criteria_raw
        if isinstance(criteria_raw, Sequence) and not isinstance(criteria_raw, str | bytes)
        else []
    )
    scorecard_items = _dedupe_preview_items(
        [
            item.get("title")
            for item in criteria_items
            if isinstance(item, Mapping)
        ],
        limit=3,
    )
    core_questions = _dedupe_preview_items(
        facts.get(FactKey.INTERVIEW_CORE_QUESTIONS.value, []),
        limit=2,
    )

    one_liner = (
        summary_preview_copy(
            "at_company",
            language=language,
            role_title=role_title,
            company=company,
        )
        if company
        else role_title
    )
    prefix = lambda key, value: summary_preview_copy(
        f"prefix.{key}",
        language=language,
        value=value,
    )
    job_ad_signals = _dedupe_preview_items(
        [
            prefix("role", role_title),
            prefix("why_role", role_outcome) if role_outcome else "",
            prefix("outputs", ", ".join(expected_outputs[:2])) if expected_outputs else "",
            prefix("tasks", ", ".join(tasks[:2])) if tasks else "",
            prefix("must_have", ", ".join(skills[:3])) if skills else "",
            prefix("candidate_value", ", ".join(benefits[:3])) if benefits else "",
            prefix("open_clarify", salary_caveat) if salary_caveat else "",
        ],
        limit=4,
    )
    boolean_terms = _dedupe_preview_items([role_title, *skills[:4]], limit=5)
    boolean_guidance = _dedupe_preview_items(
        [
            prefix("search_core", " + ".join(boolean_terms[:4])) if boolean_terms else "",
            prefix("location_filter", location) if location else "",
            prefix("remote_signal", remote_policy) if remote_policy else "",
            prefix("non_negotiable", ", ".join(non_negotiables))
            if non_negotiables
            else "",
            prefix("decision_scope", decision_scope) if decision_scope else "",
            prefix("open_clarify", ", ".join(open_clarifications))
            if open_clarifications
            else "",
            prefix("candidate_value", ", ".join(benefits[:2])) if benefits else "",
            summary_preview_copy("prefix.skill_missing", language=language)
            if not skills
            else "",
        ],
        limit=4,
    )
    interview_guidance = _dedupe_preview_items(
        [
            prefix("success", ", ".join(first_success_signals[:2]))
            if first_success_signals
            else "",
            prefix("validate_responsibility", decision_scope)
            if decision_scope
            else "",
            prefix("validate", ", ".join(skills[:3])) if skills else "",
            prefix("work_sample", ", ".join(expected_outputs[:2] or tasks[:2]))
            if expected_outputs or tasks
            else "",
            prefix("stages", ", ".join(stages)) if stages else "",
            prefix("scorecard", ", ".join(scorecard_items)) if scorecard_items else "",
            prefix("core_questions", ", ".join(core_questions)) if core_questions else "",
            *selected_interview_values,
        ],
        limit=5,
    )

    return {
        "is_preview": True,
        "notice": summary_preview_copy("notice", language=language),
        "fragments": {
            "brief": {
                "title": summary_preview_copy(
                    "fragments.brief.title",
                    language=language,
                ),
                "summary": one_liner,
                "bullets": _dedupe_preview_items(
                    [
                        role_outcome,
                        prefix("outputs", ", ".join(expected_outputs))
                        if expected_outputs
                        else "",
                        prefix("first_success", ", ".join(first_success_signals[:2]))
                        if first_success_signals
                        else "",
                        prefix("top_tasks", ", ".join(tasks[:3])) if tasks else "",
                        prefix("must_have", ", ".join(skills[:3])) if skills else "",
                        prefix("offer", ", ".join(benefits[:3])) if benefits else "",
                    ],
                    limit=4,
                ),
            },
            "job_ad": {
                "title": summary_preview_copy(
                    "fragments.job_ad.title",
                    language=language,
                ),
                "summary": summary_preview_copy(
                    "fragments.job_ad.summary",
                    language=language,
                ),
                "bullets": job_ad_signals,
            },
            "boolean_search": {
                "title": summary_preview_copy(
                    "fragments.boolean_search.title",
                    language=language,
                ),
                "summary": summary_preview_copy(
                    "fragments.boolean_search.summary",
                    language=language,
                ),
                "bullets": boolean_guidance,
            },
            "interview_hr": {
                "title": summary_preview_copy(
                    "fragments.interview_hr.title",
                    language=language,
                ),
                "summary": summary_preview_copy(
                    "fragments.interview_hr.summary",
                    language=language,
                ),
                "bullets": interview_guidance,
            },
            "interview_fach": {
                "title": summary_preview_copy(
                    "fragments.interview_fach.title",
                    language=language,
                ),
                "summary": summary_preview_copy(
                    "fragments.interview_fach.summary",
                    language=language,
                ),
                "bullets": interview_guidance,
            },
        },
        "context": {
            "role_title": role_title,
            "company": company,
            "location": location,
            "salary": salary_text,
            "benefit_count": len(benefits),
            "skill_count": len(skills) + len(nice_skills),
            "task_count": len(tasks),
            "output_count": len(expected_outputs),
            "non_negotiable_count": len(non_negotiables),
            "salary_caveat": salary_caveat,
        },
    }


def brief_to_markdown(brief: VacancyBrief, *, language: str | None = None) -> str:
    structured_data = brief.structured_data.model_dump(mode="json")
    selected_benefits = [
        str(item).strip()
        for item in structured_data.get("selected_benefits", []) or []
        if str(item).strip()
    ]
    lines = []
    role_title = str(structured_data.get("job_extract", {}).get("job_title", "")).strip()
    lines.append(
        "# "
        + summary_export_copy(
            "brief_title",
            language=language,
            role_title=role_title,
        ).strip()
    )
    lines.append("")
    lines.append(f"**{summary_export_copy('one_liner', language=language)}:** {brief.one_liner}")
    lines.append("")
    lines.append(f"## {summary_export_copy('hiring_context', language=language)}")
    lines.append(brief.hiring_context)
    lines.append("")
    lines.append(f"## {summary_export_copy('role_summary', language=language)}")
    lines.append(brief.role_summary)
    lines.append("")
    lines.append(f"## {summary_export_copy('top_responsibilities', language=language)}")
    lines.extend([f"- {x}" for x in brief.top_responsibilities])
    lines.append("")
    lines.append(f"## {summary_export_copy('must_have', language=language)}")
    lines.extend([f"- {x}" for x in brief.must_have])
    lines.append("")
    lines.append(f"## {summary_export_copy('nice_to_have', language=language)}")
    lines.extend([f"- {x}" for x in brief.nice_to_have])
    lines.append("")
    if selected_benefits:
        lines.append(f"## {summary_export_copy('candidate_value', language=language)}")
        lines.extend([f"- {x}" for x in selected_benefits])
        lines.append("")
    offer_positioning = structured_data.get("offer_positioning")
    if isinstance(offer_positioning, Mapping):
        salary_caveat = str(offer_positioning.get("salary_caveat") or "").strip()
        if salary_caveat:
            lines.append(f"## {summary_export_copy('salary_caveat', language=language)}")
            lines.append(f"- {salary_caveat}")
            lines.append("")
    lines.append(f"## {summary_export_copy('dealbreakers', language=language)}")
    lines.extend([f"- {x}" for x in brief.dealbreakers])
    lines.append("")
    lines.append(f"## {summary_export_copy('interview_plan', language=language)}")
    lines.extend([f"- {x}" for x in brief.interview_plan])
    lines.append("")
    lines.append(f"## {summary_export_copy('evaluation_rubric', language=language)}")
    lines.extend([f"- {x}" for x in brief.evaluation_rubric])
    lines.append("")
    lines.append(f"## {summary_export_copy('risks_open_questions', language=language)}")
    lines.extend([f"- {x}" for x in brief.risks_open_questions])
    lines.append("")
    lines.append(f"## {summary_export_copy('job_ad_draft', language=language)}")
    lines.append(brief.job_ad_draft)
    lines.append("")
    return "\n".join(lines)


def boolean_search_pack_to_markdown(
    pack: BooleanSearchPack,
    *,
    language: str | None = None,
) -> str:
    def _as_bullets(values: list[str], *, code: bool = False) -> list[str]:
        if not values:
            return [f"- {summary_export_copy('empty', language=language)}"]
        if code:
            return [f"- `{value}`" for value in values]
        return [f"- {value}" for value in values]

    lines = [
        f"# {summary_export_copy('boolean_title', language=language)}",
        "",
        f"**{summary_export_copy('role_title', language=language)}:** {pack.role_title}",
        "",
        f"## {summary_export_copy('must_have_terms', language=language)}",
        *_as_bullets(pack.must_have_terms),
        "",
        f"## {summary_export_copy('seniority_terms', language=language)}",
        *_as_bullets(pack.seniority_terms),
        "",
        f"## {summary_export_copy('exclusion_terms', language=language)}",
        *_as_bullets(pack.exclusion_terms),
        "",
        f"## {summary_export_copy('target_locations', language=language)}",
        *_as_bullets(pack.target_locations),
        "",
    ]
    for channel_label, channel in (
        ("Google", pack.google),
        ("LinkedIn", pack.linkedin),
        ("XING", pack.xing),
    ):
        lines.extend(
            [
                f"## {channel_label}",
                "",
                f"### {summary_export_copy('broad', language=language)}",
                *_as_bullets(channel.broad, code=True),
                "",
                f"### {summary_export_copy('focused', language=language)}",
                *_as_bullets(channel.focused, code=True),
                "",
                f"### {summary_export_copy('fallback', language=language)}",
                *_as_bullets(channel.fallback, code=True),
                "",
            ]
        )
    lines.extend(
        [
            f"## {summary_export_copy('channel_limitations', language=language)}",
            *_as_bullets(pack.channel_limitations),
            "",
            f"## {summary_export_copy('usage_notes', language=language)}",
            *_as_bullets(pack.usage_notes),
            "",
        ]
    )
    return "\n".join(lines)
