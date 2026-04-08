from constants import AnswerType
from llm_client import normalize_question_plan
from schemas import Question, QuestionPlan, QuestionStep


def test_normalize_category_questions_to_select_types() -> None:
    plan = QuestionPlan(
        steps=[
            QuestionStep(
                step_key="skills",
                title_de="Skills",
                questions=[
                    Question(
                        id="hard_skills",
                        label="Hard Skills",
                        answer_type=AnswerType.SHORT_TEXT,
                        required=True,
                    ),
                    Question(
                        id="seniority_level",
                        label="Seniority",
                        answer_type=AnswerType.LONG_TEXT,
                    ),
                    Question(
                        id="work_mode",
                        label="Arbeitsmodell",
                        answer_type=AnswerType.SHORT_TEXT,
                        default=["Hybrid"],
                    ),
                ],
            )
        ]
    )

    normalized = normalize_question_plan(plan)
    questions = normalized.steps[0].questions

    assert questions[0].answer_type is AnswerType.MULTI_SELECT
    assert "Sonstiges" in (questions[0].options or [])
    assert questions[0].default == []

    assert questions[1].answer_type is AnswerType.SINGLE_SELECT
    assert "Sonstiges" in (questions[1].options or [])

    assert questions[2].answer_type is AnswerType.SINGLE_SELECT
    assert questions[2].default == "Hybrid"
