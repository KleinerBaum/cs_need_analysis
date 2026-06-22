from __future__ import annotations

from collections.abc import Mapping

from constants import (
    AnswerType,
    FactKey,
    QUESTION_LIMIT_SCOPE_META_KEY,
    UI_MODE_QUESTION_LIMIT_RATIOS,
)
from question_limits import (
    build_step_question_scope,
    compute_adaptive_question_limits,
    select_questions_for_adaptive_limit,
    select_questions_for_step_scope,
    select_visible_questions_for_step_scope,
)
from schemas import JobAdExtract, Question, QuestionDependency, QuestionPlan, QuestionStep


def _limit(limits: Mapping[str, object], step_key: str) -> int:
    raw_limit = limits[step_key]
    if isinstance(raw_limit, Mapping):
        return int(raw_limit["limit"])
    return int(raw_limit)


def _build_plan() -> QuestionPlan:
    return QuestionPlan(
        steps=[
            QuestionStep(
                step_key="skills",
                title_de="Skills",
                questions=[
                    Question(
                        id="skills_must",
                        label="Must-have Skills",
                        answer_type=AnswerType.MULTI_SELECT,
                        target_path="must_have_skills",
                    ),
                    Question(
                        id="skills_nice",
                        label="Nice-to-have Skills",
                        answer_type=AnswerType.MULTI_SELECT,
                        target_path="nice_to_have_skills",
                    ),
                    Question(
                        id="skills_soft",
                        label="Soft Skills",
                        answer_type=AnswerType.MULTI_SELECT,
                        target_path="soft_skills",
                    ),
                ],
            ),
            QuestionStep(
                step_key="interview",
                title_de="Interview",
                questions=[
                    Question(
                        id="interview_rounds",
                        label="Anzahl Runden",
                        answer_type=AnswerType.NUMBER,
                        target_path="recruitment_steps",
                    ),
                    Question(
                        id="interview_panel",
                        label="Panel-Beteiligte",
                        answer_type=AnswerType.SHORT_TEXT,
                    ),
                    Question(
                        id="interview_duration",
                        label="Dauer",
                        answer_type=AnswerType.SHORT_TEXT,
                    ),
                    Question(
                        id="interview_assessment",
                        label="Assessments",
                        answer_type=AnswerType.SHORT_TEXT,
                    ),
                    Question(
                        id="interview_feedback",
                        label="Feedback-SLA",
                        answer_type=AnswerType.SHORT_TEXT,
                    ),
                    Question(
                        id="interview_offer",
                        label="Offer-Prozess",
                        answer_type=AnswerType.SHORT_TEXT,
                    ),
                ],
            ),
        ]
    )


def test_adaptive_limits_reduce_steps_with_good_jobspec_coverage() -> None:
    plan = _build_plan()
    job_extract = JobAdExtract(
        must_have_skills=["Python", "SQL"],
        nice_to_have_skills=["Spark"],
        soft_skills=["Kommunikation"],
    )

    limits = compute_adaptive_question_limits(
        plan=plan,
        ui_mode="standard",
        answers={},
        answer_meta={},
        job_extract=job_extract,
    )

    assert _limit(limits, "skills") == 2
    assert _limit(limits, "interview") == 3
    assert limits[QUESTION_LIMIT_SCOPE_META_KEY]["ui_mode"] == "standard"
    assert (
        limits[QUESTION_LIMIT_SCOPE_META_KEY]["question_limit_ratio"]
        == UI_MODE_QUESTION_LIMIT_RATIOS["standard"]
    )


def test_standard_mode_limits_standard_scope_to_half_per_step() -> None:
    plan = QuestionPlan(
        steps=[
            QuestionStep(
                step_key=step_key,
                title_de=step_key,
                questions=[
                    Question(
                        id=f"{step_key}_{index}",
                        label=f"{step_key} {index}",
                        answer_type=AnswerType.SHORT_TEXT,
                    )
                    for index in range(8)
                ],
            )
            for step_key in (
                "company",
                "role_tasks",
                "skills",
                "benefits",
                "interview",
            )
        ]
    )

    limits = compute_adaptive_question_limits(
        plan=plan,
        ui_mode="standard",
        answers={
            question.id: "covered" for step in plan.steps for question in step.questions
        },
        answer_meta={},
        job_extract=None,
    )

    assert {
        step_key: _limit(limits, step_key)
        for step_key in ("company", "role_tasks", "skills", "benefits", "interview")
    } == {
        "company": 4,
        "role_tasks": 4,
        "skills": 4,
        "benefits": 4,
        "interview": 4,
    }


