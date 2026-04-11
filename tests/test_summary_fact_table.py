from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

from constants import AnswerType
from schemas import JobAdExtract, Question, QuestionPlan, QuestionStep


SUMMARY_PATH = Path(__file__).resolve().parents[1] / "wizard_pages" / "08_summary.py"
SPEC = spec_from_file_location("wizard_pages.page_08_summary_facts", SUMMARY_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("Could not load summary page module")
SUMMARY_MODULE = module_from_spec(SPEC)
SPEC.loader.exec_module(SUMMARY_MODULE)  # type: ignore[attr-defined]


def test_build_summary_compact_table_is_row_based_with_missing_and_partial_answers() -> (
    None
):
    """Expected vs Actual: Fakten-Tabelle bleibt row-basiert und zeigt fehlende/teilweise Eingaben korrekt."""
    job = JobAdExtract(
        job_title="Data Engineer", company_name="Acme", location_country="DE"
    )
    plan = QuestionPlan(
        steps=[
            QuestionStep(
                step_key="team",
                title_de="Team",
                questions=[
                    Question(
                        id="team_size", label="Teamgröße", answer_type=AnswerType.NUMBER
                    ),
                    Question(
                        id="collab",
                        label="Zusammenarbeit",
                        answer_type=AnswerType.LONG_TEXT,
                    ),
                ],
            ),
            QuestionStep(
                step_key="skills",
                title_de="Skills",
                questions=[
                    Question(
                        id="must_have",
                        label="Must-Haves",
                        answer_type=AnswerType.MULTI_SELECT,
                    ),
                ],
            ),
        ]
    )
    answers = {
        "team_size": 6,
        # collab fehlt absichtlich
        "must_have": ["Python", "SQL"],
    }

    rows = SUMMARY_MODULE._build_summary_compact_table(
        job=job,
        answers=answers,
        plan=plan,
        brief=None,
    )

    assert rows, "Expected non-empty fact table rows; actual rows are empty"
    assert rows[0]["Jobspec-Übersicht"].startswith("Titel: Data Engineer")
    assert rows[0]["Team"] == "Teamgröße: 6"
    assert rows[0]["Skills"] == "Must-Haves: Python, SQL"
    # Zweite Zeile zeigt fehlende Team-Antwort als leere Zelle (teilweise beantwortet)
    assert rows[1]["Team"] == ""
    assert rows[1]["Skills"] == ""


def test_build_summary_compact_table_marks_unanswered_step() -> None:
    """Expected vs Actual: Vollständig unbeantworteter Step wird explizit als 'Keine Eingaben' ausgewiesen."""
    job = JobAdExtract(job_title="Data Engineer")
    plan = QuestionPlan(
        steps=[
            QuestionStep(
                step_key="company",
                title_de="Unternehmen",
                questions=[
                    Question(
                        id="culture",
                        label="Kultur",
                        answer_type=AnswerType.LONG_TEXT,
                    )
                ],
            )
        ]
    )

    rows = SUMMARY_MODULE._build_summary_compact_table(
        job=job,
        answers={},
        plan=plan,
        brief=None,
    )

    assert rows[0]["Unternehmen"] == "Keine Eingaben"
