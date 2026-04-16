from __future__ import annotations

from constants import (
    AnswerType,
    NON_INTAKE_STEP_KEYS,
    STEPS,
    STEP_KEY_BENEFITS,
    STEP_KEY_COMPANY,
    STEP_KEY_INTERVIEW,
    STEP_KEY_JOBSPEC_REVIEW,
    STEP_KEY_LANDING,
    STEP_KEY_ROLE_TASKS,
    STEP_KEY_SKILLS,
    STEP_KEY_SUMMARY,
    STEP_KEY_TEAM,
)
from question_progress import compute_question_progress
from schemas import Question, QuestionStep
from wizard_pages import load_pages


def test_loaded_wizard_pages_match_canonical_steps() -> None:
    pages = load_pages()
    visible_page_keys = [page.key for page in pages]
    expected_visible_step_order = [
        STEP_KEY_LANDING,
        STEP_KEY_COMPANY,
        STEP_KEY_ROLE_TASKS,
        STEP_KEY_SKILLS,
        STEP_KEY_BENEFITS,
        STEP_KEY_INTERVIEW,
        STEP_KEY_SUMMARY,
    ]

    assert visible_page_keys == [step.key for step in STEPS]
    assert visible_page_keys == expected_visible_step_order
    assert STEP_KEY_JOBSPEC_REVIEW not in visible_page_keys
    assert STEP_KEY_TEAM not in visible_page_keys


def test_non_intake_step_keys_follow_active_step_contract() -> None:
    rendered_step_keys = {step.key for step in STEPS}
    assert NON_INTAKE_STEP_KEYS
    assert STEP_KEY_JOBSPEC_REVIEW not in rendered_step_keys
    assert all(step_key in rendered_step_keys for step_key in NON_INTAKE_STEP_KEYS)


def test_team_questions_still_progress_via_plan_and_answers_without_routed_step() -> None:
    team_step = QuestionStep(
        step_key=STEP_KEY_TEAM,
        title_de="Team",
        questions=[
            Question(
                id="team_size",
                label="Wie groß ist das Team?",
                answer_type=AnswerType.SHORT_TEXT,
                required=True,
            )
        ],
    )

    progress = compute_question_progress(
        team_step.questions,
        answers={"team_size": "8"},
        answer_meta={},
    )

    assert team_step.step_key == STEP_KEY_TEAM
    assert progress == {"total": 1, "answered": 1, "required_unanswered": 0}