def test_standard_mode_applies_half_ratio_to_covered_standard_questions() -> None:
    plan = QuestionPlan(
        steps=[
            QuestionStep(
                step_key="company",
                title_de="Unternehmen",
                questions=[
                    Question(
                        id=f"company_context_{index}",
                        label=f"Company context {index}",
                        answer_type=AnswerType.SHORT_TEXT,
                        target_path=FactKey.COMPANY_COMPANY_NAME.value,
                    )
                    for index in range(8)
                ],
            )
        ]
    )

    limits = compute_adaptive_question_limits(
        plan=plan,
        ui_mode="standard",
        answers={},
        answer_meta={},
        job_extract=None,
        intake_facts={FactKey.COMPANY_COMPANY_NAME.value: "Example GmbH"},
        intake_fact_evidence={
            FactKey.COMPANY_COMPANY_NAME.value: {"confidence": 0.9}
        },
        confidence_threshold=0.6,
    )

    assert _limit(limits, "company") == 4


def test_adaptive_limits_scale_by_mode_depth() -> None:
    plan = _build_plan()

    quick_limits = compute_adaptive_question_limits(
        plan=plan,
        ui_mode="quick",
        answers={},
        answer_meta={},
        job_extract=None,
    )
    standard_limits = compute_adaptive_question_limits(
        plan=plan,
        ui_mode="standard",
        answers={},
        answer_meta={},
        job_extract=None,
    )
    expert_limits = compute_adaptive_question_limits(
        plan=plan,
        ui_mode="expert",
        answers={},
        answer_meta={},
        job_extract=None,
    )

    assert _limit(quick_limits, "interview") == 2
    assert _limit(standard_limits, "interview") == 3
    assert _limit(expert_limits, "interview") == 6
    assert _limit(quick_limits, "skills") == 1
    assert _limit(standard_limits, "skills") == 2
    assert _limit(expert_limits, "skills") == 3


def test_expert_mode_uses_full_dependency_visible_question_set() -> None:
    plan = QuestionPlan(
        steps=[
            QuestionStep(
                step_key="skills",
                title_de="Skills",
                questions=[
                    Question(
                        id=f"skill_{index}",
                        label=f"Skill {index}",
                        answer_type=AnswerType.SHORT_TEXT,
                    )
                    for index in range(7)
                ],
            )
        ]
    )

    limits = compute_adaptive_question_limits(
        plan=plan,
        ui_mode="expert",
        answers={question.id: "covered" for question in plan.steps[0].questions},
        answer_meta={},
        job_extract=None,
    )

    assert _limit(limits, "skills") == 7


def test_expert_scope_counts_dependency_hidden_without_adaptive_hidden() -> None:
    visible_question = Question(
        id="work_model",
        label="Arbeitsmodell",
        answer_type=AnswerType.SHORT_TEXT,
        priority="core",
    )
    hidden_follow_up = Question(
        id="hybrid_days",
        label="Wie viele Office-Tage?",
        answer_type=AnswerType.NUMBER,
        priority="detail",
        depends_on=[QuestionDependency(question_id="work_model", equals="Hybrid")],
    )
    extra_visible = Question(
        id="office_location",
        label="Office-Standort",
        answer_type=AnswerType.SHORT_TEXT,
        priority="detail",
    )
    plan = QuestionPlan(
        steps=[
            QuestionStep(
                step_key="company",
                title_de="Unternehmen",
                questions=[visible_question, hidden_follow_up, extra_visible],
            )
        ]
    )

    limits = compute_adaptive_question_limits(
        plan=plan,
        ui_mode="expert",
        answers={"work_model": "Remote"},
        answer_meta={},
        job_extract=None,
    )
    scope = build_step_question_scope(
        plan.steps[0].questions,
        step_key="company",
        question_limits=limits,
        answers={"work_model": "Remote"},
        answer_meta={},
        job_extract=None,
    )

    assert _limit(limits, "company") == 2
    assert [question.id for question in scope.visible_questions] == [
        "work_model",
        "office_location",
    ]
    assert scope.dependency_hidden_questions_count == 1
    assert scope.adaptive_hidden_questions_count == 0
    assert scope.hidden_questions_count == 1


