from __future__ import annotations

from constants import AnswerType, FactKey
from question_dependencies import should_show_question
from schemas import Question, QuestionDependency


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


def test_remote_followup_can_use_canonical_intake_facts() -> None:
    onsite_details = _question(
        "remote_policy_detail",
        label="Wie viele On-site Tage pro Woche?",
        help_text="Remote policy und Onsite-Erwartungen beschreiben.",
    )

    assert (
        should_show_question(
            onsite_details,
            answers={},
            answer_meta={},
            step_key="company",
            intake_facts={FactKey.COMPANY_REMOTE_POLICY.value: "Hybrid"},
        )
        is True
    )
    assert (
        should_show_question(
            onsite_details,
            answers={},
            answer_meta={},
            step_key="company",
            intake_facts={FactKey.COMPANY_PLACE_OF_WORK.value: "vor Ort"},
        )
        is False
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


def test_travel_and_oncall_followups_can_use_canonical_intake_facts() -> None:
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
            answers={},
            answer_meta={},
            step_key="role_tasks",
            intake_facts={FactKey.ROLE_TRAVEL_REQUIRED.value: True},
        )
        is True
    )
    assert (
        should_show_question(
            travel_frequency,
            answers={},
            answer_meta={},
            step_key="role_tasks",
            intake_facts={FactKey.ROLE_TRAVEL_REQUIRED.value: False},
        )
        is False
    )
    assert (
        should_show_question(
            oncall_rotation,
            answers={},
            answer_meta={},
            step_key="benefits",
            intake_facts={FactKey.ROLE_ON_CALL.value: "Ja"},
        )
        is True
    )
    assert (
        should_show_question(
            oncall_rotation,
            answers={},
            answer_meta={},
            step_key="benefits",
            intake_facts={FactKey.ROLE_ON_CALL.value: "Nein"},
        )
        is False
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


def test_salary_detail_can_use_canonical_intake_fact() -> None:
    salary_flex = _question(
        "salary_flex_detail",
        label="Wie flexibel ist die Gehaltsspanne inklusive Bonus?",
        target_path="compensation.bonus_notes",
    )

    assert (
        should_show_question(
            salary_flex,
            answers={},
            answer_meta={},
            step_key="benefits",
            intake_facts={
                FactKey.BENEFITS_SALARY_RANGE.value: {
                    "min": 80000,
                    "max": 95000,
                    "currency": "EUR",
                }
            },
        )
        is True
    )
    assert (
        should_show_question(
            salary_flex,
            answers={},
            answer_meta={},
            step_key="benefits",
            intake_facts={FactKey.BENEFITS_SALARY_RANGE.value: {"min": None, "max": ""}},
        )
        is False
    )


def test_leadership_followup_can_use_canonical_intake_facts() -> None:
    team_size = _question(
        "team_size_detail",
        label="Wie groß ist das Team?",
        help_text="Bitte Teamgröße und direkte Reports angeben.",
    )

    assert (
        should_show_question(
            team_size,
            answers={},
            answer_meta={},
            step_key="team",
            intake_facts={FactKey.COMPANY_DIRECT_REPORTS_COUNT.value: 3},
        )
        is True
    )
    assert (
        should_show_question(
            team_size,
            answers={},
            answer_meta={},
            step_key="team",
            intake_facts={FactKey.COMPANY_REPORTS_TO.value: "Head of Product"},
        )
        is True
    )
    assert (
        should_show_question(
            team_size,
            answers={},
            answer_meta={},
            step_key="team",
            intake_facts={FactKey.COMPANY_DIRECT_REPORTS_COUNT.value: 0},
        )
        is False
    )


def test_empty_canonical_fact_values_do_not_trigger_visibility() -> None:
    remote_detail = _question(
        "remote_policy_detail",
        label="Wie viele On-site Tage pro Woche?",
        help_text="Remote policy und Onsite-Erwartungen beschreiben.",
    )
    salary_flex = _question(
        "salary_flex_detail",
        label="Wie flexibel ist die Gehaltsspanne inklusive Bonus?",
        target_path="compensation.bonus_notes",
    )

    assert (
        should_show_question(
            remote_detail,
            answers={},
            answer_meta={},
            step_key="company",
            intake_facts={FactKey.COMPANY_REMOTE_POLICY.value: "   "},
        )
        is False
    )
    assert (
        should_show_question(
            salary_flex,
            answers={},
            answer_meta={},
            step_key="benefits",
            intake_facts={FactKey.BENEFITS_SALARY_RANGE.value: {}},
        )
        is False
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


def test_declared_depends_on_overrides_heuristics_when_present() -> None:
    question = Question(
        id="travel_frequency",
        label="Wie hoch ist die Reisefrequenz?",
        answer_type=AnswerType.SHORT_TEXT,
        depends_on=[QuestionDependency(question_id="travel_required", equals="Ja")],
    )

    assert (
        should_show_question(
            question,
            answers={"travel_required": "Nein"},
            answer_meta={},
            step_key="role_tasks",
            intake_facts={FactKey.ROLE_TRAVEL_REQUIRED.value: True},
        )
        is False
    )
    assert (
        should_show_question(
            question,
            answers={"travel_required": "Ja"},
            answer_meta={},
            step_key="role_tasks",
        )
        is True
    )
