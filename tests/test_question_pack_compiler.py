from __future__ import annotations

from constants import (
    AnswerType,
    ESCO_QUESTION_SKILL_GROUP_DIGITAL_DATA_AI,
    ESCO_QUESTION_SKILL_GROUP_REGULATION_SAFETY,
    ESCO_QUESTION_SKILL_GROUP_TOOLS_METHODS,
    FactKey,
    QUESTION_IMPACT_TARGET_BRIEF,
    QUESTION_IMPACT_TARGET_EXPORT,
    QUESTION_IMPACT_TARGET_INTERVIEW,
    QUESTION_IMPACT_TARGET_SALARY,
    QUESTION_IMPACT_TARGET_SKILLS,
    QUESTION_IMPACT_TARGETS,
    STEP_KEY_COMPANY,
    STEP_KEY_SKILLS,
)
from question_limits import (
    _question_is_adaptive_essential,
    compute_adaptive_question_limits,
    select_questions_for_step_scope_from_plan,
)
from question_plan_compiler import compile_question_plan
from question_packs import QUESTION_PACK_REGISTRY
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


_EXPECTED_COMPANY_METADATA = {
    "ctx_company_employer_pitch": (
        [QUESTION_IMPACT_TARGET_BRIEF, QUESTION_IMPACT_TARGET_EXPORT],
        "medium",
        0.86,
    ),
    "ctx_company_business_unit": (
        [
            QUESTION_IMPACT_TARGET_BRIEF,
            QUESTION_IMPACT_TARGET_SALARY,
            QUESTION_IMPACT_TARGET_EXPORT,
        ],
        "low",
        0.78,
    ),
    "ctx_company_hiring_reason": (
        [QUESTION_IMPACT_TARGET_BRIEF, QUESTION_IMPACT_TARGET_INTERVIEW],
        "low",
        None,
    ),
    "ctx_company_growth_context": (
        [QUESTION_IMPACT_TARGET_BRIEF, QUESTION_IMPACT_TARGET_SALARY],
        "medium",
        None,
    ),
    "ctx_company_role_business_impact": (
        [QUESTION_IMPACT_TARGET_BRIEF, QUESTION_IMPACT_TARGET_INTERVIEW],
        "medium",
        None,
    ),
    "ctx_company_role_positioning": (
        [QUESTION_IMPACT_TARGET_BRIEF, QUESTION_IMPACT_TARGET_EXPORT],
        "low",
        None,
    ),
    "ctx_team_name": (
        [
            QUESTION_IMPACT_TARGET_BRIEF,
            QUESTION_IMPACT_TARGET_INTERVIEW,
            QUESTION_IMPACT_TARGET_EXPORT,
        ],
        "low",
        0.76,
    ),
    "ctx_team_leadership_scope": (
        [
            QUESTION_IMPACT_TARGET_BRIEF,
            QUESTION_IMPACT_TARGET_SALARY,
            QUESTION_IMPACT_TARGET_INTERVIEW,
            QUESTION_IMPACT_TARGET_EXPORT,
        ],
        "low",
        0.88,
    ),
    "ctx_team_size_direct": (
        [QUESTION_IMPACT_TARGET_BRIEF, QUESTION_IMPACT_TARGET_SALARY],
        "low",
        None,
    ),
    "ctx_team_stakeholders_primary": (
        [
            QUESTION_IMPACT_TARGET_BRIEF,
            QUESTION_IMPACT_TARGET_INTERVIEW,
            QUESTION_IMPACT_TARGET_EXPORT,
        ],
        "low",
        0.80,
    ),
    "ctx_company_work_arrangement": (
        [
            QUESTION_IMPACT_TARGET_BRIEF,
            QUESTION_IMPACT_TARGET_SALARY,
            QUESTION_IMPACT_TARGET_EXPORT,
        ],
        "low",
        0.90,
    ),
    "ctx_company_language_internal": (
        [QUESTION_IMPACT_TARGET_SKILLS, QUESTION_IMPACT_TARGET_INTERVIEW],
        "low",
        None,
    ),
    "ctx_company_language_external": (
        [QUESTION_IMPACT_TARGET_SKILLS, QUESTION_IMPACT_TARGET_EXPORT],
        "low",
        None,
    ),
    "ctx_company_non_negotiables": (
        [
            QUESTION_IMPACT_TARGET_BRIEF,
            QUESTION_IMPACT_TARGET_SALARY,
            QUESTION_IMPACT_TARGET_SKILLS,
            QUESTION_IMPACT_TARGET_EXPORT,
        ],
        "medium",
        0.88,
    ),
    "ctx_team_success_context_90d": (
        [QUESTION_IMPACT_TARGET_BRIEF, QUESTION_IMPACT_TARGET_INTERVIEW],
        "medium",
        None,
    ),
    "ctx_remote_geography": (
        [
            QUESTION_IMPACT_TARGET_BRIEF,
            QUESTION_IMPACT_TARGET_SALARY,
            QUESTION_IMPACT_TARGET_EXPORT,
        ],
        "low",
        0.86,
    ),
    "ctx_hiring_growth_context": (
        [QUESTION_IMPACT_TARGET_BRIEF, QUESTION_IMPACT_TARGET_SALARY],
        "medium",
        0.66,
    ),
    "ctx_confidential_external_narrative": (
        [QUESTION_IMPACT_TARGET_BRIEF, QUESTION_IMPACT_TARGET_EXPORT],
        "medium",
        0.82,
    ),
    "ctx_low_maturity_role_assumptions": (
        [
            QUESTION_IMPACT_TARGET_BRIEF,
            QUESTION_IMPACT_TARGET_INTERVIEW,
            QUESTION_IMPACT_TARGET_EXPORT,
        ],
        "medium",
        0.84,
    ),
    "ctx_leadership_reporting_detail": (
        [
            QUESTION_IMPACT_TARGET_BRIEF,
            QUESTION_IMPACT_TARGET_SALARY,
            QUESTION_IMPACT_TARGET_INTERVIEW,
            QUESTION_IMPACT_TARGET_EXPORT,
        ],
        "medium",
        0.88,
    ),
    "ctx_company_allowed_regions_timezones": (
        [
            QUESTION_IMPACT_TARGET_BRIEF,
            QUESTION_IMPACT_TARGET_SALARY,
            QUESTION_IMPACT_TARGET_EXPORT,
        ],
        "low",
        0.86,
    ),
}