def test_adaptive_limits_treat_low_confidence_fact_as_uncovered() -> None:
    plan = _build_plan()
    intake_facts = {
        FactKey.SKILLS_MUST_HAVE_SKILLS.value: ["Python"],
        FactKey.SKILLS_NICE_TO_HAVE_SKILLS.value: ["Spark"],
        FactKey.SKILLS_SOFT_SKILLS.value: ["Kommunikation"],
    }
    intake_fact_evidence = {
        FactKey.SKILLS_MUST_HAVE_SKILLS.value: {"confidence": 0.4},
        FactKey.SKILLS_NICE_TO_HAVE_SKILLS.value: {"confidence": 0.4},
        FactKey.SKILLS_SOFT_SKILLS.value: {"confidence": 0.4},
    }

    limits = compute_adaptive_question_limits(
        plan=plan,
        ui_mode="standard",
        answers={},
        answer_meta={},
        job_extract=JobAdExtract(
            must_have_skills=["Python"],
            nice_to_have_skills=["Spark"],
            soft_skills=["Kommunikation"],
        ),
        intake_facts=intake_facts,
        intake_fact_evidence=intake_fact_evidence,
        confidence_threshold=0.6,
    )

    assert _limit(limits, "skills") == 2


def test_quick_mode_limits_uncovered_core_questions_to_thirty_percent() -> None:
    plan = QuestionPlan(
        steps=[
            QuestionStep(
                step_key="role_tasks",
                title_de="Rolle",
                questions=[
                    Question(
                        id=f"core_{index}",
                        label=f"Core {index}",
                        answer_type=AnswerType.SHORT_TEXT,
                        priority="core",
                    )
                    for index in range(4)
                ]
                + [
                    Question(
                        id="detail_1",
                        label="Detail 1",
                        answer_type=AnswerType.SHORT_TEXT,
                        priority="detail",
                    ),
                    Question(
                        id="detail_2",
                        label="Detail 2",
                        answer_type=AnswerType.SHORT_TEXT,
                        priority="detail",
                    ),
                ],
            )
        ]
    )

    limits = compute_adaptive_question_limits(
        plan=plan,
        ui_mode="quick",
        answers={},
        answer_meta={},
        job_extract=None,
    )

    assert _limit(limits, "role_tasks") == 2


def test_select_questions_for_limit_applies_dependency_visibility_before_slicing() -> None:
    hidden_follow_up = Question(
        id="hybrid_days",
        label="Wie viele Office-Tage?",
        answer_type=AnswerType.NUMBER,
        priority="core",
        depends_on=[
            QuestionDependency(question_id="remote_policy", equals="hybrid")
        ],
    )
    visible_question = Question(
        id="office_location",
        label="Wo ist das Office?",
        answer_type=AnswerType.SHORT_TEXT,
        priority="standard",
    )

    selected = select_questions_for_adaptive_limit(
        [hidden_follow_up, visible_question],
        step_key="company",
        limit=1,
        answers={"remote_policy": "onsite"},
        answer_meta={},
        job_extract=None,
    )

    assert [question.id for question in selected] == ["office_location"]


def test_step_question_scope_exposes_legacy_scope_and_visible_questions() -> None:
    core_question = Question(
        id="q_core",
        label="Core",
        answer_type=AnswerType.SHORT_TEXT,
        required=True,
        priority="core",
    )
    hidden_detail = Question(
        id="q_detail",
        label="Detail",
        answer_type=AnswerType.SHORT_TEXT,
        priority="detail",
        depends_on=[
            QuestionDependency(question_id="q_core", equals="Nein"),
        ],
    )

    scope = build_step_question_scope(
        [core_question, hidden_detail],
        step_key="company",
        question_limits=None,
        answers={"q_core": "Ja"},
        answer_meta={},
        job_extract=None,
    )

    assert [question.id for question in scope.selected_questions] == [
        "q_core",
        "q_detail",
    ]
    assert [question.id for question in scope.visible_questions] == ["q_core"]
    assert scope.hidden_questions_count == 1
    assert scope.dependency_hidden_questions_count == 1
    assert scope.adaptive_hidden_questions_count == 0


