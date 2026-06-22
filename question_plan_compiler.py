"""Compile deterministic occupation question packs into the existing QuestionPlan."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any, Mapping

from constants import (
    AnswerType,
    QUESTION_IMPACT_TARGET_EXPORT,
    QUESTION_IMPACT_TARGET_INTERVIEW,
    QUESTION_IMPACT_TARGET_SKILLS,
    STEP_KEY_BENEFITS,
    STEP_KEY_COMPANY,
    STEP_KEY_INTERVIEW,
    STEP_KEY_ROLE_TASKS,
    STEP_KEY_SKILLS,
)
from llm_client import normalize_question_plan
from occupation_context import profile_fingerprint, resolve_question_module_keys
from question_packs import get_question_pack
from schemas import (
    OccupationContextProfile,
    OccupationFamily,
    OccupationQuestionConcept,
    OccupationQuestionContext,
    Question,
    QuestionFlowProvenance,
    QuestionOption,
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


def _safe_hash(value: str, length: int = 12) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:length]


def _json_safe_question_payload(question: Question | Mapping[str, Any]) -> dict[str, Any]:
    if isinstance(question, Mapping):
        payload = dict(question)
    else:
        payload = question.model_dump(mode="python", warnings=False)
    answer_type = payload.get("answer_type")
    if hasattr(answer_type, "value"):
        payload["answer_type"] = answer_type.value
    return payload


def _clone_question(question: Question) -> Question:
    return Question.model_validate(_json_safe_question_payload(question))


def _clone_step(step: QuestionStep) -> QuestionStep:
    payload = step.model_dump(mode="python", warnings=False)
    raw_questions = payload.get("questions")
    if isinstance(raw_questions, list):
        payload["questions"] = [
            _json_safe_question_payload(question)
            if isinstance(question, Question) or isinstance(question, Mapping)
            else question
            for question in raw_questions
        ]
    return QuestionStep.model_validate(payload)


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


def _context_pack_keys(context: OccupationQuestionContext | None) -> list[str]:
    if context is None:
        return []
    keys = [f"skill_group.{group}" for group in context.skill_groups]
    if context.regulated_profession is True:
        keys.append("facet.regulated_profession")
    return list(dict.fromkeys(keys))


def _reuse_rank(concept: OccupationQuestionConcept) -> int:
    level = (concept.reuse_level or "").casefold()
    if "occupation" in level:
        return 0
    if "sector" in level and "cross" not in level:
        return 1
    if "cross" in level:
        return 2
    if "transversal" in level:
        return 4
    return 3


def _concept_bucket_rank(bucket: str) -> int:
    return {
        "essential_skill": 0,
        "essential_knowledge": 1,
        "optional_skill": 2,
        "optional_knowledge": 3,
    }.get(bucket, 9)


def _concept_candidates(
    context: OccupationQuestionContext,
) -> list[tuple[str, OccupationQuestionConcept]]:
    candidates: list[tuple[str, OccupationQuestionConcept]] = [
        *[("essential_skill", concept) for concept in context.essential_skills],
        *[("essential_knowledge", concept) for concept in context.essential_knowledge],
        *[("optional_skill", concept) for concept in context.optional_skills],
        *[("optional_knowledge", concept) for concept in context.optional_knowledge],
    ]
    output: list[tuple[str, OccupationQuestionConcept]] = []
    seen: set[str] = set()
    for bucket, concept in candidates:
        key = concept.uri.strip() or f"label:{concept.label.casefold().strip()}"
        if not key or key in seen:
            continue
        output.append((bucket, concept))
        seen.add(key)
    return sorted(
        output,
        key=lambda item: (
            _concept_bucket_rank(item[0]),
            _reuse_rank(item[1]),
            item[1].label.casefold(),
            item[1].uri,
        ),
    )


def _concept_question_options(bucket: str) -> list[QuestionOption]:
    if bucket in {"essential_skill", "essential_knowledge"}:
        if bucket == "essential_knowledge":
            return [
                QuestionOption(value="none", label="Keine Vorkenntnisse"),
                QuestionOption(value="basic", label="Grundverständnis"),
                QuestionOption(value="practical", label="Praxiserfahrung"),
                QuestionOption(value="solid", label="Sicheres Anwenden"),
                QuestionOption(value="expert", label="Experten-/Anleitungsniveau"),
            ]
        return [
            QuestionOption(value="not_relevant", label="Nicht relevant"),
            QuestionOption(value="nice_to_have", label="Nice-to-have"),
            QuestionOption(value="required_basic", label="Zwingend: Grundkenntnisse"),
            QuestionOption(value="required_solid", label="Zwingend: sicher anwendbar"),
            QuestionOption(value="required_expert", label="Zwingend: Expertenniveau"),
        ]
    return [
        QuestionOption(value="no", label="Nein"),
        QuestionOption(value="rare", label="Selten"),
        QuestionOption(value="regular", label="Regelmäßig"),
        QuestionOption(
            value="critical_six_months",
            label="Kritisch für Erfolg in den ersten 6 Monaten",
        ),
    ]


def _concept_question_label(bucket: str, label: str) -> str:
    if bucket == "essential_knowledge" or bucket == "optional_knowledge":
        return f"Welches Niveau in \"{label}\" wird erwartet?"
    if bucket == "optional_skill":
        return f"Kommt \"{label}\" in dieser konkreten Stelle vor?"
    return f"Wie wichtig ist \"{label}\" für diese Position?"


def _build_esco_concept_questions(
    *,
    context: OccupationQuestionContext | None,
    seen_ids: set[str],
) -> tuple[list[Question], dict[str, list[str]]]:
    if context is None:
        return [], {}
    questions: list[Question] = []
    source_uris_by_question_id: dict[str, list[str]] = {}
    for bucket, concept in _concept_candidates(context):
        label = concept.label.strip()
        if not label:
            continue
        question_id = f"ctx_esco_{bucket}_{_safe_hash(concept.uri or label)}"
        if question_id in seen_ids:
            continue
        group_key = concept.skill_group or f"esco_{bucket}"
        question = Question(
            id=question_id,
            label=_concept_question_label(bucket, label),
            help="Aus ESCO-Kontext abgeleitet; bitte für diese konkrete Vakanz bestätigen.",
            answer_type=AnswerType.SINGLE_SELECT,
            required=False,
            options=_concept_question_options(bucket),
            target_path=f"esco_questions.{question_id}",
            priority="core" if bucket.startswith("essential") else "detail",
            group_key=group_key,
            rationale="ESCO essential/optional concepts require vacancy-specific confirmation.",
            impact_targets=[
                QUESTION_IMPACT_TARGET_SKILLS,
                QUESTION_IMPACT_TARGET_INTERVIEW,
                QUESTION_IMPACT_TARGET_EXPORT,
            ],
            acquisition_cost="low",
            info_gain_score=0.74 if bucket.startswith("essential") else 0.62,
        )
        questions.append(question)
        seen_ids.add(question_id)
        if concept.uri:
            source_uris_by_question_id[question_id] = [concept.uri]
    return questions, source_uris_by_question_id


def compile_question_plan(
    *,
    base_plan: QuestionPlan,
    profile: OccupationContextProfile,
    question_context: OccupationQuestionContext | None = None,
    ui_mode: str = "standard",
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
    resolved_pack_keys = list(dict.fromkeys([*profile.pack_keys, *_context_pack_keys(question_context)]))
    for pack_key in resolved_pack_keys:
        pack = get_question_pack(pack_key)
        is_context_pack = pack_key not in profile.pack_keys
        if pack is None or (not is_context_pack and not pack.applies_to(profile)):
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

    esco_questions, source_uris_by_question_id = _build_esco_concept_questions(
        context=question_context,
        seen_ids=seen_ids,
    )
    if esco_questions:
        step_by_key.setdefault(
            STEP_KEY_SKILLS,
            QuestionStep(
                step_key=STEP_KEY_SKILLS,
                title_de=STEP_KEY_SKILLS.replace("_", " ").title(),
            ),
        )
        step_by_key[STEP_KEY_SKILLS].questions.extend(esco_questions)
        injected_question_ids.extend(question.id for question in esco_questions)

    compiled_steps = sorted(step_by_key.values(), key=lambda step: _step_index(step.step_key))
    for step in compiled_steps:
        step.questions = _sort_questions(step.questions)

    compiled_plan = normalize_question_plan(
        QuestionPlan(
            schema_version=base_plan.schema_version,
            language=base_plan.language,
            steps=compiled_steps,
        ),
        preserve_noncanonical_group_ids=set(injected_question_ids),
    )
    resolved_module_keys, skipped_module_reasons = resolve_question_module_keys(
        question_context
    )
    provenance = QuestionFlowProvenance(
        profile_fingerprint=profile_fingerprint(profile),
        base_question_count=sum(len(step.questions) for step in base_plan.steps),
        compiled_question_count=sum(len(step.questions) for step in compiled_plan.steps),
        selected_pack_keys=selected_pack_keys,
        resolved_module_keys=resolved_module_keys,
        skipped_module_reasons=skipped_module_reasons,
        source_uris_by_question_id=source_uris_by_question_id,
        suppressed_question_ids=suppressed_question_ids,
        demoted_question_ids=demoted_question_ids,
        injected_question_ids=injected_question_ids,
    )
    return CompiledQuestionPlan(plan=compiled_plan, provenance=provenance)


def compile_question_plan_from_payloads(
    *,
    base_plan_payload: dict[str, Any],
    profile_payload: dict[str, Any],
    question_context_payload: dict[str, Any] | None = None,
    ui_mode: str = "standard",
) -> CompiledQuestionPlan:
    return compile_question_plan(
        base_plan=QuestionPlan.model_validate(base_plan_payload),
        profile=OccupationContextProfile.model_validate(profile_payload),
        question_context=(
            OccupationQuestionContext.model_validate(question_context_payload)
            if question_context_payload
            else None
        ),
        ui_mode=ui_mode,
    )
