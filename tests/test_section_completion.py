from __future__ import annotations

from constants import (
    FactKey,
    FactResolutionStatus,
    STEP_KEY_COMPANY,
    STEP_KEY_SKILLS,
    STEP_SECTION_OPEN_QUESTIONS,
    STEP_SECTION_SOURCE_COMPARISON,
)
from schemas import QuestionStep
from step_payload import build_step_payload
from step_sections import build_section_status_payloads, section_status_summary


def _status_by_section(step_key: str, **kwargs: object) -> dict[str, dict[str, object]]:
    return {
        status["section_id"]: dict(status)
        for status in build_section_status_payloads(step_key=step_key, **kwargs)
    }


def test_section_completion_counts_registered_company_facts() -> None:
    statuses = _status_by_section(
        STEP_KEY_COMPANY,
        intake_facts={
            FactKey.COMPANY_COMPANY_NAME.value: "Example GmbH",
            FactKey.TEAM_SIZE_DIRECT.value: 4,
        },
        intake_fact_evidence={
            FactKey.COMPANY_COMPANY_NAME.value: {
                "confidence": 0.9,
                "resolution_status": FactResolutionStatus.INFERRED.value,
            },
            FactKey.TEAM_SIZE_DIRECT.value: {
                "confidence": 0.9,
                "resolution_status": FactResolutionStatus.CONFIRMED.value,
            },
        },
        confidence_threshold=0.6,
    )

    open_questions = statuses[STEP_SECTION_OPEN_QUESTIONS]

    assert open_questions["completion_state"] == "complete"
    assert open_questions["answered"] == 2
    assert open_questions["total"] > 2
    assert FactKey.COMPANY_BRAND_NAME.value in open_questions["missing_fact_keys"]


def test_section_completion_respects_conflicted_or_low_confidence_evidence() -> None:
    statuses = _status_by_section(
        STEP_KEY_SKILLS,
        intake_facts={
            FactKey.SKILLS_MUST_HAVE_SKILLS.value: ["Python"],
            FactKey.SKILLS_NICE_TO_HAVE_SKILLS.value: ["SQL"],
        },
        intake_fact_evidence={
            FactKey.SKILLS_MUST_HAVE_SKILLS.value: {
                "confidence": 0.4,
                "resolution_status": FactResolutionStatus.INFERRED.value,
            },
            FactKey.SKILLS_NICE_TO_HAVE_SKILLS.value: {
                "confidence": 0.9,
                "resolution_status": FactResolutionStatus.CONFLICTED.value,
            },
        },
        confidence_threshold=0.6,
    )

    source_comparison = statuses[STEP_SECTION_SOURCE_COMPARISON]

    assert source_comparison["completion_state"] == "not_started"
    assert source_comparison["answered"] == 0
    assert FactKey.SKILLS_MUST_HAVE_SKILLS.value in source_comparison["missing_fact_keys"]
    assert FactKey.SKILLS_NICE_TO_HAVE_SKILLS.value in source_comparison["missing_fact_keys"]


def test_step_payload_includes_section_statuses_without_changing_question_status() -> None:
    payload = build_step_payload(
        step=QuestionStep(step_key=STEP_KEY_COMPANY, title_de="Company", questions=[]),
        answers={},
        answer_meta={},
        question_limits=None,
        intake_facts={FactKey.COMPANY_COMPANY_NAME.value: "Example GmbH"},
    )

    complete_sections, total_sections = section_status_summary(
        payload["section_statuses"]
    )

    assert payload["step_status"]["total"] == 0
    assert total_sections >= 1
    assert complete_sections >= 1
