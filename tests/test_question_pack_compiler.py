from __future__ import annotations

from constants import AnswerType, FactKey
from question_plan_compiler import compile_question_plan
from schemas import (
    JobAdExtract,
    OccupationQuestionConcept,
    OccupationQuestionContext,
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
                    _question("driving_license", "Welche Führerscheinklasse ist nötig?")
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
                    _question("driving_license", "Welche Führerscheinklasse ist nötig?")
                ],
            )
        ]
    )

    compiled = compile_question_plan(base_plan=base_plan, profile=profile)
    questions = [q for step in compiled.plan.steps for q in step.questions]
    demoted = next(q for q in questions if q.id == "driving_license")

    assert demoted.priority == "detail"
    assert compiled.provenance.demoted_question_ids == ["driving_license"]


def test_compiler_injects_skill_group_pack_and_esco_concept_questions() -> None:
    profile = classify_occupation_context(job=JobAdExtract(job_title="Data Engineer"))
    context = OccupationQuestionContext(
        occupation_uri="uri:occupation:data-engineer",
        preferred_label="Data engineer",
        isco_code="2511",
        nace_codes=["J62"],
        regulated_profession=True,
        skill_groups=["digital_data_ai"],
        essential_skills=[
            OccupationQuestionConcept(
                uri="uri:skill:python",
                label="Python",
                concept_type="skill",
                relation="essential",
                skill_group="digital_data_ai",
                reuse_level="occupation-specific",
            )
        ],
    )
    base_plan = QuestionPlan(
        steps=[
            QuestionStep(
                step_key="skills",
                title_de="Skills",
                questions=[_question("base_skill", "Welche Skills fehlen?")],
            )
        ]
    )

    compiled = compile_question_plan(
        base_plan=base_plan,
        profile=profile,
        question_context=context,
        ui_mode="standard",
    )
    question_ids = [q.id for step in compiled.plan.steps for q in step.questions]
    esco_question_ids = [
        question_id
        for question_id in question_ids
        if question_id.startswith("ctx_esco_essential_skill_")
    ]

    assert "ctx_sg_digital_data_ai" in question_ids
    assert "ctx_regulated_requirements" in question_ids
    assert len(esco_question_ids) == 1
    assert "SKILL_GROUP:digital_data_ai" in compiled.provenance.resolved_module_keys
    assert "ISCO4:2511" in compiled.provenance.resolved_module_keys
    assert compiled.provenance.source_uris_by_question_id[esco_question_ids[0]] == [
        "uri:skill:python"
    ]


def test_compiler_caps_esco_concept_questions_by_ui_mode() -> None:
    profile = classify_occupation_context(job=JobAdExtract(job_title="Data Engineer"))
    context = OccupationQuestionContext(
        occupation_uri="uri:occupation:data-engineer",
        preferred_label="Data engineer",
        essential_skills=[
            OccupationQuestionConcept(
                uri=f"uri:skill:{index}",
                label=f"Skill {index}",
                concept_type="skill",
                relation="essential",
            )
            for index in range(5)
        ],
    )

    compiled = compile_question_plan(
        base_plan=QuestionPlan(steps=[]),
        profile=profile,
        question_context=context,
        ui_mode="quick",
    )
    esco_questions = [
        q
        for step in compiled.plan.steps
        for q in step.questions
        if q.id.startswith("ctx_esco_")
    ]

    assert len(esco_questions) == 3


def test_compiler_injects_routing_facet_questions() -> None:
    profile = classify_occupation_context(
        job=JobAdExtract(job_title="Operations Lead", contract_type="freelance"),
        answers={
            FactKey.INTAKE_HIRING_REASON.value: "replacement",
            FactKey.INTAKE_URGENCY.value: "high",
            FactKey.INTAKE_HIRING_VOLUME.value: 2,
            FactKey.INTAKE_SEARCH_CONFIDENTIALITY.value: "high",
            FactKey.INTAKE_ROLE_DEFINITION_MATURITY.value: "low",
            FactKey.TEAM_LEADERSHIP_SCOPE.value: "fachliche_fuehrung",
            FactKey.COMPANY_WORK_ARRANGEMENT.value: "remote_cross_border",
        },
    )

    compiled = compile_question_plan(base_plan=QuestionPlan(steps=[]), profile=profile)
    questions = {q.id: q for step in compiled.plan.steps for q in step.questions}

    assert "ctx_hiring_replacement_gap" in questions
    assert "ctx_interview_urgency_tradeoffs" in questions
    assert "ctx_confidential_external_narrative" in questions
    assert "ctx_multi_hire_calibration" in questions
    assert "ctx_low_maturity_role_assumptions" in questions
    assert "ctx_leadership_reporting_detail" in questions
    assert "ctx_contract_constraints" in questions
    assert "ctx_company_allowed_regions_timezones" in questions
    assert questions["ctx_company_allowed_regions_timezones"].fact_key == (
        FactKey.COMPANY_ALLOWED_REGIONS_TIMEZONES.value
    )
    assert "facet.international_context" in compiled.provenance.selected_pack_keys
