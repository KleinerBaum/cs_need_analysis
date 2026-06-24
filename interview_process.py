"""Helpers for interview process state, display rows, and export payloads."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from typing import Any

from constants import AnswerType, FactKey, STEP_KEY_INTERVIEW
from schemas import JobAdExtract, Question, QuestionPlan, QuestionStep


INTERVIEW_INTERNAL_FLOW_DEFAULT: dict[str, Any] = {
    "contacts": [],
    "info_loop_items": [],
    "earliest_start_date": None,
    "latest_start_date": None,
    "selected_value_ids": [],
}


def normalize_interview_internal_flow(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        return dict(INTERVIEW_INTERNAL_FLOW_DEFAULT)

    contacts = raw.get("contacts", [])
    info_loop_items = raw.get("info_loop_items", [])
    selected_value_ids = raw.get("selected_value_ids", [])
    return {
        "contacts": contacts if isinstance(contacts, list) else [],
        "info_loop_items": [
            str(item).strip()
            for item in info_loop_items
            if isinstance(item, str) and str(item).strip()
        ]
        if isinstance(info_loop_items, list)
        else [],
        "earliest_start_date": raw.get("earliest_start_date"),
        "latest_start_date": raw.get("latest_start_date"),
        "selected_value_ids": [
            str(item).strip()
            for item in selected_value_ids
            if isinstance(item, str) and str(item).strip()
        ]
        if isinstance(selected_value_ids, list)
        else [],
    }


def _compact(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _row_id(*parts: str) -> str:
    source = "||".join(_compact(part).casefold() for part in parts)
    return hashlib.sha1(source.encode("utf-8")).hexdigest()[:12]


def _add_row(
    rows: list[dict[str, str]],
    *,
    area: str,
    field: str,
    value: Any,
    source: str,
    status: str = "Vollständig",
) -> None:
    cleaned = _compact(value)
    if not cleaned:
        return
    rows.append(
        {
            "id": _row_id(area, field, cleaned, source),
            "Bereich": area,
            "Feld": field,
            "Wert": cleaned,
            "Quelle": source,
            "Status": status,
        }
    )


def _format_question_answer(question: Question, value: Any) -> str:
    if value is None:
        return ""
    if question.answer_type == AnswerType.BOOLEAN:
        return "Ja" if bool(value) else "Nein"
    if isinstance(value, list):
        return ", ".join(_compact(item) for item in value if _compact(item))
    if isinstance(value, dict):
        parts = [
            f"{_compact(key)}: {_compact(item)}"
            for key, item in value.items()
            if _compact(item)
        ]
        return "; ".join(parts)
    return _compact(value)


def _interview_step_from_plan(plan: QuestionPlan | None) -> QuestionStep | None:
    if plan is None:
        return None
    return next(
        (step for step in plan.steps if step.step_key == STEP_KEY_INTERVIEW),
        None,
    )


def _is_process_question(question: Question) -> bool:
    haystack = " ".join(
        (
            question.id or "",
            question.label or "",
            question.help or "",
            question.group_key or "",
            question.target_path or "",
        )
    ).casefold()
    return any(
        keyword in haystack
        for keyword in (
            "stage",
            "prozess",
            "schritt",
            "ablauf",
            "interview",
            "timeline",
            "feedback",
        )
    )


def build_candidate_stage_values(
    *,
    job: JobAdExtract,
    answers: dict[str, Any],
    plan: QuestionPlan | None,
) -> list[str]:
    stages = [
        _compact(
            f"{step.name}{': ' + step.details if _compact(step.details) else ''}"
        )
        for step in job.recruitment_steps
        if _compact(step.name)
    ]
    if stages:
        return stages

    interview_step = _interview_step_from_plan(plan)
    if interview_step is None:
        return []
    fallback_values: list[str] = []
    for question in interview_step.questions:
        if not _is_process_question(question):
            continue
        formatted = _format_question_answer(question, answers.get(question.id))
        if formatted:
            fallback_values.append(formatted)
    return fallback_values


def build_interview_value_rows(
    *,
    job: JobAdExtract,
    answers: dict[str, Any],
    plan: QuestionPlan | None,
    internal_flow: dict[str, Any],
) -> list[dict[str, str]]:
    normalized_flow = normalize_interview_internal_flow(internal_flow)
    rows: list[dict[str, str]] = []

    candidate_stages = build_candidate_stage_values(
        job=job,
        answers=answers,
        plan=plan,
    )
    for idx, stage in enumerate(candidate_stages, start=1):
        _add_row(
            rows,
            area="Interview",
            field=f"Interviewphase {idx}",
            value=stage,
            source="Jobspec" if job.recruitment_steps else "Intake-Antwort",
        )

    interview_step = _interview_step_from_plan(plan)
    if interview_step is not None:
        for question in interview_step.questions:
            formatted = _format_question_answer(question, answers.get(question.id))
            if formatted:
                _add_row(
                    rows,
                    area="Interview",
                    field=question.label,
                    value=formatted,
                    source="Intake-Antwort",
                )

    info_loop_items = normalized_flow["info_loop_items"]
    if info_loop_items:
        _add_row(
            rows,
            area="Kandidatenkommunikation",
            field="Recruiting-Infoloop",
            value=", ".join(info_loop_items),
            source="Interview-Step",
        )

    earliest_start = _compact(normalized_flow.get("earliest_start_date"))
    latest_start = _compact(normalized_flow.get("latest_start_date"))
    if earliest_start:
        _add_row(
            rows,
            area="Zeitplan",
            field="Frühestmöglicher Startzeitpunkt",
            value=earliest_start,
            source="Interview-Step",
        )
    if latest_start:
        _add_row(
            rows,
            area="Zeitplan",
            field="Spätester Startzeitpunkt",
            value=latest_start,
            source="Interview-Step",
        )

    for contact in normalized_flow["contacts"]:
        if not isinstance(contact, dict):
            continue
        role = _compact(contact.get("role"))
        name = _compact(contact.get("name"))
        if name:
            _add_row(
                rows,
                area="Interne Rollen",
                field=f"{role} Ansprechpartner" if role else "Ansprechpartner",
                value=name,
                source="Interview-Step",
            )
        phone = _compact(contact.get("phone"))
        if phone:
            _add_row(
                rows,
                area="Interne Rollen",
                field=f"{role} Telefonnummer" if role else "Telefonnummer",
                value=phone,
                source="Interview-Step",
            )
        email = _compact(contact.get("email"))
        if email:
            _add_row(
                rows,
                area="Interne Rollen",
                field=f"{role} E-Mail-Adresse" if role else "E-Mail-Adresse",
                value=email,
                source="Interview-Step",
            )
        if bool(contact.get("participates_in_interview")):
            _add_row(
                rows,
                area="Interne Rollen",
                field=f"{role} Interviewteilnahme" if role else "Interviewteilnahme",
                value="Ja",
                source="Interview-Step",
            )
        interview_datetime = _compact(contact.get("interview_datetime"))
        if interview_datetime:
            _add_row(
                rows,
                area="Zeitplan",
                field=f"{role} Interviewtag" if role else "Interviewtag",
                value=interview_datetime,
                source="Interview-Step",
            )

    seen: set[str] = set()
    deduped: list[dict[str, str]] = []
    for row in rows:
        key = "|".join(
            row[column].casefold()
            for column in ("Bereich", "Feld", "Wert", "Quelle")
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(row)
    return deduped


def default_selected_interview_value_ids(rows: list[dict[str, str]]) -> list[str]:
    return [row["id"] for row in rows if _compact(row.get("Wert"))]


def _object_list(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _text_list(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value] if _compact(value) else []
    if not isinstance(value, list):
        return []
    return [_compact(item) for item in value if _compact(item)]


def _safe_interview_export_row(row: Mapping[str, str]) -> bool:
    area = _compact(row.get("Bereich") or row.get("area")).casefold()
    field = _compact(row.get("Feld") or row.get("field")).casefold()
    if area in {"interne rollen", "internal roles"}:
        return False
    blocked_terms = (
        "e-mail",
        "email",
        "telefon",
        "phone",
        "ansprechpartner",
        "contact",
        "kontakt",
        "name",
    )
    if any(term in field for term in blocked_terms):
        return False
    return area in {
        "interview",
        "zeitplan",
        "timing",
        "kandidatenkommunikation",
        "candidate communication",
    }


def _safe_internal_flow_payload(normalized_flow: Mapping[str, Any]) -> dict[str, Any]:
    contact_roles: list[dict[str, Any]] = []
    for contact in normalized_flow.get("contacts", []):
        if not isinstance(contact, dict):
            continue
        role = _compact(contact.get("role"))
        if not role:
            continue
        contact_roles.append(
            {
                "role": role,
                "participates_in_interview": bool(
                    contact.get("participates_in_interview")
                ),
            }
        )
    return {
        "contacts": contact_roles,
        "info_loop_items": list(normalized_flow.get("info_loop_items", [])),
        "earliest_start_date": normalized_flow.get("earliest_start_date"),
        "latest_start_date": normalized_flow.get("latest_start_date"),
        "selected_value_ids": list(normalized_flow.get("selected_value_ids", [])),
    }


def _stage_context_from_facts(
    *,
    job: JobAdExtract,
    intake_facts: Mapping[str, Any],
) -> list[dict[str, Any]]:
    fact_steps = _object_list(intake_facts.get(FactKey.INTERVIEW_RECRUITMENT_STEPS.value))
    stages: list[dict[str, Any]] = []
    if fact_steps:
        for item in fact_steps:
            name = _compact(item.get("name"))
            if not name:
                continue
            stages.append(
                {
                    "stage": name,
                    "intent": _compact(item.get("goal") or item.get("details")),
                    "duration_minutes": item.get("duration_minutes"),
                }
            )
    else:
        for step in job.recruitment_steps:
            name = _compact(step.name)
            if not name:
                continue
            stages.append(
                {
                    "stage": name,
                    "intent": _compact(step.details),
                    "duration_minutes": None,
                }
            )
    return stages


def _decision_owner_context(intake_facts: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in _object_list(intake_facts.get(FactKey.INTERVIEW_STAGE_OWNERS.value)):
        stage = _compact(item.get("stage"))
        decision_role = _compact(item.get("decision_role"))
        if stage or decision_role:
            rows.append(
                {
                    "stage": stage,
                    "responsibility": decision_role,
                }
            )
    return rows


def _candidate_communication_context(
    *,
    intake_facts: Mapping[str, Any],
    normalized_flow: Mapping[str, Any],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in _object_list(
        intake_facts.get(FactKey.INTERVIEW_COMMUNICATION_SLA.value)
    ):
        event = _compact(item.get("event"))
        if not event:
            continue
        rows.append(
            {
                "event": event,
                "days": item.get("days"),
                "stage_hint": _compact(item.get("stage_hint")),
            }
        )
    for label in normalized_flow.get("info_loop_items", []):
        text = _compact(label)
        if text:
            rows.append({"event": text, "days": None, "stage_hint": ""})
    return rows


def build_interview_hiring_plan_context(
    *,
    job: JobAdExtract,
    answers: dict[str, Any],
    plan: QuestionPlan | None,
    internal_flow: dict[str, Any],
    intake_facts: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build sanitized hiring-plan context for generated outputs."""

    del answers
    del plan
    facts = intake_facts or {}
    normalized_flow = normalize_interview_internal_flow(internal_flow)
    scorecard = facts.get(FactKey.INTERVIEW_SCORECARD_TEMPLATE.value)
    scorecard_payload = scorecard if isinstance(scorecard, dict) else {}
    fairness_notes = _compact(
        facts.get(FactKey.INTERVIEW_COMPLIANCE_NOTES.value)
        or scorecard_payload.get("notes")
    )
    context = {
        "stage_intents": _stage_context_from_facts(job=job, intake_facts=facts),
        "evaluator_responsibilities": _decision_owner_context(facts),
        "assessment_evidence": _object_list(
            facts.get(FactKey.INTERVIEW_ASSESSMENT_EVIDENCE.value)
        ),
        "scorecard_template": scorecard_payload,
        "core_questions": _text_list(facts.get(FactKey.INTERVIEW_CORE_QUESTIONS.value)),
        "candidate_communication": _candidate_communication_context(
            intake_facts=facts,
            normalized_flow=normalized_flow,
        ),
        "fairness_notes": fairness_notes,
        "separation_note": (
            "Candidate communication and scheduling stay separate from evaluation logic."
        ),
        "output_consequences": [
            "HR-Sheet: consistent stage intent, knockout checks, candidate updates.",
            "Fachbereich-Sheet: observable evidence, scorecard criteria, debrief anchors.",
            "Fair interview evidence: same core questions and documented success signals.",
        ],
    }
    return {key: value for key, value in context.items() if value not in ("", [], {})}


