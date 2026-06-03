"""Compile deterministic occupation question packs into the existing QuestionPlan."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from constants import (
    STEP_KEY_BENEFITS,
    STEP_KEY_COMPANY,
    STEP_KEY_INTERVIEW,
    STEP_KEY_ROLE_TASKS,
    STEP_KEY_SKILLS,
)
from llm_client import normalize_question_plan
from occupation_context import profile_fingerprint
from question_packs import get_question_pack
from schemas import (
    OccupationContextProfile,
    OccupationFamily,
    Question,
    QuestionFlowProvenance,
    QuestionPlan,
    QuestionStep,
    RelevanceLevel,
    WorkArrangement,
)


@dataclass(frozen=True)
class CompiledQuestionPlan:
    plan: QuestionPlan
    provenance: QuestionFlowProvenance


_VISIBLE_INTAKE_STEP_ORDER: tuple[str, ...] = (
    STEP_KEY_COMPANY,
    STEP_KEY_ROLE_TASKS,
    STEP_KEY_SKILLS,
    STEP_KEY_BENEFITS,
    STEP_KEY_INTERVIEW,
)


def _question_blob(question: Question) -> str:
    return " ".join(
        str(part or "").casefold()
        for part in (
            question.id,
            question.label,
            question.help,
            question.rationale,
            question.target_path,
            question.group_key,
        )
    )


def _contains_any(blob: str, terms: tuple[str, ...]) -> bool:
    return any(term in blob for term in terms)


def _clone_question(question: Question) -> Question:
    return Question.model_validate(question.model_dump(mode="json"))


def _clone_step(step: QuestionStep) -> QuestionStep:
    return QuestionStep.model_validate(step.model_dump(mode="json"))


def _should_suppress_or_demote(
    question: Question,
    profile: OccupationContextProfile,
) -> tuple[str | None, str]:
    blob = _question_blob(question)
    if (
        profile.driving_relevance == RelevanceLevel.IRRELEVANT
        and _contains_any(
            blob,
            (
                "fuehrerschein",
                "führerschein",
                "driving",
                "driver",
                "fahrzeug",
                "dienstwagen",
            ),
        )
    ):
        return "suppress", "driving_irrelevant"

    remote_only_terms = (
        "global remote",
        "remote-only",
        "remote only",
        "weltweit",
        "work from anywhere",
        "zeitzone",
        "timezone",
    )
    if (
        profile.work_arrangement == WorkArrangement.ONSITE_REQUIRED
        and _contains_any(blob, remote_only_terms)
    ):
        return "suppress", "onsite_required"

    if profile.occupation_family in {
        OccupationFamily.CLINICAL_PHYSICIAN,
        OccupationFamily.NURSING_CARE,
        OccupationFamily.FIELD_SERVICE,
        OccupationFamily.TRANSPORT_LOGISTICS,
    } and _contains_any(blob, remote_only_terms):
        return "suppress", "family_onsite_bias"

    if profile.occupation_family == OccupationFamily.FIELD_SALES and _contains_any(
        blob,
        ("remote-only", "remote only", "asynchron", "async collaboration"),
    ):
        return "demote", "field_sales_remote_detail"

    return None, ""


def _sort_questions(questions: list[Question]) -> list[Question]:
    priority_rank = {"core": 0, "standard": 1, "detail": 2}
    return sorted(
        questions,
        key=lambda question: (
            priority_rank.get(question.priority or "", 1),
            question.group_key or "",
            question.id,
        ),
    )


def _step_index(step_key: str) -> tuple[int, str]:
    try:
        return (_VISIBLE_INTAKE_STEP_ORDER.index(step_key), step_key)
    except ValueError:
        return (len(_VISIBLE_INTAKE_STEP_ORDER), step_key)


def compile_question_plan(
    *,
    base_plan: QuestionPlan,
    profile: OccupationContextProfile,
) -> CompiledQuestionPlan:
    """Return a compiled QuestionPlan while preserving the existing render contract."""

    step_by_key = {step.step_key: _clone_step(step) for step in base_plan.steps}
    for step_key in _VISIBLE_INTAKE_STEP_ORDER:
        step_by_key.setdefault(
            step_key,
            QuestionStep(step_key=step_key, title_de=step_key.replace("_", " ").title()),
        )

    suppressed_question_ids: list[str] = []
    demoted_question_ids: list[str] = []
    injected_question_ids: list[str] = []
    high_confidence = profile.confidence >= 0.65

    for step in step_by_key.values():
        retained_questions: list[Question] = []
        for original_question in step.questions:
            question = _clone_question(original_question)
            action, _reason = _should_suppress_or_demote(question, profile)
            if action == "suppress" and high_confidence:
                suppressed_question_ids.append(question.id)
                continue
            if action in {"suppress", "demote"}:
                question.priority = "detail"
                demoted_question_ids.append(question.id)
            retained_questions.append(question)
        step.questions = retained_questions

    seen_ids = {
        question.id for step in step_by_key.values() for question in step.questions
    }
    selected_pack_keys: list[str] = []
    for pack_key in profile.pack_keys:
        pack = get_question_pack(pack_key)
        if pack is None or not pack.applies_to(profile):
            continue
        selected_pack_keys.append(pack_key)
        for entry in pack.entries:
            question = _clone_question(entry.question)
            if question.id in seen_ids:
                continue
            step_by_key.setdefault(
                entry.step_key,
                QuestionStep(
                    step_key=entry.step_key,
                    title_de=entry.step_key.replace("_", " ").title(),
                ),
            )
            step_by_key[entry.step_key].questions.append(question)
            seen_ids.add(question.id)
            injected_question_ids.append(question.id)

    compiled_steps = sorted(step_by_key.values(), key=lambda step: _step_index(step.step_key))
    for step in compiled_steps:
        step.questions = _sort_questions(step.questions)

    compiled_plan = normalize_question_plan(
        QuestionPlan(
            schema_version=base_plan.schema_version,
            language=base_plan.language,
            steps=compiled_steps,
        )
    )
    provenance = QuestionFlowProvenance(
        profile_fingerprint=profile_fingerprint(profile),
        base_question_count=sum(len(step.questions) for step in base_plan.steps),
        compiled_question_count=sum(len(step.questions) for step in compiled_plan.steps),
        selected_pack_keys=selected_pack_keys,
        suppressed_question_ids=suppressed_question_ids,
        demoted_question_ids=demoted_question_ids,
        injected_question_ids=injected_question_ids,
    )
    return CompiledQuestionPlan(plan=compiled_plan, provenance=provenance)


def compile_question_plan_from_payloads(
    *,
    base_plan_payload: dict[str, Any],
    profile_payload: dict[str, Any],
) -> CompiledQuestionPlan:
    return compile_question_plan(
        base_plan=QuestionPlan.model_validate(base_plan_payload),
        profile=OccupationContextProfile.model_validate(profile_payload),
    )
