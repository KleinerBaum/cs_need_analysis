from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

from constants import AnswerType
from schemas import Question, QuestionOption, question_option_label_map

SUMMARY_PATH = Path(__file__).resolve().parents[1] / "wizard_pages" / "08_summary.py"
SPEC = spec_from_file_location(
    "wizard_pages.page_08_summary_option_labels", SUMMARY_PATH
)
assert SPEC and SPEC.loader
summary = module_from_spec(SPEC)
SPEC.loader.exec_module(summary)


def test_question_option_label_map_humanizes_snake_case_value() -> None:
    question = Question(
        id="culture",
        label="Kulturelle Risiken",
        answer_type=AnswerType.MULTI_SELECT,
        options=["keine_hands_on_mentalitaet", "teamfit"],
    )

    labels = question_option_label_map(question)

    assert labels["keine_hands_on_mentalitaet"] == "Keine Hands-on-Mentalität"
    assert labels["teamfit"] == "Teamfit"


def test_question_option_label_map_prefers_explicit_labels() -> None:
    question = Question(
        id="risk",
        label="Risiko",
        answer_type=AnswerType.SINGLE_SELECT,
        options=[
            QuestionOption(
                value="keine_hands_on_mentalitaet", label="Keine Hands-on-Mentalität"
            ),
            QuestionOption(value="unklare_erwartungen", label="Unklare Erwartungen"),
        ],
    )

    labels = question_option_label_map(question)

    assert labels == {
        "keine_hands_on_mentalitaet": "Keine Hands-on-Mentalität",
        "unklare_erwartungen": "Unklare Erwartungen",
    }


def test_summary_formats_multi_with_option_labels() -> None:
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

    formatted = summary._format_summary_answer_value(
        question,
        ["keine_hands_on_mentalitaet", "unklare_erwartungen"],
    )

    assert formatted == "Keine Hands-on-Mentalität, Unklare Erwartungen"