def _question(question_id: str, label: str) -> Question:
    return Question(
        id=question_id,
        label=label,
        answer_type=AnswerType.SHORT_TEXT,
        priority="standard",
        group_key="base",
    )


def _company_registry_questions() -> dict[str, Question]:
    questions: dict[str, Question] = {}
    for pack in QUESTION_PACK_REGISTRY.values():
        for entry in pack.entries:
            if entry.step_key != STEP_KEY_COMPANY:
                continue
            assert entry.question.id not in questions
            questions[entry.question.id] = entry.question
    return questions


def test_company_pack_entries_have_adaptive_metadata() -> None:
    questions = _company_registry_questions()
    canonical_targets = set(QUESTION_IMPACT_TARGETS)

    assert set(questions) == set(_EXPECTED_COMPANY_METADATA)
    for question_id, (
        expected_targets,
        expected_cost,
        expected_score,
    ) in _EXPECTED_COMPANY_METADATA.items():
        question = questions[question_id]

        assert question.rationale and question.rationale.strip()
        assert question.impact_targets == expected_targets
        assert set(question.impact_targets) <= canonical_targets
        assert question.acquisition_cost == expected_cost
        assert question.info_gain_score == expected_score

        if question.priority == "core":
            assert question.info_gain_score is not None
        else:
            assert question.priority == "standard"
            if question.info_gain_score is None:
                assert not _question_is_adaptive_essential(question)


def test_registry_pack_entries_have_priority_metadata_contract() -> None:
    canonical_targets = set(QUESTION_IMPACT_TARGETS)

    for pack in QUESTION_PACK_REGISTRY.values():
        for entry in pack.entries:
            question = entry.question

            assert question.group_key
            assert question.rationale and question.rationale.strip()
            assert question.impact_targets
            assert set(question.impact_targets) <= canonical_targets
            assert question.acquisition_cost in {"low", "medium", "high"}

            if question.priority == "core":
                assert question.info_gain_score is not None
                assert 0.0 <= question.info_gain_score <= 1.0
                assert _question_is_adaptive_essential(question)


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
    questions = {q.id: q for step in compiled.plan.steps for q in step.questions}
    question_ids = list(questions)
    esco_question_ids = [
        question_id
        for question_id in question_ids
        if question_id.startswith("ctx_esco_essential_skill_")
    ]

    assert len(question_ids) == len(set(question_ids))
    assert "ctx_sg_digital_data_ai" in question_ids
    assert "ctx_regulated_requirements" in question_ids
    assert len(esco_question_ids) == 1
    assert questions["base_skill"].group_key == "application_context"
    assert questions["ctx_sg_digital_data_ai"].group_key == "digital_data_ai"
    assert questions["ctx_regulated_requirements"].group_key == "licenses"
    assert questions[esco_question_ids[0]].group_key == "digital_data_ai"
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


