from __future__ import annotations

from constants import AnswerType
from question_progress import is_answered
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