def test_step_question_scope_counts_adaptive_hidden_questions() -> None:
    uncovered_core = Question(
        id="uncovered_core",
        label="Hiring goal",
        answer_type=AnswerType.SHORT_TEXT,
        priority="core",
        required=True,
    )
    covered_detail = Question(
        id="covered_detail",
        label="Company name",
        answer_type=AnswerType.SHORT_TEXT,
        priority="detail",
        target_path=FactKey.COMPANY_COMPANY_NAME.value,
    )
    lower_gain_detail = Question(
        id="lower_gain_detail",
        label="Detail",
        answer_type=AnswerType.SHORT_TEXT,
        priority="detail",
    )

    scope = build_step_question_scope(
        [covered_detail, uncovered_core, lower_gain_detail],
        step_key="company",
        question_limits={"company": 1},
        answers={},
        answer_meta={},
        job_extract=None,
        intake_facts={FactKey.COMPANY_COMPANY_NAME.value: "Example GmbH"},
    )

    assert [question.id for question in scope.selected_questions] == ["uncovered_core"]
    assert [question.id for question in scope.visible_questions] == ["uncovered_core"]
    assert scope.dependency_hidden_questions_count == 0
    assert scope.adaptive_hidden_questions_count == 2
    assert scope.hidden_questions_count == 2


def test_step_question_scope_counts_dependency_and_adaptive_hidden_questions() -> None:
    trigger = Question(
        id="work_model",
        label="Arbeitsmodell",
        answer_type=AnswerType.SHORT_TEXT,
        priority="core",
    )
    dependency_hidden = Question(
        id="hybrid_days",
        label="Wie viele Office-Tage?",
        answer_type=AnswerType.NUMBER,
        priority="core",
        depends_on=[QuestionDependency(question_id="work_model", equals="Hybrid")],
    )
    adaptive_selected = Question(
        id="missing_context",
        label="Fehlender Kontext",
        answer_type=AnswerType.SHORT_TEXT,
        priority="standard",
    )

    scope = build_step_question_scope(
        [trigger, dependency_hidden, adaptive_selected],
        step_key="company",
        question_limits={"company": 1},
        answers={"work_model": "Remote"},
        answer_meta={},
        job_extract=None,
    )

    assert [question.id for question in scope.visible_questions] == ["missing_context"]
    assert scope.dependency_hidden_questions_count == 1
    assert scope.adaptive_hidden_questions_count == 1
    assert scope.hidden_questions_count == 2


def test_visible_question_scope_respects_intake_fact_confidence_threshold() -> None:
    remote_policy = Question(
        id="remote_policy",
        label="Remote policy",
        answer_type=AnswerType.SHORT_TEXT,
        target_path=FactKey.COMPANY_REMOTE_POLICY.value,
    )
    hybrid_days = Question(
        id="hybrid_days",
        label="Wie viele Office-Tage?",
        answer_type=AnswerType.NUMBER,
        priority="core",
        depends_on=[
            QuestionDependency(question_id="remote_policy", equals="Hybrid")
        ],
    )

    low_confidence = select_visible_questions_for_step_scope(
        [remote_policy, hybrid_days],
        step_key="company",
        question_limits=None,
        answers={},
        answer_meta={},
        job_extract=None,
        intake_facts={FactKey.COMPANY_REMOTE_POLICY.value: "Hybrid"},
        intake_fact_evidence={
            FactKey.COMPANY_REMOTE_POLICY.value: {"confidence": 0.4}
        },
        confidence_threshold=0.6,
    )
    high_confidence = select_visible_questions_for_step_scope(
        [remote_policy, hybrid_days],
        step_key="company",
        question_limits=None,
        answers={},
        answer_meta={},
        job_extract=None,
        intake_facts={FactKey.COMPANY_REMOTE_POLICY.value: "Hybrid"},
        intake_fact_evidence={
            FactKey.COMPANY_REMOTE_POLICY.value: {"confidence": 0.8}
        },
        confidence_threshold=0.6,
    )

    assert [question.id for question in low_confidence] == ["remote_policy"]
    assert [question.id for question in high_confidence] == [
        "remote_policy",
        "hybrid_days",
    ]