def build_interview_export_payload(
    *,
    job: JobAdExtract,
    answers: dict[str, Any],
    plan: QuestionPlan | None,
    internal_flow: dict[str, Any],
    intake_facts: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    normalized_flow = normalize_interview_internal_flow(internal_flow)
    rows = build_interview_value_rows(
        job=job,
        answers=answers,
        plan=plan,
        internal_flow=normalized_flow,
    )
    selected_ids = normalized_flow["selected_value_ids"] or default_selected_interview_value_ids(
        rows
    )
    selected_rows = [
        row
        for row in rows
        if row["id"] in set(selected_ids) and _safe_interview_export_row(row)
    ]
    scheduling = {
        "candidate_updates": list(normalized_flow["info_loop_items"]),
        "earliest_start_date": normalized_flow.get("earliest_start_date"),
        "latest_start_date": normalized_flow.get("latest_start_date"),
    }
    scheduling = {key: value for key, value in scheduling.items() if value}
    evaluation_plan = build_interview_hiring_plan_context(
        job=job,
        answers=answers,
        plan=plan,
        internal_flow=normalized_flow,
        intake_facts=intake_facts,
    )
    payload: dict[str, Any] = {
        "candidate_stages": build_candidate_stage_values(
            job=job,
            answers=answers,
            plan=plan,
        ),
        "selected_values": selected_rows,
        "internal_flow": {
            **_safe_internal_flow_payload(normalized_flow),
            "selected_value_ids": [row["id"] for row in selected_rows],
        },
        "scheduling": scheduling,
        "evaluation_plan": evaluation_plan,
        "artifact_impact": ["brief", "interview_hr", "interview_fach"],
    }
    return payload
