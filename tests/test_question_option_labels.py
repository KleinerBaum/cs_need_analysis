import json
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

from constants import (
    AnswerType,
    FactKey,
    QUESTION_IMPACT_TARGET_BRIEF,
    STEP_KEY_COMPANY,
)
from question_packs.types import load_question_pack_from_json
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


def test_json_loaded_question_options_preserve_explicit_labels(
    tmp_path: Path,
) -> None:
    path = tmp_path / "pack.json"
    path.write_text(
        json.dumps(
            {
                "pack_key": "test.option_labels",
                "description": "Synthetic option-label pack.",
                "entries": [
                    {
                        "step_key": STEP_KEY_COMPANY,
                        "question": {
                            "id": "ctx_option_label_probe",
                            "label": "Welche Positionierung passt?",
                            "answer_type": AnswerType.MULTI_SELECT.value,
                            "options": [
                                {
                                    "value": "Stabilitaet",
                                    "label": "Stabilität",
                                },
                                "teamfit",
                            ],
                            "target_path": (
                                FactKey.COMPANY_ROLE_RELEVANT_POSITIONING.value
                            ),
                            "fact_key": (
                                FactKey.COMPANY_ROLE_RELEVANT_POSITIONING.value
                            ),
                            "rationale": "Validates JSON option label preservation.",
                            "priority": "standard",
                            "group_key": "company_profile",
                            "impact_targets": [QUESTION_IMPACT_TARGET_BRIEF],
                            "acquisition_cost": "low",
                        },
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    pack = load_question_pack_from_json(path)

    labels = question_option_label_map(pack.entries[0].question)

    assert labels["Stabilitaet"] == "Stabilität"
    assert labels["teamfit"] == "Teamfit"


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
