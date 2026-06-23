"""Pure helpers for Summary export formatting and input fingerprints."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from typing import Any

from constants import APP_NAME, FactKey, SSKey, VACANCY_DRAFT_SCHEMA_VERSION
from schemas import BooleanSearchPack, JobAdExtract, VacancyBrief

VACANCY_DRAFT_SCHEMA_ID = "cs_need_analysis.vacancy_draft"
LIVE_ARTIFACT_PREVIEW_NOTICE = (
    "Live preview from current inputs. Not a final export and no artifact generation."
)


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
) -> str:
    non_sensitive_payload = {
        "job": job.model_dump(mode="json", exclude_none=True),
        "answers": answers,
        "intake_facts": intake_facts or {},
        "intake_fact_resolution": intake_fact_resolution or {},
        "confidence_threshold": confidence_threshold,
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


def _preview_salary_text(job: JobAdExtract) -> str:
    salary_range = getattr(job, "salary_range", None)
    if salary_range is None:
        return ""
    salary_min = _compact_preview_text(getattr(salary_range, "min", None))
    salary_max = _compact_preview_text(getattr(salary_range, "max", None))
    if salary_min and salary_max:
        amount = f"{salary_min} - {salary_max}"
    elif salary_min:
        amount = f"ab {salary_min}"
    elif salary_max:
        amount = f"bis {salary_max}"
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


def build_live_artifact_preview_payload(
    *,
    job: JobAdExtract,
    answers: Mapping[str, Any] | None = None,
    selected_role_tasks: Sequence[str] | None = None,
    selected_skills: Sequence[str] | None = None,
    selected_benefits: Sequence[str] | None = None,
    intake_facts: Mapping[str, Any] | None = None,
    interview_process: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build concise deterministic artifact previews without generating artifacts."""

    _ = answers  # Reserved for future preview-only routing without changing callers.
    facts = intake_facts or {}
    role_title = _compact_preview_text(job.job_title) or "Rolle"
    company = _compact_preview_text(job.company_name)
    location = _compact_preview_text(job.location_city or job.location_country)
    remote_policy = _compact_preview_text(job.remote_policy)
    salary_text = _preview_salary_text(job)
    role_summary = _compact_preview_text(job.role_overview) or role_title
    tasks = _dedupe_preview_items(
        [*(selected_role_tasks or []), *list(job.responsibilities or [])],
        limit=4,
    )
    skills = _dedupe_preview_items(
        [*(selected_skills or []), *list(job.must_have_skills or [])],
        limit=5,
    )
    nice_skills = _dedupe_preview_items(job.nice_to_have_skills or [], limit=3)
    benefits = _dedupe_preview_items(
        [*(selected_benefits or []), *list(job.benefits or [])],
        limit=4,
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

    one_liner = f"{role_title} bei {company}" if company else role_title
    job_ad_signals = _dedupe_preview_items(
        [
            f"Rolle: {role_title}",
            f"Aufgaben: {', '.join(tasks[:2])}" if tasks else "",
            f"Must-have: {', '.join(skills[:3])}" if skills else "",
            f"Candidate Value: {', '.join(benefits[:3])}" if benefits else "",
        ],
        limit=4,
    )
    boolean_terms = _dedupe_preview_items([role_title, *skills[:4]], limit=5)
    boolean_guidance = _dedupe_preview_items(
        [
            f"Suchkern: {' + '.join(boolean_terms[:4])}" if boolean_terms else "",
            f"Standortfilter: {location}" if location else "",
            f"Remote-Signal: {remote_policy}" if remote_policy else "",
            f"Offen klären: {', '.join(open_clarifications)}"
            if open_clarifications
            else "",
            "Skill-Auswahl schärfen, um Trefferrauschen zu senken."
            if not skills
            else "",
        ],
        limit=4,
    )
    interview_guidance = _dedupe_preview_items(
        [
            f"Validieren: {', '.join(skills[:3])}" if skills else "",
            f"Arbeitsprobe/Evidenz: {', '.join(tasks[:2])}" if tasks else "",
            f"Stufen: {', '.join(stages)}" if stages else "",
            f"Scorecard: {', '.join(scorecard_items)}" if scorecard_items else "",
            f"Kernfragen: {', '.join(core_questions)}" if core_questions else "",
            *selected_interview_values,
        ],
        limit=5,
    )

    return {
        "is_preview": True,
        "notice": LIVE_ARTIFACT_PREVIEW_NOTICE,
        "fragments": {
            "brief": {
                "title": "Recruiting Brief",
                "summary": one_liner,
                "bullets": _dedupe_preview_items(
                    [
                        role_summary,
                        f"Top-Aufgaben: {', '.join(tasks[:3])}" if tasks else "",
                        f"Must-have: {', '.join(skills[:3])}" if skills else "",
                        f"Angebot: {', '.join(benefits[:3])}" if benefits else "",
                    ],
                    limit=4,
                ),
            },
            "job_ad": {
                "title": "Job-Ad-Richtung",
                "summary": "Welche Signale später die Anzeige prägen.",
                "bullets": job_ad_signals,
            },
            "boolean_search": {
                "title": "Boolean-Relevanz",
                "summary": "Welche Eingaben den Suchstring scharf oder breit machen.",
                "bullets": boolean_guidance,
            },
            "interview_guide": {
                "title": "Interview-Guide-Folgen",
                "summary": "Welche Antworten später Fragen, Scorecard und Evidenz lenken.",
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
        },
    }


def brief_to_markdown(brief: VacancyBrief) -> str:
    structured_data = brief.structured_data.model_dump(mode="json")
    selected_benefits = [
        str(item).strip()
        for item in structured_data.get("selected_benefits", []) or []
        if str(item).strip()
    ]
    lines = []
    lines.append(
        f"# Recruiting Brief – {structured_data.get('job_extract', {}).get('job_title', '')}".strip()
    )
    lines.append("")
    lines.append(f"**One-liner:** {brief.one_liner}")
    lines.append("")
    lines.append("## Hiring Context")
    lines.append(brief.hiring_context)
    lines.append("")
    lines.append("## Role Summary")
    lines.append(brief.role_summary)
    lines.append("")
    lines.append("## Top Responsibilities")
    lines.extend([f"- {x}" for x in brief.top_responsibilities])
    lines.append("")
    lines.append("## Must-have")
    lines.extend([f"- {x}" for x in brief.must_have])
    lines.append("")
    lines.append("## Nice-to-have")
    lines.extend([f"- {x}" for x in brief.nice_to_have])
    lines.append("")
    if selected_benefits:
        lines.append("## Candidate Value")
        lines.extend([f"- {x}" for x in selected_benefits])
        lines.append("")
    lines.append("## Dealbreakers")
    lines.extend([f"- {x}" for x in brief.dealbreakers])
    lines.append("")
    lines.append("## Interview Plan")
    lines.extend([f"- {x}" for x in brief.interview_plan])
    lines.append("")
    lines.append("## Evaluation Rubric")
    lines.extend([f"- {x}" for x in brief.evaluation_rubric])
    lines.append("")
    lines.append("## Risks / Open Questions")
    lines.extend([f"- {x}" for x in brief.risks_open_questions])
    lines.append("")
    lines.append("## Stellenanzeigenentwurf (DE)")
    lines.append(brief.job_ad_draft)
    lines.append("")
    return "\n".join(lines)


def boolean_search_pack_to_markdown(pack: BooleanSearchPack) -> str:
    def _as_bullets(values: list[str], *, code: bool = False) -> list[str]:
        if not values:
            return ["- —"]
        if code:
            return [f"- `{value}`" for value in values]
        return [f"- {value}" for value in values]

    lines = [
        "# Suchstrings",
        "",
        f"**Role Title:** {pack.role_title}",
        "",
        "## Must-have Terms",
        *_as_bullets(pack.must_have_terms),
        "",
        "## Seniority Terms",
        *_as_bullets(pack.seniority_terms),
        "",
        "## Exclusion Terms",
        *_as_bullets(pack.exclusion_terms),
        "",
        "## Target Locations",
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
                "### Broad",
                *_as_bullets(channel.broad, code=True),
                "",
                "### Focused",
                *_as_bullets(channel.focused, code=True),
                "",
                "### Fallback",
                *_as_bullets(channel.fallback, code=True),
                "",
            ]
        )
    lines.extend(
        [
            "## Channel Limitations",
            *_as_bullets(pack.channel_limitations),
            "",
            "## Usage Notes",
            *_as_bullets(pack.usage_notes),
            "",
        ]
    )
    return "\n".join(lines)
