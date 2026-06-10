from __future__ import annotations

from constants import AnswerType, FactKey
from schemas import Question, QuestionOption
from summary_facts import (
    SummaryFactsRow,
    format_summary_answer_value,
    group_summary_fact_rows_by_area,
    status_for_answer_value,
    status_for_value,
    summary_core_fact_row,
)


def test_group_summary_fact_rows_by_area_preserves_order() -> None:
    rows = [
        SummaryFactsRow("Kernprofil", "Rolle", "Engineer", "Jobspec", "Vollständig"),
        SummaryFactsRow("Benefits", "Benefits", "Mentoring", "Auswahl", "Vollständig"),
        SummaryFactsRow("Kernprofil", "Stadt", "Berlin", "Jobspec", "Vollständig"),
    ]

    grouped = group_summary_fact_rows_by_area(rows)

    assert [(area, [row.feld for row in area_rows]) for area, area_rows in grouped] == [
        ("Kernprofil", ["Rolle", "Stadt"]),
        ("Benefits", ["Benefits"]),
    ]


def test_format_summary_answer_value_uses_option_labels() -> None:
    question = Question(
        id="risk",
        label="Risiko",
        answer_type=AnswerType.MULTI_SELECT,
        options=[
            QuestionOption(
                value="keine_hands_on_mentalitaet", label="Keine Hands-on-Mentalität"
            ),
            "unklare_erwartungen",
        ],
    )

    formatted = format_summary_answer_value(
        question,
        ["keine_hands_on_mentalitaet", "unklare_erwartungen"],
    )

    assert formatted == "Keine Hands-on-Mentalität, Unklare Erwartungen"


def test_status_helpers_distinguish_missing_partial_and_complete() -> None:
    assert status_for_value(None) == "Fehlend"
    assert status_for_value({"name": "M. Example", "email": ""}) == "Teilweise"
    assert status_for_value(["Python", "SQL"]) == "Vollständig"

    question = Question(
        id="must_have",
        label="Must-Haves",
        answer_type=AnswerType.MULTI_SELECT,
    )
    assert (
        status_for_answer_value(
            question=question,
            raw_value=["Python", ""],
            formatted="Python",
        )
        == "Teilweise"
    )


def test_summary_core_fact_row_prefers_canonical_fact_evidence_source() -> None:
    row = summary_core_fact_row(
        label="Rolle",
        fact_key=FactKey.ROLE_JOB_TITLE,
        fallback_value="Data Engineer",
        intake_facts={FactKey.ROLE_JOB_TITLE.value: "Analytics Engineer"},
        intake_fact_evidence={
            FactKey.ROLE_JOB_TITLE.value: {"source_label": "Manual input"}
        },
    )

    assert row.to_dict() == {
        "Bereich": "Kernprofil",
        "Feld": "Rolle",
        "Wert": "Analytics Engineer",
        "Quelle": "Manual input",
        "Status": "Vollständig",
    }