def test_context_heavy_standard_scope_prioritizes_company_metadata() -> None:
    answers = {
        FactKey.INTAKE_HIRING_REASON.value: "replacement",
        FactKey.INTAKE_URGENCY.value: "high",
        FactKey.INTAKE_HIRING_VOLUME.value: 3,
        FactKey.INTAKE_SEARCH_CONFIDENTIALITY.value: "high",
        FactKey.INTAKE_ROLE_DEFINITION_MATURITY.value: "low",
        FactKey.TEAM_LEADERSHIP_SCOPE.value: "disziplinarische_fuehrung",
        FactKey.COMPANY_WORK_ARRANGEMENT.value: "remote_cross_border",
    }
    intake_facts = {
        FactKey.TEAM_LEADERSHIP_SCOPE.value: "disziplinarische_fuehrung",
        FactKey.COMPANY_WORK_ARRANGEMENT.value: "remote_cross_border",
        FactKey.COMPANY_REMOTE_POLICY.value: "remote_cross_border",
    }
    profile = classify_occupation_context(
        job=JobAdExtract(
            job_title="Operations Lead",
            contract_type="freelance",
            remote_policy="remote_cross_border",
        ),
        answers=answers,
    )
    compiled = compile_question_plan(base_plan=QuestionPlan(steps=[]), profile=profile)

    limits = compute_adaptive_question_limits(
        plan=compiled.plan,
        ui_mode="standard",
        answers=answers,
        answer_meta={},
        job_extract=None,
        intake_facts=intake_facts,
    )
    selected = select_questions_for_step_scope_from_plan(
        compiled.plan,
        STEP_KEY_COMPANY,
        question_limits=limits,
        answers=answers,
        answer_meta={},
        job_extract=None,
        intake_facts=intake_facts,
    )
    selected_ids = [question.id for question in selected]

    assert "ctx_leadership_reporting_detail" in selected_ids
    assert "ctx_low_maturity_role_assumptions" in selected_ids
    assert "ctx_confidential_external_narrative" in selected_ids
    assert "ctx_company_role_business_impact" not in selected_ids


def test_skills_heavy_standard_scope_prioritizes_skill_metadata_and_expert_depth() -> None:
    profile = classify_occupation_context(
        job=JobAdExtract(
            job_title="Senior Data Engineer",
            remote_policy="Remote",
            tech_stack=["Python", "SQL"],
        )
    )
    context = OccupationQuestionContext(
        occupation_uri="uri:occupation:data-engineer",
        preferred_label="Data engineer",
        regulated_profession=True,
        skill_groups=[
            ESCO_QUESTION_SKILL_GROUP_DIGITAL_DATA_AI,
            ESCO_QUESTION_SKILL_GROUP_TOOLS_METHODS,
            ESCO_QUESTION_SKILL_GROUP_REGULATION_SAFETY,
        ],
        essential_skills=[
            OccupationQuestionConcept(
                uri="uri:skill:python",
                label="Python",
                concept_type="skill",
                relation="essential",
                skill_group=ESCO_QUESTION_SKILL_GROUP_DIGITAL_DATA_AI,
                reuse_level="occupation-specific",
            )
        ],
    )
    compiled = compile_question_plan(
        base_plan=QuestionPlan(steps=[]),
        profile=profile,
        question_context=context,
        ui_mode="standard",
    )

    standard_limits = compute_adaptive_question_limits(
        plan=compiled.plan,
        ui_mode="standard",
        answers={},
        answer_meta={},
        job_extract=None,
    )
    standard_selected = select_questions_for_step_scope_from_plan(
        compiled.plan,
        STEP_KEY_SKILLS,
        question_limits=standard_limits,
        answers={},
        answer_meta={},
        job_extract=None,
    )
    standard_ids = [question.id for question in standard_selected]

    assert "ctx_tech_stack_must" in standard_ids
    assert "ctx_regulated_requirements" in standard_ids
    assert "ctx_sg_digital_data_ai" in standard_ids
    assert "ctx_skills_free_text_reason" not in standard_ids
    assert standard_ids.index("ctx_regulated_requirements") < standard_ids.index(
        "ctx_sg_tools_methods"
    )

    expert_limits = compute_adaptive_question_limits(
        plan=compiled.plan,
        ui_mode="expert",
        answers={},
        answer_meta={},
        job_extract=None,
    )
    expert_selected = select_questions_for_step_scope_from_plan(
        compiled.plan,
        STEP_KEY_SKILLS,
        question_limits=expert_limits,
        answers={},
        answer_meta={},
        job_extract=None,
    )
    skills_step = next(
        step for step in compiled.plan.steps if step.step_key == STEP_KEY_SKILLS
    )

    assert len(expert_selected) == len(skills_step.questions)
    assert "ctx_skills_free_text_reason" in [
        question.id for question in expert_selected
    ]
