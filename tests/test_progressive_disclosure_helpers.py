from __future__ import annotations

from constants import AnswerType
from question_progress import build_answered_lookup, compute_question_progress
from schemas import Question, QuestionDependency
from ui_components import (
    _collect_incomplete_group_titles,
    _split_core_and_detail_questions,
)


def test_split_core_and_detail_questions_falls_back_for_legacy_metadata() -> None:
    questions = [
        Question(
            id="q_required_1",
            label="Pflicht 1",
            answer_type=AnswerType.SHORT_TEXT,
            required=True,
        ),
        Question(
            id="q_optional_1",
            label="Optional 1",
            answer_type=AnswerType.SHORT_TEXT,
            required=False,
        ),
        Question(
            id="q_required_2",
            label="Pflicht 2",
            answer_type=AnswerType.SHORT_TEXT,
            required=True,
        ),
    ]

    core, detail = _split_core_and_detail_questions(questions)

    assert [question.id for question in core] == [
        "q_required_1",
        "q_required_2",
        "q_optional_1",
    ]
    assert detail == []


def test_group_incomplete_titles_uses_answered_lookup() -> None:
    core_question = Question(
        id="core_1",
        label="Minimalprofil",
        answer_type=AnswerType.SHORT_TEXT,
        required=True,
        priority="core",
    )
    detail_open = Question(
        id="detail_1",
        label="Detail optional",
        answer_type=AnswerType.SHORT_TEXT,
        required=False,
        priority="detail",
    )
    detail_required = Question(
        id="detail_2",
        label="Detail Pflicht",
        answer_type=AnswerType.SHORT_TEXT,
        required=True,
        priority="detail",
    )
    answers = {"core_1": "Ja", "detail_1": "Done", "detail_2": ""}
    answered_lookup = build_answered_lookup(
        [core_question, detail_open, detail_required],
        answers,
        answer_meta={},
    )

    incomplete = _collect_incomplete_group_titles(
        [("Details", [detail_open, detail_required])],
        answers,
        answer_meta={},
        answered_lookup=answered_lookup,
    )

    assert incomplete == ["Details"]
    detail_progress = compute_question_progress(
        [detail_open, detail_required],
        answers,
        answer_meta={},
        answered_lookup=answered_lookup,
    )
    assert detail_progress["required_unanswered"] == 1


def test_declared_dependency_is_answered_handles_placeholder_like_values() -> None:
    dependent_question = Question(
        id="detail_dep",
        label="Follow-up",
        answer_type=AnswerType.SHORT_TEXT,
        depends_on=[QuestionDependency(question_id="work_mode", is_answered=True)],
    )

    from question_dependencies import should_show_question

    assert (
        should_show_question(
            dependent_question,
            answers={"work_mode": "— Bitte wählen —"},
            answer_meta={},
            step_key="company",
        )
        is False
    )
    assert (
        should_show_question(
            dependent_question,
            answers={"work_mode": "Hybrid"},
            answer_meta={},
            step_key="company",
        )
        is True
    )
