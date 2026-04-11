from __future__ import annotations

from constants import AnswerType
from question_limits import compute_adaptive_question_limits
from schemas import JobAdExtract, Question, QuestionPlan, QuestionStep


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

    assert limits["skills"] == 2
    assert limits["interview"] == 6


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
