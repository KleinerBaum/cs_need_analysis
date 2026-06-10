from __future__ import annotations

from constants import AnswerType, FactKey
from question_plan_compiler import compile_question_plan
from schemas import (
    JobAdExtract,
    Question,
    QuestionPlan,
    QuestionStep,
    RelevanceLevel,
)
from occupation_context import classify_occupation_context


def _question(question_id: str, label: str) -> Question:
    return Question(
        id=question_id,
        label=label,
        answer_type=AnswerType.SHORT_TEXT,
        priority="standard",
        group_key="base",
    )


def test_compiler_injects_selected_digital_product_packs() -> None:
    profile = classify_occupation_context(
        job=JobAdExtract(job_title="Software Developer", remote_policy="Remote")
    )
    base_plan = QuestionPlan(
        steps=[
            QuestionStep(
                step_key="role_tasks",
                title_de="Rolle",
                questions=[_question("base_role", "Was sind die Hauptaufgaben?")],
            )
        ]
    )

    compiled = compile_question_plan(base_plan=base_plan, profile=profile)
    question_ids = [q.id for step in compiled.plan.steps for q in step.questions]

    assert "base_role" in question_ids
    assert "ctx_digital_ownership" in question_ids
    assert "ctx_tech_stack_must" in question_ids
    assert "ctx_remote_geography" in question_ids
    fact_by_question_id = {
        q.id: q.fact_key for step in compiled.plan.steps for q in step.questions
    }
    assert fact_by_question_id["ctx_digital_ownership"] == (
        FactKey.ROLE_RESPONSIBILITIES.value
    )
    assert fact_by_question_id["ctx_tech_stack_must"] == FactKey.ROLE_TECH_STACK.value
    assert fact_by_question_id["ctx_remote_geography"] == (
        FactKey.COMPANY_REMOTE_POLICY.value
    )
    assert "family.digital_product" in compiled.provenance.selected_pack_keys
    assert compiled.provenance.base_question_count == 1
    assert compiled.provenance.compiled_question_count > 1


def test_compiler_suppresses_irrelevant_driving_question_for_digital_role() -> None:
    profile = classify_occupation_context(
        job=JobAdExtract(job_title="Software Developer", remote_policy="Remote")
    )
    base_plan = QuestionPlan(
        steps=[
            QuestionStep(
                step_key="skills",
                title_de="Skills",
                questions=[
                    _question("driving_license", "Welche Fuehrerscheinklasse ist noetig?")
                ],
            )
        ]
    )

    compiled = compile_question_plan(base_plan=base_plan, profile=profile)
    question_ids = [q.id for step in compiled.plan.steps for q in step.questions]

    assert "driving_license" not in question_ids
    assert compiled.provenance.suppressed_question_ids == ["driving_license"]


def test_compiler_demotes_irrelevant_question_when_confidence_is_low() -> None:
    profile = classify_occupation_context(job=JobAdExtract(job_title="Software"))
    profile.confidence = 0.5
    profile.driving_relevance = RelevanceLevel.IRRELEVANT
    base_plan = QuestionPlan(
        steps=[
            QuestionStep(
                step_key="skills",
                title_de="Skills",
                questions=[
                    _question("driving_license", "Welche Fuehrerscheinklasse ist noetig?")
                ],
            )
        ]
    )

    compiled = compile_question_plan(base_plan=base_plan, profile=profile)
    questions = [q for step in compiled.plan.steps for q in step.questions]
    demoted = next(q for q in questions if q.id == "driving_license")

    assert demoted.priority == "detail"
    assert compiled.provenance.demoted_question_ids == ["driving_license"]
