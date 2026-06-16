from __future__ import annotations

from constants import AnswerType, FactKey
from question_limits import (
    compute_adaptive_question_limits,
    select_questions_for_adaptive_limit,
)
from schemas import JobAdExtract, Question, QuestionDependency, QuestionPlan, QuestionStep


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

    assert limits["skills"] == 3
    assert limits["interview"] == 6


def test_standard_mode_applies_step_specific_question_floors() -> None:
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
        answers={question.id: "covered" for step in plan.steps for question in step.questions},
        answer_meta={},
        job_extract=None,
    )

    assert limits == {
        "company": 5,
        "role_tasks": 6,
        "skills": 5,
        "benefits": 4,
        "interview": 5,
    }


def test_adaptive_limits_scale_by_mode_depth() -> None:
    plan = _build_plan()

    quick_limits = compute_adaptive_question_limits(
        plan=plan,
        ui_mode="quick",
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

    assert quick_limits["interview"] < expert_limits["interview"]
    assert quick_limits["skills"] < expert_limits["skills"]


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

    assert limits["skills"] == 7


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

    assert limits["skills"] == 3


def test_adaptive_limits_keep_uncovered_core_questions_in_scope() -> None:
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

    assert limits["role_tasks"] == 4


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


def test_high_information_gain_questions_are_adaptive_essential() -> None:
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

    assert limits["company"] == 3


def test_follow_up_prompt_questions_are_treated_as_adaptive_essential() -> None:
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

    assert limits["interview"] == 4