def test_select_questions_for_limit_prioritizes_uncovered_core_question() -> None:
    covered_detail = Question(
        id="detail_context",
        label="Detail",
        answer_type=AnswerType.SHORT_TEXT,
        priority="detail",
        target_path=FactKey.COMPANY_COMPANY_NAME.value,
    )
    uncovered_core = Question(
        id="hiring_goal",
        label="Hiring goal",
        answer_type=AnswerType.SHORT_TEXT,
        priority="core",
    )

    selected = select_questions_for_adaptive_limit(
        [covered_detail, uncovered_core],
        step_key="company",
        limit=1,
        answers={},
        answer_meta={},
        job_extract=None,
        intake_facts={FactKey.COMPANY_COMPANY_NAME.value: "Example GmbH"},
    )

    assert [question.id for question in selected] == ["hiring_goal"]


def test_select_questions_for_step_scope_uses_adaptive_limit_mapping() -> None:
    covered_detail = Question(
        id="covered_detail",
        label="Already covered",
        answer_type=AnswerType.SHORT_TEXT,
        priority="detail",
        target_path=FactKey.COMPANY_COMPANY_NAME.value,
    )
    uncovered_core = Question(
        id="uncovered_core",
        label="Hiring goal",
        answer_type=AnswerType.SHORT_TEXT,
        priority="core",
    )

    selected = select_questions_for_step_scope(
        [covered_detail, uncovered_core],
        step_key="company",
        question_limits={"company": 1},
        answers={},
        answer_meta={},
        job_extract=None,
        intake_facts={FactKey.COMPANY_COMPANY_NAME.value: "Example GmbH"},
    )

    assert [question.id for question in selected] == ["uncovered_core"]


def test_select_questions_for_limit_ranks_information_gain_metadata() -> None:
    low_gain = Question(
        id="low_gain",
        label="Low gain",
        answer_type=AnswerType.SHORT_TEXT,
        priority="standard",
        info_gain_score=0.1,
        acquisition_cost="high",
    )
    high_gain = Question(
        id="high_gain",
        label="High gain",
        answer_type=AnswerType.SHORT_TEXT,
        priority="standard",
        impact_targets=["brief", "salary", "interview"],
        info_gain_score=0.9,
        acquisition_cost="low",
    )

    selected = select_questions_for_adaptive_limit(
        [low_gain, high_gain],
        step_key="company",
        limit=1,
        answers={},
        answer_meta={},
        job_extract=None,
    )

    assert [question.id for question in selected] == ["high_gain"]


def test_quick_mode_excludes_detail_questions_even_with_high_information_gain() -> None:
    plan = QuestionPlan(
        steps=[
            QuestionStep(
                step_key="company",
                title_de="Unternehmen",
                questions=[
                    Question(
                        id=f"high_gain_{index}",
                        label=f"High gain {index}",
                        answer_type=AnswerType.SHORT_TEXT,
                        priority="detail",
                        impact_targets=["brief", "salary", "skills", "export"],
                        info_gain_score=0.95,
                        acquisition_cost="low",
                    )
                    for index in range(3)
                ],
            )
        ]
    )

    limits = compute_adaptive_question_limits(
        plan=plan,
        ui_mode="quick",
        answers={},
        answer_meta={},
        job_extract=None,
    )

    assert _limit(limits, "company") == 0


def test_quick_mode_excludes_detail_follow_up_questions() -> None:
    plan = QuestionPlan(
        steps=[
            QuestionStep(
                step_key="interview",
                title_de="Interview",
                questions=[
                    *[
                        Question(
                            id=f"probe_{index}",
                            label=f"Probe {index}",
                            answer_type=AnswerType.SHORT_TEXT,
                            priority="detail",
                            follow_up_prompts=["Bitte konkretisieren"],
                        )
                        for index in range(4)
                    ],
                    *[
                        Question(
                            id=f"detail_{index}",
                            label=f"Detail {index}",
                            answer_type=AnswerType.SHORT_TEXT,
                            priority="detail",
                        )
                        for index in range(2)
                    ],
                ],
            )
        ]
    )

    limits = compute_adaptive_question_limits(
        plan=plan,
        ui_mode="quick",
        answers={},
        answer_meta={},
        job_extract=None,
    )

    assert _limit(limits, "interview") == 0
