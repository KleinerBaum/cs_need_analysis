from __future__ import annotations

from constants import AnswerType
from question_dependencies import should_show_question
from schemas import Question


def _question(
    question_id: str,
    *,
    label: str,
    help_text: str | None = None,
    target_path: str | None = None,
) -> Question:
    return Question(
        id=question_id,
        label=label,
        help=help_text,
        answer_type=AnswerType.SHORT_TEXT,
        target_path=target_path,
    )


def test_leadership_followup_hidden_until_leadership_yes() -> None:
    team_size = _question(
        "team_size_detail",
        label="Wie groß ist das Team?",
        help_text="Bitte Teamgröße und direkte Reports angeben.",
    )

    assert (
        should_show_question(
            team_size,
            answers={"leadership_required": "Nein"},
            answer_meta={},
            step_key="team",
        )
        is False
    )
    assert (
        should_show_question(
            team_size,
            answers={"leadership_required": "Ja"},
            answer_meta={},
            step_key="team",
        )
        is True
    )


def test_remote_followup_depends_on_remote_or_hybrid_selection() -> None:
    onsite_details = _question(
        "remote_policy_detail",
        label="Wie viele On-site Tage pro Woche?",
        help_text="Remote policy und Onsite-Erwartungen beschreiben.",
    )

    assert (
        should_show_question(
            onsite_details,
            answers={"place_of_work": "vor Ort"},
            answer_meta={},
            step_key="company",
        )
        is False
    )
    assert (
        should_show_question(
            onsite_details,
            answers={"place_of_work": "Hybrid"},
            answer_meta={},
            step_key="company",
        )
        is True
    )


def test_travel_and_oncall_followups_require_yes_like_answers() -> None:
    travel_frequency = _question(
        "travel_frequency",
        label="Wie hoch ist die Reisefrequenz und welche Regionen?",
    )
    oncall_rotation = _question(
        "oncall_rotation",
        label="Wie oft ist die On-Call Rotation und gibt es eine Zulage?",
    )

    assert (
        should_show_question(
            travel_frequency,
            answers={"travel_required": "Nein"},
            answer_meta={},
            step_key="role_tasks",
        )
        is False
    )
    assert (
        should_show_question(
            travel_frequency,
            answers={"travel_required": "Ja"},
            answer_meta={},
            step_key="role_tasks",
        )
        is True
    )

    assert (
        should_show_question(
            oncall_rotation,
            answers={"on_call": "Nein"},
            answer_meta={},
            step_key="benefits",
        )
        is False
    )
    assert (
        should_show_question(
            oncall_rotation,
            answers={"on_call": True},
            answer_meta={},
            step_key="benefits",
        )
        is True
    )


def test_salary_detail_reveals_when_compensation_answer_is_present() -> None:
    salary_flex = _question(
        "salary_flex_detail",
        label="Wie flexibel ist die Gehaltsspanne inklusive Bonus?",
        target_path="compensation.bonus_notes",
    )

    assert (
        should_show_question(
            salary_flex,
            answers={"salary_range": ""},
            answer_meta={},
            step_key="benefits",
        )
        is False
    )
    assert (
        should_show_question(
            salary_flex,
            answers={"salary_range": "80k-95k EUR"},
            answer_meta={},
            step_key="benefits",
        )
        is True
    )


def test_non_dependent_question_is_always_visible() -> None:
    base_question = _question("role_summary", label="Was ist das Ziel der Rolle?")

    assert (
        should_show_question(
            base_question,
            answers={},
            answer_meta={},
            step_key="role_tasks",
        )
        is True
    )
