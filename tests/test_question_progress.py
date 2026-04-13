from __future__ import annotations

from constants import AnswerType
from question_progress import (
    build_step_scope_progress_labels,
    compute_question_progress,
    is_answered,
)
from schemas import Question


def _question(answer_type: AnswerType) -> Question:
    return Question(id=f"q_{answer_type.value}", label="Frage", answer_type=answer_type)


def test_is_answered_text_requires_non_empty_value() -> None:
    question = _question(AnswerType.SHORT_TEXT)

    assert is_answered(question, "Ja", {}) is True
    assert is_answered(question, "   ", {}) is False


def test_is_answered_multi_select_requires_non_empty_list() -> None:
    question = _question(AnswerType.MULTI_SELECT)

    assert is_answered(question, ["A"], {}) is True
    assert is_answered(question, [], {}) is False


def test_is_answered_single_select_rejects_placeholder() -> None:
    question = _question(AnswerType.SINGLE_SELECT)

    assert is_answered(question, "Option A", {}) is True
    assert is_answered(question, "— Bitte wählen —", {}) is False
    assert is_answered(question, None, {}) is False


def test_is_answered_boolean_requires_touch_or_confirm() -> None:
    question = _question(AnswerType.BOOLEAN)

    assert is_answered(question, False, {}) is False
    assert is_answered(question, False, {"touched": True}) is True
    assert is_answered(question, False, {"confirmed": True}) is True


def test_is_answered_number_requires_touch_or_confirm() -> None:
    question = _question(AnswerType.NUMBER)

    assert is_answered(question, 50, {}) is False
    assert is_answered(question, 50, {"touched": True}) is True


def test_is_answered_date_requires_non_empty_string() -> None:
    question = _question(AnswerType.DATE)

    assert is_answered(question, "2026-04-08", {}) is True
    assert is_answered(question, "", {}) is False


def test_compute_question_progress_counts_answered_and_required_open() -> None:
    required_text = Question(
        id="q_req_text",
        label="Pflicht Text",
        answer_type=AnswerType.SHORT_TEXT,
        required=True,
    )
    optional_multi = Question(
        id="q_opt_multi",
        label="Optional Multi",
        answer_type=AnswerType.MULTI_SELECT,
        required=False,
    )
    required_boolean = Question(
        id="q_req_bool",
        label="Pflicht Bool",
        answer_type=AnswerType.BOOLEAN,
        required=True,
    )
    required_number = Question(
        id="q_req_number",
        label="Pflicht Zahl",
        answer_type=AnswerType.NUMBER,
        required=True,
    )

    progress = compute_question_progress(
        [required_text, optional_multi, required_boolean, required_number],
        answers={
            "q_req_text": "Ja",
            "q_opt_multi": ["A"],
            "q_req_bool": False,
            "q_req_number": 3,
        },
        answer_meta={
            "q_req_bool": {"touched": True},
            "q_req_number": {},
        },
    )

    assert progress == {"total": 4, "answered": 3, "required_unanswered": 1}


def test_build_step_scope_progress_labels_marks_scope_difference() -> None:
    labels = build_step_scope_progress_labels(
        visible_answered=1,
        visible_total=1,
        overall_answered=1,
        overall_total=3,
    )

    assert labels["visible_label"] == "Sichtbar im aktuellen Umfang: 1/1"
    assert (
        labels["overall_label"]
        == "Gesamt im Step (inkl. derzeit ausgeblendeter Details): 1/3"
    )
    assert labels["has_different_denominator"] is True
