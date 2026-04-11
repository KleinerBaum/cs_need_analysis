from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import streamlit as st

from constants import AnswerType, SSKey
from schemas import JobAdExtract, Question, QuestionPlan, QuestionStep


SUMMARY_PATH = Path(__file__).resolve().parents[1] / "wizard_pages" / "08_summary.py"
SPEC = spec_from_file_location("wizard_pages.page_08_summary_facts", SUMMARY_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("Could not load summary page module")
SUMMARY_MODULE = module_from_spec(SPEC)
SPEC.loader.exec_module(SUMMARY_MODULE)  # type: ignore[attr-defined]


def _set_classification_state() -> None:
    st.session_state[SSKey.COMPANY_NACE_CODE.value] = "62.01"
    st.session_state[SSKey.EURES_NACE_TO_ESCO.value] = {
        "62.01": "http://data.europa.eu/esco/occupation/123"
    }


def test_build_summary_fact_rows_include_jobspec_core_facts() -> None:
    _set_classification_state()
    job = JobAdExtract(
        job_title="Data Engineer",
        company_name="Acme",
        location_country="DE",
        location_city="Berlin",
    )

    rows = SUMMARY_MODULE._build_summary_fact_rows(
        job=job,
        answers={},
        plan=None,
        brief=None,
        selected_occupation_title="Dateningenieur/in",
    )

    role_row = next(row for row in rows if row["Feld"] == "Rolle")
    assert role_row == {
        "Bereich": "Kernprofil",
        "Feld": "Rolle",
        "Wert": "Data Engineer",
        "Quelle": "Jobspec",
        "Status": "Vollständig",
    }


def test_build_summary_fact_rows_include_answer_rows() -> None:
    _set_classification_state()
    plan = QuestionPlan(
        steps=[
            QuestionStep(
                step_key="team",
                title_de="Team",
                questions=[
                    Question(
                        id="team_size",
                        label="Teamgröße",
                        answer_type=AnswerType.NUMBER,
                    ),
                ],
            )
        ]
    )

    rows = SUMMARY_MODULE._build_summary_fact_rows(
        job=JobAdExtract(job_title="Data Engineer"),
        answers={"team_size": 7},
        plan=plan,
        brief=None,
        selected_occupation_title=None,
    )

    team_row = next(row for row in rows if row["Feld"] == "Teamgröße")
    assert team_row["Bereich"] == "Team"
    assert team_row["Wert"] == "7"
    assert team_row["Quelle"] == "Intake-Antwort"
    assert team_row["Status"] == "Vollständig"


def test_build_summary_fact_rows_marks_missing_values_as_fehlend() -> None:
    _set_classification_state()
    plan = QuestionPlan(
        steps=[
            QuestionStep(
                step_key="skills",
                title_de="Skills",
                questions=[
                    Question(
                        id="must_have",
                        label="Must-Haves",
                        answer_type=AnswerType.MULTI_SELECT,
                    )
                ],
            )
        ]
    )

    rows = SUMMARY_MODULE._build_summary_fact_rows(
        job=JobAdExtract(job_title="Data Engineer"),
        answers={},
        plan=plan,
        brief=None,
        selected_occupation_title=None,
    )

    skill_row = next(row for row in rows if row["Feld"] == "Must-Haves")
    assert skill_row["Wert"] == "Nicht beantwortet"
    assert skill_row["Status"] == "Fehlend"


def test_build_summary_fact_rows_include_esco_and_nace_rows() -> None:
    _set_classification_state()

    rows = SUMMARY_MODULE._build_summary_fact_rows(
        job=JobAdExtract(job_title="Data Engineer"),
        answers={},
        plan=None,
        brief=None,
        selected_occupation_title="Dateningenieur/in",
    )

    fields = {row["Feld"]: row for row in rows}
    assert fields["ESCO Occupation"]["Status"] == "Automatisch erkannt"
    assert fields["NACE-Code"]["Wert"] == "62.01"
    assert fields["NACE → ESCO Mapping"]["Wert"].startswith("http://data.europa.eu")


def test_build_summary_fact_rows_have_deterministic_ordering() -> None:
    _set_classification_state()

    rows = SUMMARY_MODULE._build_summary_fact_rows(
        job=JobAdExtract(job_title="Data Engineer"),
        answers={},
        plan=None,
        brief=None,
        selected_occupation_title=None,
    )

    ordered_fields = [row["Feld"] for row in rows[:7]]
    assert ordered_fields == [
        "Rolle",
        "Unternehmen",
        "Land",
        "Stadt",
        "ESCO Occupation",
        "NACE-Code",
        "NACE → ESCO Mapping",
    ]
