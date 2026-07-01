from __future__ import annotations

from constants import (
    AnswerType,
    FactKey,
    FactResolutionStatus,
    FactSourceType,
    STEP_KEY_COMPANY,
    STEP_KEY_ROLE_TASKS,
    STEP_SECTION_OPEN_QUESTIONS,
)
from schemas import Question, QuestionStep
from step_sections import (
    filter_open_questions_for_step,
    get_section_fact_keys,
    get_step_sections,
    question_candidate_fact_keys,
    should_show_open_question,
)


def test_company_registry_declares_reference_open_question_fact_keys() -> None:
    sections = get_step_sections(STEP_KEY_COMPANY)

    assert sections[0].section_id == STEP_SECTION_OPEN_QUESTIONS
    assert sections[0].step_key == STEP_KEY_COMPANY
    assert FactKey.COMPANY_COMPANY_NAME in sections[0].fact_keys
    assert FactKey.TEAM_SIZE_DIRECT in sections[0].fact_keys
    assert FactKey.COMPANY_WORK_ARRANGEMENT in sections[0].fact_keys
    assert FactKey.COMPANY_NON_NEGOTIABLES in sections[0].fact_keys
    assert sections[0].open_question_fallback is False
    assert "ctx_confidential_external_narrative" in sections[0].duplicate_exempt_question_ids
    assert FactKey.COMPANY_COMPANY_NAME in get_section_fact_keys(
        STEP_KEY_COMPANY,
        STEP_SECTION_OPEN_QUESTIONS,
    )


def test_question_candidate_fact_keys_resolves_legacy_paths_and_explicit_fact_key() -> None:
    question = Question(
        id="q_1",
        label="Rolle",
        answer_type=AnswerType.SHORT_TEXT,
        target_path="job.job_title",
        fact_key=FactKey.ROLE_JOB_TITLE.value,
    )

    assert question_candidate_fact_keys(question) == (FactKey.ROLE_JOB_TITLE,)


def test_company_open_question_filter_removes_structured_duplicates_but_keeps_exemption() -> None:
    step = QuestionStep(
        step_key=STEP_KEY_COMPANY,
        title_de="Company",
        questions=[
            Question(
                id="ctx_team_size_direct",
                label="Wie groß ist das unmittelbare Team?",
                answer_type=AnswerType.NUMBER,
                fact_key=FactKey.TEAM_SIZE_DIRECT.value,
            ),
            Question(
                id="ctx_confidential_external_narrative",
                label="Welche Details sollen extern neutralisiert werden?",
                answer_type=AnswerType.LONG_TEXT,
                fact_key=FactKey.COMPANY_NON_NEGOTIABLES.value,
            ),
            Question(
                id="ctx_distinct_role_assumption",
                label="Welche Annahme bleibt offen?",
                answer_type=AnswerType.LONG_TEXT,
                fact_key=FactKey.ROLE_ASSUMPTIONS.value,
            ),
        ],
    )

    filtered = filter_open_questions_for_step(step)

    assert filtered is not None
    assert [question.id for question in filtered.questions] == [
        "ctx_confidential_external_narrative",
    ]


def test_open_question_visibility_hides_fact_owned_by_another_structured_step() -> None:
    question = Question(
        id="custom_question",
        label="Welche Annahmen sind offen?",
        answer_type=AnswerType.LONG_TEXT,
        fact_key=FactKey.ROLE_ASSUMPTIONS.value,
    )

    assert (
        should_show_open_question(
            question,
            step_key=STEP_KEY_COMPANY,
            intake_facts={FactKey.ROLE_ASSUMPTIONS.value: "Hybrid ist moeglich"},
            intake_fact_evidence={
                FactKey.ROLE_ASSUMPTIONS.value: {
                    "source_type": FactSourceType.JOBSPEC.value,
                    "confidence": 0.9,
                    "resolution_status": FactResolutionStatus.INFERRED.value,
                }
            },
            confidence_threshold=0.6,
        )
        is False
    )

    assert (
        should_show_open_question(
            question,
            step_key=STEP_KEY_COMPANY,
            intake_facts={FactKey.ROLE_ASSUMPTIONS.value: "Hybrid ist moeglich"},
            intake_fact_evidence={
                FactKey.ROLE_ASSUMPTIONS.value: {
                    "source_type": FactSourceType.JOBSPEC.value,
                    "confidence": 0.4,
                    "resolution_status": FactResolutionStatus.INFERRED.value,
                }
            },
            confidence_threshold=0.6,
        )
        is False
    )


def test_role_tasks_registry_owns_work_context_for_duplicate_suppression() -> None:
    step = QuestionStep(
        step_key=STEP_KEY_ROLE_TASKS,
        title_de="Role",
        questions=[
            Question(
                id="ctx_work_arrangement",
                label="Welches Arbeitsmodell gilt?",
                answer_type=AnswerType.SINGLE_SELECT,
                fact_key=FactKey.COMPANY_WORK_ARRANGEMENT.value,
            ),
            Question(
                id="ctx_unmapped",
                label="Was ist fachlich noch offen?",
                answer_type=AnswerType.LONG_TEXT,
            ),
        ],
    )

    filtered = filter_open_questions_for_step(step)

    assert filtered is not None
    assert [question.id for question in filtered.questions] == ["ctx_unmapped"]
