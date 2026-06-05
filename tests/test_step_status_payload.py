from __future__ import annotations

from constants import AnswerType
from schemas import JobAdExtract, Question, QuestionStep
from step_status import build_step_status_payload


def _always_visible(*_: object) -> bool:
    return True


def test_build_step_status_payload_includes_missing_essential_ids_and_labels() -> None:
    step = QuestionStep(
        step_key="company",
        title_de="Company",
        questions=[
            Question(
                id="q_core_open",
                label="Pflicht offen",
                answer_type=AnswerType.SHORT_TEXT,
                required=True,
                priority="core",
            ),
            Question(
                id="q_core_done",
                label="Pflicht erledigt",
                answer_type=AnswerType.SHORT_TEXT,
                required=True,
                priority="core",
            ),
            Question(
                id="q_detail",
                label="Detail",
                answer_type=AnswerType.SHORT_TEXT,
                required=False,
                priority="detail",
            ),
        ],
    )

    payload = build_step_status_payload(
        step=step,
        answers={"q_core_done": "Ja"},
        answer_meta={},
        should_show_question=_always_visible,
        step_key=step.step_key,
    )

    assert payload["missing_essential_ids"] == ["q_core_open"]
    assert payload["missing_essentials"] == ["Pflicht offen"]
    assert payload["essentials_answered"] == 1
    assert payload["essentials_total"] == 2


def test_build_step_status_payload_counts_jobspec_covered_company_essentials() -> None:
    step = QuestionStep(
        step_key="company",
        title_de="Company",
        questions=[
            Question(
                id="company_q_name",
                label="Wie heißt das Unternehmen?",
                answer_type=AnswerType.SHORT_TEXT,
                required=True,
                priority="core",
            ),
            Question(
                id="company_q_city",
                label="In welcher Stadt befindet sich das Unternehmen?",
                answer_type=AnswerType.SHORT_TEXT,
                required=True,
                priority="core",
            ),
            Question(
                id="company_q_country",
                label="In welchem Land befindet sich das Unternehmen?",
                answer_type=AnswerType.SHORT_TEXT,
                required=True,
                priority="core",
            ),
            Question(
                id="company_q_contract",
                label="Was ist die Art des Arbeitsvertrags?",
                answer_type=AnswerType.SHORT_TEXT,
                required=True,
                priority="core",
            ),
        ],
    )

    payload = build_step_status_payload(
        step=step,
        answers={},
        answer_meta={},
        should_show_question=_always_visible,
        step_key=step.step_key,
        job_extract=JobAdExtract(
            company_name="Rheinbahn",
            employment_type="Unbefristeter Arbeitsvertrag",
        ),
    )

    assert payload["answered"] == 2
    assert payload["total"] == 4
    assert payload["essentials_answered"] == 2
    assert payload["essentials_total"] == 4
    assert payload["missing_essential_ids"] == [
        "company_q_city",
        "company_q_country",
    ]
